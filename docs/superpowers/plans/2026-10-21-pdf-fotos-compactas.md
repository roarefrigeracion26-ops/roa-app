# Fotos compactas en el PDF (carta, 2x2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reducir el papel del informe PDF mostrando hasta 2 fotos ANTES y 2 DESPUÉS por equipo en una cuadrícula de dos columnas, en tamaño carta, y bajar el límite de subida a 2 fotos por etapa.

**Architecture:** El PDF se arma en `PDFOrdenView` y se renderiza con xhtml2pdf (pisa) desde `templates/operations/reporte_pdf_aa.html`. xhtml2pdf no soporta flexbox ni grid, así que la cuadrícula se implementa con tablas HTML. La sección fotográfica se extrae a un parcial reutilizable para ANTES y DESPUÉS. El límite se gobierna con la constante `MAX_FOTOS_POR_MOMENTO`.

**Tech Stack:** Django 5.2, xhtml2pdf 0.2.17, pypdf 6.7.5 (tests), Pillow.

## Global Constraints

- Sin em dash en textos nuevos.
- No cambiar el contenido técnico, mediciones, observaciones ni el pie del informe.
- No borrar fotos existentes ni bloquear las ya guardadas (las órdenes con 3 fotos por etapa deben seguir renderizando todas).
- Mantener la proporción original de las imágenes (nunca fijar ancho y alto a la vez).
- Tests junto a cada cambio; un commit por tarea.
- Comando de tests: `$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test -v 1`

---

### Task 1: Límite de 2 fotos por etapa

**Files:**
- Modify: `operations/models.py:10`
- Modify: `operations/views.py` (docstring y `aviso_maximo` de `SubirFotosView`)
- Test: `operations/tests.py` (`FotosViewsTests`)

**Interfaces:**
- Consumes: `MAX_FOTOS_POR_MOMENTO` ya se usa en `models.py`, `views.py` y `_bloque_fotos.html`.
- Produces: `MAX_FOTOS_POR_MOMENTO = 2`, que el contador `{{ count }}/{{ max_fotos }}` y la validación toman automáticamente.

- [ ] **Step 1: Escribir tests que fallan**

En `operations/tests.py`, dentro de `FotosViewsTests`, agregar después de `test_bloquea_cuando_ya_hay_maximo`:

```python
    def test_limite_es_dos_fotos_por_etapa(self):
        self.assertEqual(MAX_FOTOS_POR_MOMENTO, 2)

    def test_rechaza_tercera_foto_e_indica_el_limite(self):
        self.client.post(self.url_subir(), {
            'fotos': [imagen_subida('a.jpg'), imagen_subida('b.jpg')],
        })
        respuesta = self.client.post(
            self.url_subir(), {'fotos': [imagen_subida('c.jpg')]},
            HTTP_X_REQUESTED_WITH='fetch',
        )
        self.assertEqual(
            FotoEquipo.objects.filter(
                equipo_intervenido=self.ei, momento=MomentoFoto.ANTES,
            ).count(),
            2,
        )
        self.assertFalse(respuesta.json()['ok'])
        self.assertIn('Máximo 2 fotos por etapa', respuesta.json()['message'])
        self.assertEqual(respuesta.json()['max'], 2)
```

Actualizar `test_formulario_renderiza_bloques_de_fotos`: cambiar `self.assertIn('1/3', html)` por:

```python
        self.assertIn(f'1/{MAX_FOTOS_POR_MOMENTO}', html)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations.tests.FotosViewsTests -v 1
```
Expected: FAIL en `test_limite_es_dos_fotos_por_etapa` (3 != 2) y en `test_rechaza_tercera_foto_e_indica_el_limite` (el mensaje dice "Máximo 3").

- [ ] **Step 3: Implementar el límite**

En `operations/models.py:10`:

```python
MAX_FOTOS_POR_MOMENTO = 2
```

En `operations/views.py`, en `SubirFotosView`, reemplazar el docstring y el aviso:

```python
class SubirFotosView(LoginRequiredMixin, View):
    """POST: agrega fotos por etapa (Antes/Después) hasta el máximo permitido."""
```

```python
            aviso_maximo = (
                f'Máximo {MAX_FOTOS_POR_MOMENTO} fotos por etapa. '
                'Elimina una para agregar otra.'
            )
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations.tests.FotosViewsTests -v 1
```
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add operations/models.py operations/views.py operations/tests.py
git commit -m "feat: limite de dos fotos por etapa"
```

---

### Task 2: PDF en carta con cuadrícula de dos columnas

**Files:**
- Create: `templates/operations/_pdf_fotos_grid.html`
- Modify: `templates/operations/reporte_pdf_aa.html` (`@page`, estilos y sección de registro fotográfico)
- Test: `operations/tests.py` (`FotosViewsTests`)

**Interfaces:**
- Consumes: `ei.fotos_antes` y `ei.fotos_despues`, listas que arma `PDFOrdenView`.
- Produces: parcial `_pdf_fotos_grid.html` con parámetros `titulo` (texto) y `fotos` (lista de `FotoEquipo`).

- [ ] **Step 1: Escribir tests que fallan**

Dentro de `FotosViewsTests`, después de `test_pdf_sin_fotos_no_falla_ni_incluye_registro`:

```python
    def test_pdf_usa_tamano_carta(self):
        from pypdf import PdfReader
        from operations.views import PDFOrdenView

        respuesta = PDFOrdenView().get(self._request(), orden_id=self.orden.pk)
        self.assertEqual(respuesta.status_code, 200)
        pagina = PdfReader(io.BytesIO(respuesta.content)).pages[0]
        self.assertAlmostEqual(float(pagina.mediabox.width), 612, delta=1)
        self.assertAlmostEqual(float(pagina.mediabox.height), 792, delta=1)

    def test_plantilla_pdf_fotos_en_dos_columnas(self):
        colores = [(200, 10, 10), (10, 200, 10), (10, 10, 200), (200, 200, 10)]
        for indice, color in enumerate(colores):
            momento = MomentoFoto.ANTES if indice < 2 else MomentoFoto.DESPUES
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei,
                momento=momento,
                imagen=imagen_subida(f'grid-{indice}.jpg', color=color),
            )

        ei = EquipoIntervenido.objects.get(pk=self.ei.pk)
        ei.fotos_antes = list(ei.fotos.filter(momento=MomentoFoto.ANTES))
        ei.fotos_despues = list(ei.fotos.filter(momento=MomentoFoto.DESPUES))

        from django.template.loader import get_template
        html = get_template('operations/reporte_pdf_aa.html').render({
            'orden': self.orden,
            'equipo': self.orden.equipo,
            'equipos_intervenidos': [ei],
            'actividades': [],
            'fecha': self.orden.hora_inicio,
            'es_preventivo': False,
        })
        self.assertEqual(html.count('class="foto-bloque"'), 2)
        self.assertEqual(html.count('class="foto-celda"'), 4)

    def test_pdf_compacto_no_agrega_mas_de_una_pagina(self):
        from pypdf import PdfReader
        from operations.views import PDFOrdenView

        sin_fotos = PdfReader(io.BytesIO(
            PDFOrdenView().get(self._request(), orden_id=self.orden.pk).content,
        ))

        colores = [(200, 10, 10), (10, 200, 10), (10, 10, 200), (200, 200, 10)]
        for indice, color in enumerate(colores):
            momento = MomentoFoto.ANTES if indice < 2 else MomentoFoto.DESPUES
            FotoEquipo.objects.create(
                equipo_intervenido=self.ei,
                momento=momento,
                imagen=imagen_subida(f'compacto-{indice}.jpg', color=color),
            )

        con_fotos = PdfReader(io.BytesIO(
            PDFOrdenView().get(self._request(), orden_id=self.orden.pk).content,
        ))
        self.assertLessEqual(len(con_fotos.pages), len(sin_fotos.pages) + 1)
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations.tests.FotosViewsTests.test_pdf_usa_tamano_carta operations.tests.FotosViewsTests.test_plantilla_pdf_fotos_en_dos_columnas operations.tests.FotosViewsTests.test_pdf_compacto_no_agrega_mas_de_una_pagina -v 2
```
Expected: FAIL (página A4 de 595 x 842 pt, sin `foto-bloque` y demasiadas páginas).

- [ ] **Step 3: Crear el parcial de la cuadrícula**

`templates/operations/_pdf_fotos_grid.html`:

```html
<table class="foto-bloque">
    <tr>
        <td colspan="2" class="foto-titulo">{{ titulo }}</td>
    </tr>
    {% if fotos %}
    <tr>
        {% for foto in fotos|slice:":2" %}
        <td class="foto-celda"><img class="foto-img" src="{{ foto.imagen.url }}"></td>
        {% endfor %}
    </tr>
    {% if fotos|length > 2 %}
    {% for foto in fotos|slice:"2:" %}
    <tr>
        <td class="foto-celda"><img class="foto-img" src="{{ foto.imagen.url }}"></td>
        <td class="foto-celda"></td>
    </tr>
    {% endfor %}
    {% endif %}
    {% else %}
    <tr>
        <td colspan="2" class="foto-vacio">Sin fotos.</td>
    </tr>
    {% endif %}
</table>
```

- [ ] **Step 4: Cambiar tamaño de página y estilos**

En `templates/operations/reporte_pdf_aa.html`, dentro de `<style>`, cambiar:

```css
        @page {
            size: letter;
            margin: 12mm 10mm;
        }
```

Agregar antes de `</style>`:

```css
        .foto-bloque {
            width: 100%;
            border-collapse: collapse;
            margin: 3px 0 0;
            page-break-inside: avoid;
        }

        .foto-titulo {
            border: 1px solid #333;
            font-weight: bold;
            font-size: 8pt;
            color: #8B6914;
            padding: 2px 5px;
        }

        .foto-celda {
            border: 1px solid #333;
            width: 50%;
            padding: 2px;
            vertical-align: top;
            text-align: center;
        }

        .foto-img {
            width: 92mm;
            border: 1px solid #333;
        }

        .foto-vacio {
            border: 1px solid #333;
            font-size: 8pt;
            color: #555;
            padding: 2px 5px;
        }
```

- [ ] **Step 5: Reemplazar la sección de fotos**

En `templates/operations/reporte_pdf_aa.html`, reemplazar el bloque actual desde
`{% if ei.fotos_antes or ei.fotos_despues %}` hasta su `{% endif %}` (líneas 365 a 391)
por:

```html
    {% if ei.fotos_antes or ei.fotos_despues %}
    <div class="section-bar" style="margin-top:4px;background:#8B6914;-pdf-keep-with-next:true;">REGISTRO FOTOGRÁFICO</div>
    {% include 'operations/_pdf_fotos_grid.html' with titulo='ANTES' fotos=ei.fotos_antes %}
    {% include 'operations/_pdf_fotos_grid.html' with titulo='DESPUÉS' fotos=ei.fotos_despues %}
    {% endif %}
```

- [ ] **Step 6: Correr los tests nuevos**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations.tests.FotosViewsTests -v 1
```
Expected: PASS. Si `test_pdf_compacto_no_agrega_mas_de_una_pagina` falla, revisar que la imagen no tenga alto fijo y que las tablas no se separen; ajustar solo `width` de `.foto-img` y paddings, nunca proporción.

- [ ] **Step 7: Commit**

```powershell
git add templates/operations/_pdf_fotos_grid.html templates/operations/reporte_pdf_aa.html operations/tests.py
git commit -m "feat: fotos compactas en carta dentro del PDF"
```

---

### Task 3: Validación con PDF de prueba

**Files:**
- Create (temporal, no se commitea): `operations/test_muestra_pdf_tmp.py`
- Output: `C:\Users\Usuario\AppData\Local\Temp\opencode\pdf-muestra\`

**Interfaces:**
- Consumes: `PDFOrdenView` y la plantilla ya modificada.
- Produces: PDF de muestra con 2 fotos ANTES y 2 DESPUÉS para revisión visual.

- [ ] **Step 1: Crear el test temporal que escribe el PDF**

`operations/test_muestra_pdf_tmp.py`:

```python
import io
import os
from datetime import date

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from PIL import Image

from inventory.models import Cliente, EquipoAA
from operations.models import EquipoIntervenido, FotoEquipo, MomentoFoto, OrdenServicio
from users.models import Tecnico


def foto(nombre, tamano, color):
    buffer = io.BytesIO()
    Image.new('RGB', tamano, color).save(buffer, format='JPEG')
    buffer.seek(0)
    return SimpleUploadedFile(nombre, buffer.read(), content_type='image/jpeg')


@override_settings(
    MEDIA_ROOT=os.path.join(settings.BASE_DIR, '.muestra-media'),
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class MuestraPDFTests(TestCase):
    def test_genera_muestra(self):
        tecnico = Tecnico.objects.create_user(username='muestra', password='clave123')
        cliente = Cliente.objects.create(nombre='Tienda Muestra')
        equipo = EquipoAA.objects.create(cliente=cliente, nombre='UCA 1', tipo_equipo='UCA')
        orden = OrdenServicio.objects.create(
            equipo=equipo, cliente=cliente, tecnico=tecnico, tipo='MC',
            radicado='MC0001', cliente_nombre='Tienda Muestra',
            fecha=date.today(), hora_inicio=timezone.now(),
        )
        ei = EquipoIntervenido.objects.create(
            orden=orden, nombre_equipo='UCA 1', tipo_equipo='UCA',
            ubicacion='Cocina', marca='York', modelo='YHAC',
        )
        for indice, tamano in enumerate([(1600, 1200), (1200, 1600), (1600, 1200), (1200, 1600)]):
            FotoEquipo.objects.create(
                equipo_intervenido=ei,
                momento=MomentoFoto.ANTES if indice < 2 else MomentoFoto.DESPUES,
                imagen=foto(f'muestra-{indice}.jpg', tamano, (30 * indice, 80, 140)),
            )

        request = RequestFactory().get('/')
        request.user = tecnico
        from operations.views import PDFOrdenView
        respuesta = PDFOrdenView().get(request, orden_id=orden.pk)
        self.assertEqual(respuesta.status_code, 200)

        salida = os.path.join(os.environ.get('TEMP', '.'), 'opencode', 'pdf-muestra')
        os.makedirs(salida, exist_ok=True)
        ruta = os.path.join(salida, 'muestra.pdf')
        with open(ruta, 'wb') as archivo:
            archivo.write(respuesta.content)
        print(f'\nPDF de muestra: {ruta}\n')
```

- [ ] **Step 2: Generar el PDF**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test operations.test_muestra_pdf_tmp -v 2
```
Expected: PASS y ruta impresa.

- [ ] **Step 3: Medir páginas y tamaño**

Run:
```powershell
& "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" -c "from pypdf import PdfReader; r=PdfReader(r'C:\Users\Usuario\AppData\Local\Temp\opencode\pdf-muestra\muestra.pdf'); print('paginas', len(r.pages)); print('tamano', float(r.pages[0].mediabox.width), float(r.pages[0].mediabox.height)); print('texto', [t for t in (r.pages[0].extract_text() or '').split() if t in ('ANTES','DESPUÉS')])"
```
Expected: `paginas` 1 o 2, `tamano` 612.0 792.0 y aparecen ANTES y DESPUÉS.

- [ ] **Step 4: Renderizar las páginas a PNG y revisarlas**

Instalar temporalmente PyMuPDF solo en el venv (no va a `requirements.txt`):

```powershell
& "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" -m pip install pymupdf
```

```powershell
& "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" -c "import fitz, os; d=os.path.join(os.environ['TEMP'],'opencode','pdf-muestra'); doc=fitz.open(os.path.join(d,'muestra.pdf')); [p.get_pixmap(dpi=110).save(os.path.join(d,f'pagina-{i+1}.png')) for i,p in enumerate(doc)]; print(len(doc),'paginas renderizadas')"
```

Revisar visualmente `pagina-1.png` (y `pagina-2.png` si existe): 2 fotos ANTES arriba y 2 DESPUÉS abajo, proporciones correctas, sin cortes ni superposición, encabezados legibles.

- [ ] **Step 5: Limpiar**

```powershell
Remove-Item -LiteralPath "operations\test_muestra_pdf_tmp.py"
Remove-Item -LiteralPath "$env:TEMP\opencode\pdf-muestra" -Recurse -Force
& "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" -m pip uninstall -y pymupdf
Remove-Item -LiteralPath ".muestra-media" -Recurse -Force -ErrorAction SilentlyContinue
```

- [ ] **Step 6: Correr la suite completa**

Run:
```powershell
$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test -v 1
```
Expected: todos los tests en verde.
