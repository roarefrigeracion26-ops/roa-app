# Soporte Multi-Cliente (Empresas y Sedes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adaptar la aplicación de ROA para soportar múltiples empresas cliente con sus logos corporativos en tarjetas interactivas, organizando sus sedes y flexibilizando los radicados de órdenes de servicio en el flujo móvil y reportes.

**Architecture:** Separación jerárquica en dos niveles mediante el nuevo modelo `Empresa` y relación con `Cliente` (como Sede), migración de datos que preserva el histórico asignándolo a "OLIMPICA S.A.", nueva pantalla móvil interactiva de empresas con cards y logos corporativos, flexibilización de radicado alfanumérico en formularios y ajuste del encabezado de orden en PDF.

**Tech Stack:** Python 3.10+, Django 5.x, Bootstrap 5 / Vanilla CSS, SQLite / PostgreSQL, Pillow, xhtml2pdf.

**Spec:** [docs/superpowers/specs/2026-11-01-soporte-multi-cliente-design.md](file:///c:/Users/Usuario/roa-app/docs/superpowers/specs/2026-11-01-soporte-multi-cliente-design.md)

## Global Constraints

- Preservar la integridad referencial de todas las órdenes de servicio (`OrdenServicio`) y equipos (`EquipoAA`) existentes.
- Migración de datos 100% segura que vincule automáticamente todas las tiendas existentes a la empresa "OLIMPICA S.A.".
- El formato documental `FT-GM-01` Versión `01`, el logo de ROA y las 10 actividades preventivas se mantienen estándar para todas las empresas.
- Todo técnico activo puede acceder y trabajar con cualquier empresa y sede sin restricciones de cuenta.

## Review Focus

- Sede sin código numérico: el sistema debe renderizar sin errores en la lista móvil, selector de orden y reporte PDF mostrando nombre y dirección.
- Radicado alfanumérico con formato libre (ej. `OT-2025-01`, `MC-004`, `9167`): el formulario debe aceptarlo y almacenarlo sin obligar formato estrictamente numérico.
- Empresa sin logo subido: debe mostrar un avatar estilizado con las iniciales de la empresa y color corporativo sin romper el grid de tarjetas.
- Redirección post-login: el técnico debe ser dirigido a `/empresas/` si no tiene órdenes abiertas para elegir el cliente con el que trabajará.
- Administración fluida: el panel de Django Admin debe permitir subir logos y registrar sedes directamente como inlines en la vista de la Empresa.

---

### Task 1: Modelo `Empresa` y migración de datos para `Cliente`

**Files:**
- Modify: `inventory/models.py:1-30`
- Create: `inventory/migrations/000X_empresa_model_and_link.py` (vía `makemigrations` y migración de datos)
- Modify: `inventory/tests.py`

**Interfaces:**
- Produces: Modelo `Empresa` con campos `nombre`, `nit`, `logo`, `activo`, `creado_en`.
- Produces: Modelo `Cliente` con `empresa = ForeignKey(Empresa, on_delete=models.PROTECT, related_name='sedes')` y `codigo = CharField(max_length=50, blank=True, default='')`.

- [ ] **Step 1: Escribir tests de modelo para Empresa y relación con Cliente**

En `inventory/tests.py`, agregar pruebas para:
- Creación de `Empresa` con y sin logo.
- Creación de `Cliente` vinculado a `Empresa` con código alfanumérico y sin código.
- Método `__str__` de `Empresa` y `Cliente`.

- [ ] **Step 2: Ejecutar test para verificar que falla**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: Error `ImportError: cannot import name 'Empresa' from 'inventory.models'`.

- [ ] **Step 3: Implementar modelo `Empresa` y actualizar `Cliente` en `inventory/models.py`**

Definir la clase `Empresa` y agregar el campo `empresa` foráneo y `codigo` flexibilizado en `Cliente` según la especificación técnica.

- [ ] **Step 4: Generar y ejecutar migraciones de esquema y datos**

Generar migración para crear `Empresa` y hacer `empresa` en `Cliente` nullable.
Crear migración de datos que asegure la existencia de la empresa "OLIMPICA S.A." y asigne todas las instancias existentes de `Cliente` a dicha empresa.
Aplicar migraciones: `python manage.py migrate inventory`.

- [ ] **Step 5: Ejecutar tests para verificar que pasan**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: PASS.

- [ ] **Step 6: Commit**

```bash
git add inventory/models.py inventory/migrations/ inventory/tests.py
git commit -m "feat(inventory): add Empresa model and link Cliente as Sede"
```

---

### Task 2: Flexibilización de Radicados y Datos en Órdenes de Servicio

**Files:**
- Modify: `operations/models.py:40-60`
- Modify: `operations/forms.py:50-95`
- Modify: `operations/views.py:126-200`
- Modify: `operations/tests.py`

**Interfaces:**
- Consumes: `Cliente.empresa` de Task 1.
- Produces: `NuevaOrdenForm` y `NuevaOrdenClienteForm` que admiten cualquier radicado alfanumérico ingresado por el técnico y precargan `cliente_nombre = sede.empresa.nombre` y `dir_cliente = f"{sede.nombre} — {sede.dir_cliente}"`.

- [ ] **Step 1: Escribir test para radicado alfanumérico y autocompletado de empresa**

En `operations/tests.py`:
- Probar creación de orden con radicado alfanumérico libre (ej. `OT-9988` o `MC1234`).
- Verificar que `cliente_nombre` tome el nombre de `sede.empresa.nombre`.

- [ ] **Step 2: Ejecutar test para verificar que falla**

Ejecutar: `python manage.py test operations.tests`
Resultado esperado: Falla por validación estricta numérica de radicado o falta de campo en el form.

- [ ] **Step 3: Actualizar `operations/models.py`, `forms.py` y `views.py`**

- En `models.py`: Ampliar `radicado` a `CharField(max_length=30)`.
- En `forms.py`: Actualizar `radicado_numero` o reemplazarlo por `radicado` alfanumérico completo con validación limpia. Eliminar widget quemado `'Ej: OLIMPICA S.A.'` y usar datos de la empresa vinculada.
- En `views.py`: En `NuevaOrdenClienteView` y `NuevaOrdenView`, inicializar `cliente_nombre` con `sede.empresa.nombre` y `dir_cliente` con la información de la sede.

- [ ] **Step 4: Ejecutar tests de operations**

Ejecutar: `python manage.py test operations.tests`
Resultado esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add operations/models.py operations/forms.py operations/views.py operations/tests.py
git commit -m "feat(operations): allow flexible alphanumeric radicado and dynamic client data"
```

---

### Task 3: Pantalla Interactiva de Selección de Empresas (`EmpresaListView`)

**Files:**
- Create: `templates/inventory/empresas.html`
- Modify: `inventory/views.py`
- Modify: `inventory/urls.py`
- Modify: `templates/base.html` (o navbar de navegación)
- Modify: `users/views.py` (o redirección post-login)
- Modify: `inventory/tests.py`

**Interfaces:**
- Consumes: Modelo `Empresa` y método `sedes.filter(activo=True).count()`.
- Produces: Vista `EmpresaListView` en ruta `/empresas/` con renderizado de cards táctiles con logo, conteo de sedes y alerta de órdenes abiertas.

- [ ] **Step 1: Escribir tests para `EmpresaListView`**

En `inventory/tests.py`:
- Verificar que un técnico autenticado reciba status 200 en `/empresas/`.
- Verificar que se listen las empresas activas y se muestre su logo o avatar con iniciales.
- Verificar que órdenes abiertas (preventivo/correctivo) se incluyan en el contexto.

- [ ] **Step 2: Ejecutar test para verificar que falla**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: 404 No Found para la URL `/empresas/`.

- [ ] **Step 3: Implementar `EmpresaListView` y plantilla `empresas.html`**

- En `inventory/views.py`: Crear `EmpresaListView(LoginRequiredMixin, View)` que consulte empresas activas con anotación o conteo de sedes y obtenga órdenes abiertas.
- En `inventory/urls.py`: Registrar `path('empresas/', views.EmpresaListView.as_view(), name='empresas')`.
- En `templates/inventory/empresas.html`: Diseñar el grid de cards interactivas para móvil/escritorio con logo centrado, hover con elevación suave, contador de sedes y fallback de avatar con iniciales cuando no haya imagen.
- En `users/views.py` / `inventory/urls.py`: Configurar la redirección del técnico a `inventory:empresas` tras login cuando no tenga órdenes activas.

- [ ] **Step 4: Ejecutar tests para verificar que pasan**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add inventory/views.py inventory/urls.py templates/inventory/empresas.html inventory/tests.py
git commit -m "feat(inventory): add interactive EmpresaListView with cards and client logos"
```

---

### Task 4: Filtrado de Sedes por Empresa (`SedesEmpresaView`) y Navegación

**Files:**
- Modify: `inventory/views.py`
- Modify: `inventory/urls.py`
- Modify: `templates/inventory/clientes.html`
- Modify: `templates/inventory/equipos_cliente.html`
- Modify: `inventory/tests.py`

**Interfaces:**
- Consumes: `empresa_id` en URL.
- Produces: Vista de sedes filtrada por empresa con botón para volver a Empresas y búsqueda reactiva.

- [ ] **Step 1: Escribir tests para `SedesEmpresaView`**

En `inventory/tests.py`:
- Verificar que al acceder a `/empresa/<empresa_id>/sedes/` solo se muestren las sedes pertenecientes a esa empresa.
- Verificar que se pueda buscar por nombre de sede o código alfanumérico.

- [ ] **Step 2: Ejecutar test para verificar que falla**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: Error o vista no filtrada.

- [ ] **Step 3: Actualizar vista de sedes y plantillas**

- En `inventory/views.py`: Adaptar `ClienteListView` o crear `SedesEmpresaView` para recibir `empresa_id`, cargar la empresa seleccionada y listar exclusivamente sus sedes activas.
- En `templates/inventory/clientes.html`: Agregar barra superior con botón "Volver a Empresas", mostrar el nombre/logo de la empresa activa y mantener el buscador reactivo.
- En `templates/inventory/equipos_cliente.html`: Ajustar el botón "Atrás" para regresar a la lista de sedes de la empresa correspondiente (`inventory:sedes_empresa`).

- [ ] **Step 4: Ejecutar tests**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: PASS.

- [ ] **Step 5: Commit**

```bash
git add inventory/views.py inventory/urls.py templates/inventory/ inventory/tests.py
git commit -m "feat(inventory): filter sedes by selected empresa and polish mobile navigation"
```

---

### Task 5: Panel de Administración de Empresas y Sedes

**Files:**
- Modify: `inventory/admin.py`
- Modify: `inventory/tests.py`

**Interfaces:**
- Consumes: Modelos `Empresa` y `Cliente`.
- Produces: `EmpresaAdmin` con carga/preview de logo y `ClienteInline` tabular.

- [ ] **Step 1: Escribir test para admin de Empresa y Sede**

En `inventory/tests.py`: Probar que un usuario staff puede acceder al changelist y add/change form de `Empresa` y `Cliente` en `/admin/`.

- [ ] **Step 2: Implementar `EmpresaAdmin` y `ClienteInline` en `inventory/admin.py`**

- Registrar `Empresa` en el admin con list_display (`nombre`, `nit`, `activo`, `total_sedes`), list_filter y búsqueda.
- Incluir un `TabularInline` para gestionar sedes dentro de la empresa.
- En `ClienteAdmin`: Mostrar columna `empresa`, permitir filtrar por empresa y buscar por `codigo`, `nombre`, `dir_cliente` y `empresa__nombre`.

- [ ] **Step 3: Ejecutar tests**

Ejecutar: `python manage.py test inventory.tests`
Resultado esperado: PASS.

- [ ] **Step 4: Commit**

```bash
git add inventory/admin.py inventory/tests.py
git commit -m "feat(inventory): configure EmpresaAdmin with logo preview and tabular sedes inlines"
```

---

### Task 6: Verificación Integral del Reporte PDF y Suite Completa de Tests

**Files:**
- Modify: `templates/operations/reporte_pdf_aa.html` (si requiere pulir visualización de sede/empresa)
- Modify: `operations/tests.py`

**Interfaces:**
- Consumes: `OrdenServicio` con datos de empresa y sede.
- Produces: PDF FT-GM-01 renderizado correctamente para sedes con y sin código numérico.

- [ ] **Step 1: Escribir test de generación de PDF para múltiples empresas**

En `operations/tests.py`:
- Generar PDF para una orden de "OLIMPICA S.A." con código de tienda.
- Generar PDF para una orden de una empresa diferente sin código de tienda.
- Verificar que ambos PDFs comiencen con `%PDF-` y contengan la información esperada sin errores de desbordamiento.

- [ ] **Step 2: Ejecutar test de PDF y suite completa**

Ejecutar: `python manage.py test`
Resultado esperado: Todos los tests del proyecto (inventory, operations, users, analytics) pasan exitosamente.

- [ ] **Step 3: Commit final de verificación**

```bash
git add templates/operations/reporte_pdf_aa.html operations/tests.py
git commit -m "test(operations): verify PDF generation and run full test suite for multi-client support"
```
