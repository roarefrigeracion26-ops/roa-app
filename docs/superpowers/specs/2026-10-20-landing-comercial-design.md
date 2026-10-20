# Landing comercial ROA en `/`

Fecha: 2026-10-20
Estado: aprobado para implementación

## Objetivo

Publicar en `/` una landing comercial de ROA Refrigeración basada en la estructura de
roarefrigeracion.com, con la identidad visual de la app, y mover el login del sistema a
`/ingresar/`. La landing es pública; el sistema sigue privado.

## Decisiones

- Una sola página con anclas. No se replican Conócenos, Servicios, Clientes, Descargables ni Contáctanos.
- Estructura comercial con paleta azul de la app, no réplica literal del WordPress 2018.
- Hero estático, sin slider.
- Se reutilizan los logos de clientes y los iconos de servicio del sitio actual.
- Las dos fotos nuevas fueron generadas con Nano Banana y están en `C:\Users\Usuario\Downloads`.
- No se toca el diseño del login salvo un enlace "Volver al inicio".

## Rutas y autenticación

- `config/urls.py`: `path('', TemplateView.as_view(template_name='landing.html'), name='landing')`
  antes de los `include`.
- `users/urls.py`: el login pasa de `''` a `'ingresar/'`.
- `LOGIN_URL`, `LOGIN_REDIRECT_URL` y `LOGOUT_REDIRECT_URL` ya usan nombres, no cambian.
- El botón del navbar apunta a `{% url 'users:login' %}`. Si `user.is_authenticated`, muestra
  "Ir al sistema" hacia el destino por rol que ya usa `base.html`.
- El login incluye un enlace "Volver al inicio" a `/`.
- Rutas internas (`/orden/...`, `/clientes/...`, `/admin/...`) no cambian.

## Estructura y contenido

1. Barra superior: `info@roarefrigeracion.com`, teléfonos y enlace "Ingresar".
2. Header: logo ROA, anclas Servicios, Clientes, Nosotros, Contacto y botón "Ingresar".
3. Hero:
   - Antetítulo: "REFRIGERACIÓN Y CLIMATIZACIÓN"
   - H1: "Aire acondicionado y refrigeración para empresas que no pueden parar"
   - Texto: "Montaje, mantenimiento e instalaciones eléctricas en Barranquilla y el Caribe colombiano."
   - Botones: "Ver servicios" (ancla) e "Ingresar al sistema" (`/ingresar/`).
4. Ofrecemos soluciones: imagen a la izquierda, texto y CTA "Conocer servicios" a la derecha.
   - Texto: "ROA Refrigeración ofrece una amplia gama de soluciones para su empresa o negocio,
     con los estándares técnicos necesarios y valores acordes a sus necesidades."
5. Servicios, lista horizontal numerada:
   - 01 Montaje de equipos: "Instalación de equipos de aire acondicionado y refrigeración para uso comercial e industrial."
   - 02 Reparación y mantenimiento: "Diagnóstico, mantenimiento preventivo y correctivo con repuestos y protocolos de seguridad."
   - 03 Instalaciones eléctricas: "Adecuación y montaje eléctrico para el funcionamiento seguro de sus equipos."
6. Clientes: "Empresas que confían en nosotros" con Éxito, Lasa, Olímpica, Bodytech y Sao.
7. Testimonio: "Nuestros clientes externos e internos gozan de todo nuestro asesoramiento, cuidado
   y preocupación en su desarrollo y crecimiento." Jorge Roa, Mánager Olímpica.
8. Contacto: Calle 91 con 39B, Barranquilla, Colombia. Teléfonos (5) 301 1758, 311 699 1895 y
   301 672 7202. Correo info@roarefrigeracion.com. Enlaces `tel:` y `mailto:`.
9. Footer: "© 2026 ROA Refrigeración. Todos los derechos reservados."

No se inventan años de experiencia, certificaciones ni cifras.

## Sistema visual

- Paleta: azul `#1565C0`, azul medio `#1976D2`, dorado `#8B6914`, fondo `#F5F9FF`, tinta `#1B2733`.
- Titulares en Montserrat 600/700 desde Google Fonts. Cuerpo con la sans del sistema.
- Hero asimétrico: texto a la izquierda sobre degradado azul oscuro, foto a la derecha.
  El degradado debe garantizar contraste AA del texto blanco.
- Secciones con 96 px de aire en escritorio, reglas doradas finas como acento.
- Servicios como lista numerada horizontal, no como tres tarjetas centradas.
- Logos de clientes en gris al 60% de opacidad, a color al pasar el mouse.
- Animación de entrada con `IntersectionObserver`, desactivada con `prefers-reduced-motion`.
- Sin degradados decorativos, sombras difusas ni bordes redondeados en todos los elementos.

## Assets

Se copian al proyecto en `static/landing/` y se optimizan:

- `logo-roa2.jpg` no está accesible (403). El logo de cabecera sale de `static/image/roa-logo.jpeg`.
- Logos de clientes desde `roarefrigeracion.com/wp-content/uploads/2018/03/`:
  `cliente-exito.jpg`, `cliente-lasa.jpg`, `cliente-olimpica.jpg`, `cliente-bodytech.jpg`, `cleinte-sao.jpg`.
- Iconos de servicio: `iconos-home-01.png`, `iconos-home-02.png`, `iconos-home-03.png`.
- Fotos generadas:
  - `Hero.jpg` (1376x768) a `static/landing/hero.jpg`.
  - `Ofrecemos.jpg` (1200x896) a `static/landing/ofrecemos.jpg`.
  - Optimizar a JPEG de calidad 82, lado máximo 1600, sin metadatos.
- El hero generado incluye el logo TRANE en el equipo. Se acepta tal cual por tratarse de un
  equipo real que la empresa interviene. Si el cliente lo objeta, se retoca antes de publicar.

## Responsive, accesibilidad y SEO

- Mobile first: menú colapsable, hero apilado, servicios en vertical, logos en dos filas.
- Contraste AA en texto sobre foto y botones, foco visible, `alt` descriptivo en cada imagen.
- Enlace "Saltar al contenido", un solo `h1` y jerarquía de encabezados correcta.
- `title`: "ROA Refrigeración | Aire acondicionado y refrigeración en Barranquilla".
- `meta description`: "Montaje, mantenimiento e instalaciones eléctricas de refrigeración y aire
  acondicionado en Barranquilla. Ingresa al sistema de seguimiento de actividades."
- Open Graph con la foto del hero y JSON-LD `LocalBusiness` con dirección, teléfono y correo.

## Pruebas

- `GET /` sin sesión responde 200 y contiene el `h1` del hero y el enlace a `/ingresar/`.
- `GET /` no contiene el formulario de login (`id_username`).
- `GET /ingresar/` responde 200 y sí contiene `id_username`.
- Usuario autenticado en `/` ve "Ir al sistema" y no "Ingresar".
- Los archivos referenciados existen en `static/landing/`.
- El login por POST en `/ingresar/` sigue autenticando y redirigiendo por rol.
- La suite completa sigue en verde.

## Fuera de alcance

- Páginas internas del sitio comercial, formulario de contacto, CMS, versión en inglés y analítica.
- Cambios al diseño del login más allá del enlace "Volver al inicio".
- Reemplazo de las fotos generadas por fotos reales de la empresa.

## Riesgos

- Los logos de clientes son marcas de terceros. Se asume autorización de ROA porque ya los usa
  en su sitio actual.
- Las fotos generadas son ilustrativas y no representan necesariamente a empleados reales.
- El logo TRANE dentro del hero puede sugerir una relación de marca; decidir antes de publicar.
