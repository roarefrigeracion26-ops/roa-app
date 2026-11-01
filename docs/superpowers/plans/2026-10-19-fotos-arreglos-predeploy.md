# Arreglos de fotos pre-deploy — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar los huecos bloqueantes (pérdida de mediciones al subir/borrar fotos, PDF que omite fotos en silencio, límite de 3 no atómico, orden no determinista) y los ajustes de bajo costo, antes de desplegar la feature de fotos.

**Architecture:** Los endpoints de fotos responden JSON (con el parcial re-renderizado) cuando la petición es fetch, para operar sin recargar y no perder mediciones; el PDF compara fotos esperadas contra descargadas y falla de forma visible; el límite de 3 se serializa con `select_for_update()` sobre `EquipoIntervenido`.

**Tech Stack:** Django 5.2, PostgreSQL (Supabase), Cloudflare R2 (django-storages/boto3), Pillow, xhtml2pdf, pypdf (tests), Bootstrap 5, JS vanilla.

## Global Constraints

- Sin em dash en texto nuevo (R-02). Reutilizar marca ROA: `--roa-blue #1565C0`; gold corregido `#8B6914` (texto blanco, contraste ≈ 5.09:1, verificable).
- Detección de AJAX SOLO por `X-Requested-With: fetch` (sin condición de `content_type`).
- El handler de fotos NO toca el flag `dirty` ni el guard `beforeunload`.
- Un commit por tarea. Tests escritos junto a cada fix. Sin push sin autorización.
- Rama: seguir en `feature/fotos-equipos`.
- Tests: `$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations`
- `select_for_update()` requiere PostgreSQL; SQLite lo ignora → el test de concurrencia usa `TransactionTestCase` y solo corre en Postgres.

---

### Task 1: Orden determinista de fotos

**Files:**
- Modify: `operations/models.py:318-322`
- Create: `operations/migrations/0010_alter_fotoequipo_options.py`
- Test: `operations/tests.py`

**Interfaces:**
- Produces: `FotoEquipo.Meta.ordering = ['creada_en', 'id']` (orden estable usado por formulario y PDF).

- [ ] **Step 1: Write the failing test**

```python
def test_orden_estable_con_misma_fecha(self):
    from datetime import timedelta
    from django.utils import timezone

    base = timezone.now()
    f1 = FotoEquipo.objects.create(equipo_intervenido=self.ei, momento=MomentoFoto.ANTES)
    f2 = FotoEquipo.objects.create(equipo_intervenido=self.ei, momento=MomentoFoto.ANTES)
    FotoEquipo.objects.filter(pk=f1.pk).update(creada_en=base)
    FotoEquipo.objects.filter(pk=f2.pk).update(creada_en=base)

    ids = list(FotoEquipo.objects.filter(equipo_intervenido=self.ei)
               .values_list('pk', flat=True))
    self.assertEqual(ids, sorted([f1.pk, f2.pk]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `manage.py test operations.tests.X.test_orden_estable_con_misma_fecha -v 2`
Expected: FAIL (el orden por `creada_en` empatado no garantiza `id` ascendente).

- [ ] **Step 3: Write minimal implementation**

`operations/models.py`:
```python
    class Meta:
        verbose_name = 'Foto de equipo'
        verbose_name_plural = 'Fotos de equipos'
        ordering = ['creada_en', 'id']
        indexes = [models.Index(fields=['equipo_intervenido', 'momento'])]
```
Run: `manage.py makemigrations operations` → genera `0010_alter_fotoequipo_options.py` (AlterModelOptions, sin cambio de esquema).

- [ ] **Step 4: Run test to verify it passes**

Run: `manage.py test operations -v 2`
Expected: PASS (13+ tests).

- [ ] **Step 5: Commit**

```bash
git add operations/models.py operations/migrations/0010_alter_fotoequipo_options.py operations/tests.py
git commit -m "fix: orden determinista de fotos (creada_en, id)"
```

---

### Task 2: Subir y borrar fotos sin recargar (evita perder mediciones) — Critical

**Files:**
- Modify: `operations/views.py` (SubirFotosView ~586-636, EliminarFotoView ~642-655; nuevo helper)
- Modify: `templates/operations/_bloque_fotos.html`
- Modify: `templates/operations/formulario_orden.html` (JS ~660-709)
- Test: `operations/tests.py`

**Interfaces:**
- Consumes: `MAX_FOTOS_POR_MOMENTO`, `MomentoFoto`.
- Produces: `_render_bloque_fotos(request, orden, ei, momento) -> str` (HTML del parcial).
- Produces: `SubirFotosView.post` / `EliminarFotoView.post` responden `JsonResponse({'ok': bool, 'html': str, 'count': int, 'max': int, 'message': str})` cuando `X-Requested-With: fetch`; sin ese header, `messages` + redirect (compatibilidad no-JS intacta).

- [ ] **Step 1: Write the failing test**

```python
def test_subir_foto_ajax_devuelve_json_y_html(self):
    resp = self.client.post(
        reverse('operations:subir_fotos', args=[self.orden.pk, self.ei.pk, 'ANTES']),
        {'fotos': self._imagen()}, HTTP_X_REQUESTED_WITH='fetch',
    )
    self.assertEqual(resp.status_code, 200)
    self.assertEqual(resp['Content-Type'], 'application/json')
    data = resp.json()
    self.assertTrue(data['ok'])
    self.assertIn('foto-bloque', data['html'])
    self.assertEqual(data['count'], 1)

def test_eliminar_foto_ajax_devuelve_json(self):
    foto = self._crear_foto(self.ei, MomentoFoto.ANTES)
    resp = self.client.post(
        reverse('operations:eliminar_foto', args=[self.orden.pk, foto.pk]),
        HTTP_X_REQUESTED_WITH='fetch',
    )
    self.assertEqual(resp.status_code, 200)
    self.assertTrue(resp.json()['ok'])
    self.assertEqual(resp.json()['count'], 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `manage.py test operations -v 2`
Expected: FAIL (hoy devuelve 302 redirect, no JSON).

- [ ] **Step 3: Write minimal implementation**

Helper en `operations/views.py`:
```python
from django.http import JsonResponse
from django.template.loader import render_to_string

def _es_fetch(request):
    return request.headers.get('X-Requested-With') == 'fetch'

def _render_bloque_fotos(request, orden, ei, momento):
    fotos = [f for f in ei.fotos.all() if f.momento == momento]
    etapa = 'antes' if momento == MomentoFoto.ANTES else 'despues'
    return render_to_string('operations/_bloque_fotos.html', {
        'orden': orden, 'ei': ei, 'momento': momento,
        'titulo': dict(MomentoFoto.choices)[momento], 'etapa': etapa,
        'fotos': fotos, 'count': len(fotos), 'max_fotos': MAX_FOTOS_POR_MOMENTO,
    }, request=request)  # request => conserva {% csrf_token %}
```

`SubirFotosView.post`: reemplazar los `return redirect(...)` por el helper de respuesta:

```python
    def _respuesta(self, request, orden, ei, momento, ok, message, status=200):
        if _es_fetch(request):
            fotos = ei.fotos.filter(momento=momento)
            return JsonResponse({
                'ok': ok, 'message': message,
                'count': fotos.count(), 'max': MAX_FOTOS_POR_MOMENTO,
                'html': _render_bloque_fotos(request, orden, ei, momento),
            }, status=status)
        (messages.success if ok else messages.error)(request, message)
        return redirect('operations:formulario_orden', orden_id=orden.pk)
```
Usar `_respuesta` en cada salida (sin archivos, tope alcanzado, validación, éxito y error inesperado), pasando `ei`/`momento` ya resueltos.

`EliminarFotoView.post`:
```python
        ei = foto.equipo_intervenido
        momento = foto.momento
        foto.delete()
        if _es_fetch(request):
            return JsonResponse({
                'ok': True, 'message': 'Foto eliminada.',
                'count': ei.fotos.filter(momento=momento).count(),
                'max': MAX_FOTOS_POR_MOMENTO,
                'html': _render_bloque_fotos(request, orden, ei, momento),
            })
        messages.success(request, 'Foto eliminada.')
        return redirect('operations:formulario_orden', orden_id=orden.pk)
```

`_bloque_fotos.html`: dar id estable al root y clase al form de borrado (para delegación):
```html
<div class="foto-bloque h-100 w-100" id="foto-bloque-{{ ei.pk }}-{{ etapa }}" data-foto-bloque>
```
```html
<form method="post" action="{% url 'operations:eliminar_foto' orden.pk foto.pk %}"
      class="m-0 foto-delete-form" onsubmit="return confirm('¿Eliminar esta foto?');">
```

`formulario_orden.html` JS: excluir los forms de fotos de los handlers globales y añadir delegación en un contenedor estable:
```javascript
// handlers globales: excluir forms de fotos
document.querySelectorAll('form:not(.foto-form):not(.foto-delete-form)').forEach(f => {
    f.addEventListener('submit', function () {
        const btn = this.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;
    });
});
document.querySelectorAll('form:not(.foto-form):not(.foto-delete-form)').forEach(f => {
    f.addEventListener('submit', () => dirty = false);
});

// delegación estable para fotos (sobrevive al reemplazo de innerHTML)
const zonaFotos = document.getElementById('equipos-intervenidos') || document.body;
document.addEventListener('change', e => {
    if (e.target.matches('.foto-input')) optimizarEntrada(e.target);
});
zonaFotos.addEventListener('submit', async e => {
    const form = e.target;
    if (!form.matches('.foto-form, .foto-delete-form')) return;
    e.preventDefault();
    const bloque = form.closest('[data-foto-bloque]');
    const aviso = form.querySelector('.foto-aviso');
    const btn = form.querySelector('button[type="submit"]');
    if (btn) btn.disabled = true;
    try {
        const resp = await fetch(form.action, {
            method: 'POST', body: new FormData(form),
            headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin',
        });
        const tipo = resp.headers.get('content-type') || '';
        if (!tipo.includes('application/json')) {
            if (aviso) aviso.textContent = 'Tu sesión expiró. Recarga la página.';
            return; // sesión expirada: fetch siguió el redirect a login
        }
        const data = await resp.json();
        if (data.html && bloque) bloque.outerHTML = data.html;
        else if (aviso) aviso.textContent = data.message || 'No se pudo actualizar.';
    } catch (err) {
        if (aviso) aviso.textContent = 'Error de red. Intenta de nuevo.';
    } finally {
        if (document.body.contains(btn)) btn.disabled = false;
    }
});
```
Añadir `id="equipos-intervenidos"` al contenedor de la sección de equipos intervenidos en `formulario_orden.html`.

- [ ] **Step 4: Run test to verify it passes**

Run: `manage.py test operations -v 2`
Expected: PASS. Verificación manual: con mediciones sin guardar, subir/borrar foto NO recarga ni pierde datos.

- [ ] **Step 5: Commit**

```bash
git add operations/views.py templates/operations/_bloque_fotos.html templates/operations/formulario_orden.html operations/tests.py
git commit -m "fix: subir y borrar fotos sin recargar la pagina (evita perder mediciones)"
```

---

### Task 3: El PDF falla de forma visible si una foto no carga

**Files:**
- Modify: `operations/views.py` (link_callback 51-88, PDFOrdenView 721-758)
- Create: `templates/operations/pdf_error.html`
- Test: `operations/tests.py`

**Interfaces:**
- Produces: `_make_link_callback(state) -> callable`; `state = {'ok': set(), 'fallos': dict, 'temporales': list}`.
- Produces: `PDFOrdenView` devuelve `500` con `pdf_error.html` si `state['fallos']` no está vacío o si `len(state['ok']) < remotas_esperadas`.

- [ ] **Step 1: Write the failing test**

```python
def test_pdf_falla_si_una_foto_no_carga(self):
    from unittest.mock import patch
    foto = self._crear_foto(self.ei, MomentoFoto.ANTES)
    with patch('operations.views.urlopen', side_effect=OSError('boom')), \
         patch.object(type(foto.imagen), 'url', new_callable=lambda: property(lambda s: 'https://r2.example/foto.jpg')):
        resp = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
    self.assertEqual(resp.status_code, 500)
    self.assertIn('Reintentar', resp.content.decode())
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL (hoy devuelve 200 con PDF sin fotos).

- [ ] **Step 3: Write minimal implementation**

`link_callback` → factory con estado, `html.unescape`, timeout, registro de temporales y fallos; limpiar temporales en `finally` desde la vista:
```python
import html as _html
import logging
logger = logging.getLogger(__name__)

def _make_link_callback(state):
    def link_callback(uri, rel):
        import os, tempfile
        from urllib.request import urlopen, Request
        s_url = settings.STATIC_URL
        m_url = getattr(settings, 'MEDIA_URL', '/media/')
        path = None
        if uri.startswith(('http://', 'https://')):
            limpio = _html.unescape(uri)
            try:
                req = Request(limpio, headers={'User-Agent': 'roa-app/1.0'})
                with urlopen(req, timeout=20) as r:
                    contenido = r.read()
                sufijo = os.path.splitext(limpio.split('?')[0])[1] or '.jpg'
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=sufijo)
                tmp.write(contenido); tmp.close()
                state['temporales'].append(tmp.name); state['ok'].add(uri)
                return tmp.name
            except Exception as error:
                state['fallos'][uri] = str(error)
                logger.error('link_callback: no se pudo descargar %s: %s', limpio, error)
                return uri
        # ... ramas static/media igual que hoy ...
    return link_callback
```

`PDFOrdenView.get`: calcular remotas esperadas, usar el callback con estado, limpiar y decidir:
```python
        fotos = [f for ei in equipos_intervenidos for f in (ei.fotos_antes + ei.fotos_despues)]
        remotas = sum(1 for f in fotos if f.imagen.url.startswith(('http://', 'https://')))
        state = {'ok': set(), 'fallos': {}, 'temporales': []}
        try:
            pdf = pisa.pisaDocument(io.BytesIO(html.encode('UTF-8')), result,
                                    link_callback=_make_link_callback(state))
        finally:
            for ruta in state['temporales']:
                try: os.remove(ruta)
                except OSError: pass
        if state['fallos'] or len(state['ok']) < remotas or pdf.err:
            logger.error('PDF orden %s: fallos=%s ok=%s esperadas=%s err=%s',
                         orden.pk, state['fallos'], len(state['ok']), remotas, pdf.err)
            return render(request, 'operations/pdf_error.html', {
                'orden': orden, 'faltantes': max(remotas - len(state['ok']), 0),
                'detalle': list(state['fallos'].keys()),
            }, status=500)
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        ...
```

`templates/operations/pdf_error.html`: página mínima con el mensaje y botón:
```html
{% extends 'base.html' %}
{% block content %}
<div class="container py-5 text-center">
  <h1 class="h4">No se pudo generar el PDF</h1>
  <p class="text-muted">Algunas fotos no se pudieron incluir ({{ faltantes }}). Revisa tu conexión e inténtalo de nuevo.</p>
  <a class="btn btn-roa-primary" href="{% url 'operations:pdf_orden' orden.pk %}">Reintentar</a>
</div>
{% endblock %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `manage.py test operations -v 2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add operations/views.py templates/operations/pdf_error.html operations/tests.py
git commit -m "fix: el PDF falla de forma visible si una foto no se puede incluir"
```

---

### Task 4: Límite de 3 fotos por etapa atómico + admin sin bypass

**Files:**
- Modify: `operations/views.py` (SubirFotosView.post ~606-615)
- Modify: `operations/models.py` (FotoEquipo.clean)
- Modify: `operations/admin.py`
- Test: `operations/tests.py`

**Interfaces:**
- Consumes: `select_for_update()` sobre `EquipoIntervenido`.
- Produces: `FotoEquipo.clean()` que lanza `ValidationError` al superar el tope.

- [ ] **Step 1: Write the failing test**

```python
def test_limite_no_se_excede_con_multiples_archivos(self):
    self._crear_foto(self.ei, MomentoFoto.ANTES)  # 1 existente
    archivos = [self._imagen() for _ in range(5)]  # intenta 5
    self.client.post(
        reverse('operations:subir_fotos', args=[self.orden.pk, self.ei.pk, 'ANTES']),
        {'fotos': archivos},
    )
    self.assertLessEqual(
        FotoEquipo.objects.filter(equipo_intervenido=self.ei, momento=MomentoFoto.ANTES).count(),
        MAX_FOTOS_POR_MOMENTO,
    )
```

Concurrencia (solo Postgres, `TransactionTestCase`):
```python
from django.db import connection
from unittest import skipUnless

@skipUnless(connection.vendor == 'postgresql', 'select_for_update requiere PostgreSQL')
class LimiteConcurrenteTests(TransactionTestCase):
    def test_dos_subidas_concurrentes_no_pasan_de_3(self):
        import threading
        from django.db import connections
        errores = []
        def subir():
            try:
                with connections['default'].cursor():
                    pass
            finally:
                connections.close_all()
        # Implementar: sembrar 1 foto; lanzar 2 hilos que suben 3 cada uno
        # contra la misma etapa; unir; assert count <= MAX_FOTOS_POR_MOMENTO.
```
(El cuerpo completo del hilo usa el `Client`/ORM con su propia conexión y llama `connections.close_all()` al terminar.)

- [ ] **Step 2: Run test to verify it fails**

Run: `manage.py test operations -v 2`
Expected: FAIL o skip en SQLite; en Postgres el test de concurrencia debe fallar hoy.

- [ ] **Step 3: Write minimal implementation**

`SubirFotosView.post` (dentro de `transaction.atomic()`):
```python
        with transaction.atomic():
            ei = get_object_or_404(
                EquipoIntervenido.objects.select_for_update(),
                pk=equipo_id, orden=orden,
            )
            existentes = ei.fotos.filter(momento=momento).count()
            if existentes >= MAX_FOTOS_POR_MOMENTO:
                return self._respuesta(request, orden, ei, momento, False,
                    f'Máximo {MAX_FOTOS_POR_MOMENTO} fotos por etapa. Elimina una para agregar otra.')
            agregadas = 0
            for archivo in archivos:
                if existentes + agregadas >= MAX_FOTOS_POR_MOMENTO:
                    break
                # validar/procesar/guardar dentro del bloque
```

`operations/models.py`:
```python
    def clean(self):
        if self.pk is None and self.equipo_intervenido_id and self.momento:
            existentes = FotoEquipo.objects.filter(
                equipo_intervenido_id=self.equipo_intervenido_id, momento=self.momento,
            ).count()
            if existentes >= MAX_FOTOS_POR_MOMENTO:
                raise ValidationError(
                    f'Máximo {MAX_FOTOS_POR_MOMENTO} fotos por etapa.'
                )
```
(Import `ValidationError` y `MAX_FOTOS_POR_MOMENTO` ya presentes en `models.py`.)

`operations/admin.py`:
```python
    def has_add_permission(self, request):
        return False  # las fotos solo entran por la app (pipeline + límite)

    def get_readonly_fields(self, request, obj=None):
        return ('imagen',) if obj else ()
```
Confirmar en el test/administrador que borrar desde admin dispara `post_delete` (llama `model.delete()`), de modo que borra el archivo.

- [ ] **Step 4: Run test to verify it passes**

Run: `manage.py test operations -v 2` (SQLite) y el test de concurrencia contra Postgres en staging.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add operations/views.py operations/models.py operations/admin.py operations/tests.py
git commit -m "fix: limite de 3 fotos por etapa atomico y admin sin bypass"
```

---

### Task 5: Regresiones (PDF, AJAX, límite, orden)

**Files:** `operations/tests.py`

- [ ] **Step 1: Write tests**

```python
def test_pdf_incrusta_todas_las_fotos(self):
    from pypdf import PdfReader
    for _ in range(2):
        self._crear_foto(self.ei, MomentoFoto.ANTES)
    self._crear_foto(self.ei, MomentoFoto.DESPUES)
    resp = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
    self.assertEqual(resp.status_code, 200)
    lector = PdfReader(io.BytesIO(resp.content))
    total = sum(len(pagina.images) for pagina in lector.pages)
    self.assertGreaterEqual(total, 3)  # al menos una XObject por foto
```
Más: subida AJAX sin redirect, borrado AJAX, orden determinista (Task 1), límite (Task 4).

- [ ] **Step 2: Run to verify red/green**

Run: `manage.py test operations -v 2` → PASS.

- [ ] **Step 3: Commit**

```bash
git add operations/tests.py
git commit -m "test: regresiones de fotos (pdf, ajax, limite, orden)"
```

---

### Task 6: Verificación R2 real en staging (manual, en paralelo)

**Files:** ninguno (checklist).

- [ ] En **staging** con R2 configurado: PUT de una foto (subir en la app), GET firmado OK (miniatura carga), PDF con la imagen incrustada.
- [ ] Confirmar `addressing_style`: si el PUT/GET falla con `virtual`, cambiar `settings.py` a `'path'` y redeployar staging.
- [ ] No hacerlo el día del deploy de producción.

---

### Bloque 2 (mismo PR)

### Task 7: Allowlist de formatos de imagen

**Files:** `operations/images.py`, `templates/operations/_bloque_fotos.html`, `operations/tests.py`

- [ ] Test: subir un archivo con `content_type='image/gif'` (o contenido no soportado) → `ValidationError`.
- [ ] Impl en `validar_archivo`:
```python
    try:
        with Image.open(archivo) as img:
            if img.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValidationError('Formato no soportado. Usa JPG, PNG o WebP.')
            img.verify()
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError('El archivo no es una imagen válida o está dañada.') from error
```
- [ ] Cliente: `accept=".jpg,.jpeg,.png,.webp"` en `_bloque_fotos.html:49`.
- [ ] Commit `fix: permitir solo JPG/PNG/WebP en fotos`.

### Task 8: Registrar fallos de borrado en la señal

**Files:** `operations/signals.py`, `operations/tests.py`

- [ ] Impl: `import logging; logger = logging.getLogger(__name__)` y en el `except`: `logger.warning('No se pudo borrar el archivo %s: %s', nombre, error)`.
- [ ] Test: storage falso que lanza en `delete()`; assert que no propaga y que se registra.
- [ ] Commit `fix: registrar fallos al borrar archivos de fotos`.

### Task 9: Contraste AA del gold

**Files:** `templates/operations/formulario_orden.html`, `templates/operations/reporte_pdf_aa.html`

- [ ] Cambiar `#B8860B` por `#8B6914` con **texto blanco** en cabecera "Después" y "REGISTRO FOTOGRÁFICO".
- [ ] Verificar contraste en código (debe dar ≥ 4.5:1):
```python
def _lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
def ratio(hexcolor):  # con blanco
    r, g, b = (int(hexcolor[i:i+2], 16) for i in (1, 3, 5))
    L = 0.2126*_lin(r) + 0.7152*_lin(g) + 0.0722*_lin(b)
    return (1.05) / (L + 0.05)
assert ratio('#8B6914') >= 4.5  # ≈ 5.09
```
Si dan < 4.5, oscurecer más.
- [ ] Commit `fix: contraste AA en cabeceras gold`.

### Task 10: Botón de borrar accesible

**Files:** `templates/operations/formulario_orden.html` (CSS `.foto-del`), `_bloque_fotos.html`

- [ ] Botón ≥ 24x24 px (ideal 44) y foco con `box-shadow` sin recorte (`overflow`/`outline-offset`).
- [ ] Commit `fix: boton de borrar de fotos mas grande y con foco visible`.

### Bloque 3 (opcional)

### Task 11: Servir /media/ solo en DEBUG

**Files:** `config/urls.py`, `README`/`.env.example`

- [ ] Añadir:
```python
from django.conf import settings
from django.conf.urls.static import static
...
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```
- [ ] Documentar que **producción exige R2** (el disco de Render es efímero).
- [ ] Commit `chore: servir media en modo DEBUG y documentar requisito de R2`.

---

## Self-Review

- **Cobertura:** todos los huecos bloqueantes (pérdida de datos T2, PDF silencioso T3, límite T8, orden T1) y de bajo costo (T7, T8-log, T9, T10) tienen tarea; verificación R2 (T10→Task 6) es manual en staging.
- **Placeholders:** ninguno intencional; el test de concurrencia describe el andamiaje (hilos + `connections.close_all()`) y se completa en ejecución por su complejidad, solo Postgres.
- **Consistencia de tipos:** `_render_bloque_fotos`, `_respuesta`, `_make_link_callback`, `state` con claves `ok/fallos/temporales` se usan coherentemente entre tareas.
