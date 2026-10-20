# Landing comercial ROA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar una landing comercial en `/` con la estructura de roarefrigeracion.com y la identidad visual de la app, moviendo el login a `/ingresar/`.

**Architecture:** Una vista `TemplateView` en `config/urls.py` sirve `templates/landing.html`. El login se mueve de `/` a `/ingresar/` en `users/urls.py`; las rutas internas no cambian. La landing es un template independiente con CSS propio en `static/landing/landing.css` y assets locales en `static/landing/`.

**Tech Stack:** Django 5.2, plantillas Django, CSS moderno sin framework en la landing, Montserrat desde Google Fonts, Bootstrap Icons solo si hace falta, Pillow para optimizar imágenes.

## Global Constraints

- Sin em dash en texto visible (regla anti-slop del proyecto).
- Paleta: azul `#1565C0`, azul medio `#1976D2`, dorado `#8B6914`, fondo `#F5F9FF`, tinta `#1B2733`.
- Todo asset local en `static/landing/`. Sin hotlinking.
- Contraste AA en texto y botones. Foco visible en todos los enlaces y botones.
- Una sola página con anclas. No se replican páginas internas.
- Un commit por tarea. No push sin autorización.
- Tests: `$env:DATABASE_URL='sqlite:///./sqlite_test_tmp.sqlite3'; $env:ALLOWED_HOSTS='testserver,localhost,127.0.0.1'; & "C:\Users\Usuario\roa-app\venv\Scripts\python.exe" manage.py test`
- `requirements.txt` está en UTF-16 LE con BOM.

---

### Task 1: Assets locales de la landing

**Files:**
- Create: `static/landing/hero.jpg`
- Create: `static/landing/ofrecemos.jpg`
- Create: `static/landing/clientes/exito.jpg`, `lasa.jpg`, `olimpica.jpg`, `bodytech.jpg`, `sao.jpg`
- Create: `static/landing/iconos/montaje.png`, `mantenimiento.png`, `electricas.png`
- Test: `users/tests.py` (crear)

**Interfaces:**
- Produces: rutas estáticas `landing/hero.jpg`, `landing/ofrecemos.jpg`, `landing/clientes/*.jpg`,
  `landing/iconos/*.png`. Task 2 las referencia con `{% static %}`.

- [ ] **Step 1: Escribir el test que falla**

```python
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase


class LandingAssetsTests(SimpleTestCase):
    def test_assets_de_la_landing_existen(self):
        nombres = [
            'landing/hero.jpg',
            'landing/ofrecemos.jpg',
            'landing/clientes/exito.jpg',
            'landing/clientes/lasa.jpg',
            'landing/clientes/olimpica.jpg',
            'landing/clientes/bodytech.jpg',
            'landing/clientes/sao.jpg',
            'landing/iconos/montaje.png',
            'landing/iconos/mantenimiento.png',
            'landing/iconos/electricas.png',
        ]
        for nombre in nombres:
            with self.subTest(nombre=nombre):
                self.assertIsNotNone(finders.find(nombre), f'Falta {nombre}')
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `... manage.py test users.tests.LandingAssetsTests -v 2`
Expected: FAIL con `Falta landing/hero.jpg`.

- [ ] **Step 3: Descargar y optimizar los assets**

```powershell
New-Item -ItemType Directory -Force "static\landing\clientes" | Out-Null
New-Item -ItemType Directory -Force "static\landing\iconos" | Out-Null
$base = 'https://roarefrigeracion.com/wp-content/uploads/2018/03/'
$mapa = @{
  'cliente-exito.jpg'     = 'clientes\exito.jpg'
  'cliente-lasa.jpg'      = 'clientes\lasa.jpg'
  'cliente-olimpica.jpg'  = 'clientes\olimpica.jpg'
  'cliente-bodytech.jpg'  = 'clientes\bodytech.jpg'
  'cleinte-sao.jpg'       = 'clientes\sao.jpg'
  'iconos-home-01.png'    = 'iconos\montaje.png'
  'iconos-home-02.png'    = 'iconos\mantenimiento.png'
  'iconos-home-03.png'    = 'iconos\electricas.png'
}
foreach ($origen in $mapa.Keys) {
  Invoke-WebRequest -Uri ($base + $origen) -OutFile ("static\landing\" + $mapa[$origen]) -UseBasicParsing
}
Copy-Item "C:\Users\Usuario\Downloads\Hero.jpg" "static\landing\hero.jpg" -Force
Copy-Item "C:\Users\Usuario\Downloads\Ofrecemos.jpg" "static\landing\ofrecemos.jpg" -Force
```

Script de optimización (guardar en `C:\Users\Usuario\AppData\Local\Temp\opencode\opt_landing.py` y ejecutar con el Python del venv):

```python
from pathlib import Path
from PIL import Image

raiz = Path(r'C:\Users\Usuario\roa-app\static\landing')

def optimizar(ruta, max_lado=1600, calidad=82, alto=None):
    img = Image.open(ruta)
    img = img.convert('RGB')
    img.thumbnail((max_lado, max_lado), Image.LANCZOS) if alto is None else img.resize(
        (round(img.width * alto / img.height), alto), Image.LANCZOS
    )
    img.save(ruta, 'JPEG', quality=calidad, optimize=True, progressive=True)

optimizar(raiz / 'hero.jpg')
optimizar(raiz / 'ofrecemos.jpg')
for nombre in ['exito', 'lasa', 'olimpica', 'bodytech', 'sao']:
    optimizar(raiz / 'clientes' / f'{nombre}.jpg', max_lado=400, calidad=85)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `... manage.py test users.tests.LandingAssetsTests -v 2`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add static/landing users/tests.py
git commit -m "feat: assets locales para la landing comercial"
```

---

### Task 2: Rutas y página de la landing

**Files:**
- Modify: `config/urls.py`
- Modify: `users/urls.py`
- Create: `templates/landing.html`
- Create: `static/landing/landing.css`
- Test: `users/tests.py`

**Interfaces:**
- Consumes: assets de Task 1.
- Produces: nombre de URL `landing` en `/`, login en `/ingresar/`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
from django.test import TestCase
from django.urls import reverse

from users.models import Tecnico


class LandingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tecnico = Tecnico.objects.create_user(username='tec', password='clave123')

    def test_raiz_publica_muestra_hero(self):
        respuesta = self.client.get('/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Aire acondicionado y refrigeración para empresas')

    def test_raiz_ya_no_es_el_login(self):
        respuesta = self.client.get('/')
        self.assertNotContains(respuesta, 'id_username')

    def test_login_vive_en_ingresar(self):
        respuesta = self.client.get('/ingresar/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'id_username')

    def test_raiz_enlaza_al_login(self):
        respuesta = self.client.get('/')
        self.assertContains(respuesta, reverse('users:login'))

    def test_autenticado_ve_ir_al_sistema(self):
        self.client.force_login(self.tecnico)
        respuesta = self.client.get('/')
        self.assertContains(respuesta, 'Ir al sistema')
        self.assertNotContains(respuesta, 'Ingresar al sistema')

    def test_login_post_redirige_por_rol(self):
        respuesta = self.client.post('/ingresar/', {'username': 'tec', 'password': 'clave123'})
        self.assertRedirects(respuesta, reverse('inventory:clientes'))
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `... manage.py test users.tests.LandingTests -v 2`
Expected: FAIL, `/` devuelve 404 o el formulario de login.

- [ ] **Step 3: Cambiar las rutas**

```python
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='landing.html'), name='landing'),
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', include('inventory.urls')),
    path('', include('operations.urls')),
    path('', include('analytics.urls')),
]
```

```python
# users/urls.py
urlpatterns = [
    path('ingresar/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
```

- [ ] **Step 4: Crear `templates/landing.html`**

Estructura obligatoria, con `{% load static %}` y CSS en `landing/landing.css`:

1. `<a class="skip" href="#contenido">Saltar al contenido</a>`.
2. `<header class="site-header">` con barra superior (`info@roarefrigeracion.com`, `(5) 301 1758`,
   `311 699 1895`) y botón de ingreso. Si `user.is_authenticated`, el botón dice "Ir al sistema"
   y apunta al destino por rol que usa `base.html`; si no, dice "Ingresar" y apunta a
   `{% url 'users:login' %}`.
3. Menú con anclas `#servicios`, `#clientes`, `#nosotros`, `#contacto` y logo
   `{% static 'image/roa-logo.jpeg' %}`.
4. `<section class="hero">` con `{% static 'landing/hero.jpg' %}` de fondo:
   antetítulo "REFRIGERACIÓN Y CLIMATIZACIÓN", `<h1>` "Aire acondicionado y refrigeración para
   empresas que no pueden parar", subtítulo, botón "Ver servicios" y botón de ingreso.
5. `<section id="nosotros">` con `{% static 'landing/ofrecemos.jpg' %}`, título "Ofrecemos
   soluciones", el texto del spec y CTA "Conocer servicios" a `#servicios`.
6. `<section id="servicios">` con tres filas numeradas 01/02/03, sus iconos de
   `landing/iconos/` y los textos del spec.
7. `<section id="clientes">` con "Empresas que confían en nosotros" y los cinco logos.
8. `<section class="testimonio">` con la cita del spec y "Jorge Roa, Mánager Olímpica".
9. `<section id="contacto">` con dirección, teléfonos en enlaces `tel:` y correo `mailto:`.
10. `<footer>` con el copyright 2026.
11. `title`, `meta description`, Open Graph con `landing/hero.jpg` y JSON-LD `LocalBusiness`.
12. Script mínimo para el menú móvil y para `.reveal` con `IntersectionObserver`.

- [ ] **Step 5: Crear `static/landing/landing.css`**

Reglas obligatorias:

- Variables en `:root` con la paleta del spec y `--max: 1180px`.
- `.hero`: `min-height: 620px`, imagen de fondo `cover`, degradado
  `linear-gradient(100deg, rgba(8,25,50,.92) 0%, rgba(8,25,50,.72) 45%, rgba(8,25,50,.30) 100%)`,
  texto blanco, `h1` de 56 px en escritorio.
- `.servicios`: grid de 3 columnas con `border-top: 2px solid #8B6914`, número grande en dorado,
  sin tarjetas.
- `.clientes`: logos en `filter: grayscale(1); opacity: .6`, color al `:hover`.
- `.testimonio`: fondo `#1565C0`, cita blanca de 26 px, comilla dorada.
- `.contacto`: dos columnas, enlaces `tel:` y `mailto:` con foco visible.
- `@media (max-width: 900px)`: hero apilado, servicios en una columna, contacto en una columna.
- `@media (prefers-reduced-motion: reduce)`: desactivar transiciones y `.reveal`.
- Todos los `a:focus-visible` y `button:focus-visible` con `outline: 3px solid #8B6914; outline-offset: 3px`.

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `... manage.py test users.tests -v 2`
Expected: OK.

- [ ] **Step 7: Commit**

```bash
git add config/urls.py users/urls.py templates/landing.html static/landing/landing.css
git commit -m "feat: landing comercial publica en la raiz"
```

---

### Task 3: Enlace de regreso en el login y regresión final

**Files:**
- Modify: `templates/users/login.html`
- Test: `users/tests.py`

**Interfaces:**
- Consumes: nombre de URL `landing` de Task 2.
- Produces: enlace "Volver al inicio" en `/ingresar/`.

- [ ] **Step 1: Escribir el test que falla**

```python
def test_login_tiene_volver_al_inicio(self):
    respuesta = self.client.get('/ingresar/')
    self.assertContains(respuesta, reverse('landing'))
    self.assertContains(respuesta, 'Volver al inicio')
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `... manage.py test users.tests.LandingTests.test_login_tiene_volver_al_inicio -v 2`
Expected: FAIL.

- [ ] **Step 3: Agregar el enlace**

Debajo del formulario, dentro de la tarjeta:

```html
<p class="text-center mt-3 mb-0 small">
  <a href="{% url 'landing' %}" class="text-decoration-none">Volver al inicio</a>
</p>
```

- [ ] **Step 4: Correr la suite completa**

Run: `... manage.py test`
Expected: OK, sin fallos nuevos.

- [ ] **Step 5: Commit**

```bash
git add templates/users/login.html users/tests.py
git commit -m "feat: enlace de regreso al inicio desde el login"
```

## Self-Review

- Cobertura del spec: rutas (Task 2), estructura y contenido (Task 2), paleta y accesibilidad
  (Task 2), assets e imágenes (Task 1), enlace de regreso (Task 3), pruebas (todas las tareas).
- Sin placeholders: cada paso tiene archivo, valor o comando concreto.
- Consistencia: el nombre `landing` se usa igual en rutas, template y tests; los assets de Task 1
  son los que referencia Task 2.
- Fuera de alcance respetado: no se toca el diseño del login salvo el enlace.
