# Fotos de equipos intervenidos (Antes/Después) en el PDF

## Objetivo

Permitir tomar hasta 3 fotos por etapa (Antes y Después) para cada equipo
intervenido en una orden, almacenarlas en Cloudflare R2 (bucket privado) y
mostrarlas en el informe PDF FT-GM-01.

## Decisiones

- Datos: PostgreSQL en Supabase (sin cambios).
- Fotos: Cloudflare R2, bucket privado, S3-compatible, vía django-storages + boto3.
- Compresión con Pillow antes de subir (máx. 1600 px, JPEG q80, sin EXIF/GPS).
- Fotos por etapa: máximo 3. Fotos opcionales (no bloquean el cierre).
- Bucket privado con URLs firmadas.

## Modelo

`FotoEquipo` en la app `operations`:
- `equipo_intervenido` FK a `EquipoIntervenido` (CASCADE, related_name `fotos`)
- `momento` = ANTES | DESPUES
- `imagen` ImageField sobre el storage por defecto
- `creada_en` auto_now_add

## Validaciones

- Servidor: auth y propiedad, orden abierta, equipo pertenece a la orden,
  momento válido, conteo <= 3, imagen real (Pillow verify), tamaño <= 10 MB,
  content-type permitido, nombre UUID.
- Cliente: tipo/tamaño, conteo, compresión en canvas, estados de UI.

## Limpieza (fotos huérfanas)

- `post_delete` en `FotoEquipo` borra el objeto en R2, diferido con
  `transaction.on_commit`.
- Subida atómica: si falla la fila tras subir el archivo, se borra el archivo.
- Comando `limpiar_fotos_huerfanas` para reconciliar bucket vs base de datos.

## Fuera de alcance

- Cola offline / reintento con mala señal.
