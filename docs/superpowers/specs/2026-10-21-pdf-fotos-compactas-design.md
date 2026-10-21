# Fotos compactas en el PDF de la orden (FT-GM-01)

Fecha: 2026-10-21
Estado: aprobado para implementación

## Objetivo

Reducir el consumo de papel del informe PDF: presentar las fotos en una cuadrícula
compacta de dos columnas, con máximo 2 fotos ANTES y 2 fotos DESPUÉS por equipo, en
tamaño carta, sin cambiar el resto del contenido ni la funcionalidad de fotos.

## Contexto actual

- `PDFOrdenView` (`operations/views.py:815`) arma el contexto y renderiza
  `templates/operations/reporte_pdf_aa.html` con xhtml2pdf (pisa).
- Hoy cada foto se dibuja a 150 mm de ancho, apilada verticalmente en bloques ANTES y
  DESPUÉS, por cada equipo intervenido. Una orden con varias fotos ocupa muchas páginas.
- `@page` está en A4.
- `MAX_FOTOS_POR_MOMENTO = 3` (`operations/models.py:10`), por lo que la app permite
  subir hasta 3 fotos por etapa.

## Decisiones

1. Tamaño de página: carta (Letter), `@page { size: letter }`.
2. Límite de fotos: 2 por etapa (ANTES y DESPUÉS). Se cambia
   `MAX_FOTOS_POR_MOMENTO = 2`. El contador y los mensajes ya leen la constante, así que
   se ajustan solos.
3. Distribución por equipo: después de sus datos y observaciones, barra
   "REGISTRO FOTOGRÁFICO", luego caja ANTES con hasta 2 fotos en una fila de dos
   columnas y caja DESPUÉS con el mismo esquema. Después sigue el siguiente equipo.
4. Implementación con tablas HTML. xhtml2pdf no soporta flexbox ni grid y las tablas son
   el mecanismo confiable; el resto del informe ya usa tablas.
5. Imágenes: ancho de celda (aproximadamente 95 mm en carta con márgenes laterales de
   10 mm), alto automático para conservar la proporción original, borde fino. Sin
   deformación.
6. Fotos heredadas: si una orden antigua tiene 3 fotos por etapa, se muestran todas; la
   tercera cae sola en una fila adicional con el mismo diseño. No se borran fotos ni se
   crean páginas con encabezados de continuación.
7. Sin captions ni numeración adicionales.
8. No se toca el resto del informe (encabezado, datos generales, actividades, mediciones,
   observaciones, pie) ni la carga, borrado o asociación de fotos.

## Archivos afectados

- `operations/models.py`: constante `MAX_FOTOS_POR_MOMENTO`.
- `templates/operations/reporte_pdf_aa.html`: `@page` y sección de registro fotográfico.
- `operations/tests.py`: tests nuevos del límite, tamaño de página y cuadrícula.

## Criterios de aceptación

1. El PDF se genera en carta (612 x 792 pt) y es legible en pantalla y al imprimir.
2. Se ven hasta 2 fotos ANTES y 2 DESPUÉS por equipo, en dos columnas, con su proporción
   original.
3. Los encabezados ANTES y DESPUÉS son claramente identificables y no se separan de sus
   fotos.
4. El PDF usa menos páginas que antes con la misma cantidad de fotos.
5. Ninguna imagen queda cortada, superpuesta o fuera de márgenes; no hay páginas casi
   vacías.
6. La app limita la subida a 2 fotos por etapa, con validación y contador coherentes.
7. Los tests existentes de PDF y fotos siguen pasando.

## Validación

- Tests automáticos en `operations/tests.py`: límite de 2 por etapa, tamaño carta medido
  con pypdf, cuadrícula de dos columnas en el HTML renderizado y que 4 fotos no agreguen
  más de una página respecto a la misma orden sin fotos.
- PDF de prueba local con una orden de 4 fotos (2 y 2), revisado visualmente y medido con
  pypdf.

## Fuera de alcance

- Rediseño general del informe o cambios en el contenido técnico.
- Cambios en la subida, recorte o almacenamiento de fotos.
- El botón "Cancelar" en correctivos (tarea aparte, pendiente).
