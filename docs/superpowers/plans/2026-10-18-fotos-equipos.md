# Fotos de equipos intervenidos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir fotos (máx. 3 por etapa Antes/Después) por equipo intervenido, guardadas en Cloudflare R2, visibles en el PDF FT-GM-01.

**Architecture:** Nuevo modelo `FotoEquipo` ligado a `EquipoIntervenido`. Storage por defecto vía django-storages S3 apuntando a R2 (con fallback a disco local). Compresión y validación con Pillow en un módulo aislado. Vistas POST para subir/eliminar. Plantilla de formulario para capturar y de PDF para mostrar cuadrícula de miniaturas.

**Tech Stack:** Django 5.2, Pillow, django-storages[s3], boto3, Bootstrap 5.

## Global Constraints

- Sin em dash en texto nuevo (regla antislop R-02).
- Nombre de archivo siempre UUID; nunca el nombre original.
- Fotos opcionales; máximo 3 por (equipo, momento).
- Variables R2: `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_REGION=auto`.
- Si faltan variables R2 en dev, usar FileSystemStorage.

---

### Task 1: Configuración de storage

**Files:** `config/settings.py`, `requirements.txt`, `.env.example`

- Añadir `django-storages` y `boto3` a requirements.
- Añadir bloque STORAGES/R2 con fallback local, MEDIA_URL/MEDIA_ROOT, límites de subida.

### Task 2: Modelo FotoEquipo + migración

**Files:** `operations/models.py`, `operations/migrations/0009_fotoequipo.py`

- Modelo con FK, momento, imagen, creada_en.

### Task 3: Procesamiento de imagen y validación

**Files:** `operations/images.py`, `operations/validators.py`

- `procesar_imagen`, `validar_imagen`, límites.

### Task 4: Vistas y URLs

**Files:** `operations/views.py`, `operations/urls.py`, `operations/forms.py`

- `SubirFotosView`, `EliminarFotoView`, `FotoEquipoForm`.

### Task 5: Limpieza y reconciliación

**Files:** `operations/signals.py`, `operations/apps.py`, `operations/management/commands/limpiar_fotos_huerfanas.py`

### Task 6: UI del formulario

**Files:** `templates/operations/formulario_orden.html`

### Task 7: PDF

**Files:** `operations/views.py`, `templates/operations/reporte_pdf_aa.html`

### Task 8: Admin

**Files:** `operations/admin.py`

### Task 9: Tests

**Files:** `operations/tests.py`

### Task 10: Verificación y Delivery Gate
