# Fotos por equipo en dos columnas (Antes | Después)

## Objetivo

En el formulario de intervención, mostrar las fotos de cada equipo
intervenido en dos columnas en lugar de apiladas: izquierda para la etapa
Antes, derecha para la etapa Después.

## Alcance

- Solo la disposición de las fotos dentro de cada tarjeta de equipo.
- No se mueven las mediciones ni ninguna otra sección.
- No se tocan vistas, modelo, URLs ni el PDF.

## Diseño

- En cada tarjeta de equipo, sustituir los dos bloques apilados por un
  `row g-3` con dos columnas `col-12 col-md-6`.
- Columna izquierda: etapa Antes. Columna derecha: etapa Después.
- Reutilizar el parcial existente `operations/_bloque_fotos.html` sin cambios
  de lógica (contador x/3, miniaturas con borrado, botón Agregar foto y
  alerta de máximo).
- En móvil las columnas se apilan: Antes arriba, Después abajo.
- Dar a cada columna una cabecera de color de la marca ROA para distinguir la
  etapa de un vistazo: azul (`--roa-blue`) para Antes, dorado (`--roa-gold`)
  para Después. Contraste de texto verificado.
- Igualar la altura de ambas columnas para evitar saltos visuales.

## Archivos

- `templates/operations/formulario_orden.html` (marcado y `extra_css`).
- `templates/operations/_bloque_fotos.html` (solo si hace falta un gancho de estilo).

## Fuera de alcance

- Reorganizar mediciones por etapa.
- Cambios en el informe PDF.
