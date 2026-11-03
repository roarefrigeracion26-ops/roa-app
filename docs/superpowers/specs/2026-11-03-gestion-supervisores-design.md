# Diseño: Gestión in-app, supervisores por empresa y filtro de servicios

- **Fecha:** 2026-11-03
- **Estado:** Aprobado
- **Alcance:** `users`, `analytics`, nueva app `gestion`, plantillas y navegación

## 1. Contexto

La app ya soporta múltiples empresas (`Empresa`) y sedes (`Cliente`). Hoy:

- La administración de empresas, sedes y usuarios se hace en `/admin/` de Django.
- Los supervisores de clientes ven **todas** las órdenes de todas las empresas.
- El dashboard filtra por sede (`cliente`), pero no por empresa cliente.
- Los supervisores pueden acceder a inventario y operaciones por URL directa.

La base actual tiene **8 supervisores** y **1 empresa** (`OLIMPICA S.A.`).

## 2. Decisiones acordadas

1. La gestión de empresas, sedes y supervisores se hace **dentro de la app**, no en `/admin/`.
2. Solo el **admin interno ROA** (`is_staff` o `is_superuser`) puede gestionar.
3. Cada supervisor se asigna a una o varias **empresas visibles**.
4. Un supervisor de cliente solo accede a **reportes** (`/reportes/`) y su exportación.
5. La tabla de servicios agrega filtro por **Empresa** y conserva el filtro por **Sede**.
6. Los supervisores existentes se asignan a `OLIMPICA S.A.` durante la migración.
7. El admin ROA siempre ve todas las empresas, sin depender de asignaciones.
8. No se eliminan empresas/sedes: se activan o desactivan (`activo`).

## 3. Modelo de datos

En `users.Tecnico`:

```python
empresas_visibles = models.ManyToManyField(
    'inventory.Empresa',
    blank=True,
    related_name='supervisores',
    verbose_name='Empresas visibles',
)
```

Migración de datos: asignar todas las empresas existentes a todos los usuarios con
`rol='supervisor'`. Con la base actual esto equivale a `OLIMPICA S.A.` para los 8
supervisores.

## 4. Reglas de acceso

### 4.1 Admin ROA

- `is_staff` o `is_superuser`: acceso a toda la app y a `/gestion/`.
- Ve todas las empresas en reportes aunque no tenga asignaciones.

### 4.2 Supervisor de cliente

- Solo puede acceder a `/reportes/`, `/reportes/exportar/`, login/logout y archivos estáticos.
- Cualquier otra ruta lo redirige a `/reportes/` mediante middleware.
- En reportes solo ve órdenes de sus `empresas_visibles` activas.
- No ve enlaces de PDF de órdenes.

### 4.3 Técnico

- Sin cambios en su flujo actual.
- No accede a `/gestion/`.

## 5. Dashboard de reportes

- El queryset base se limita a las empresas visibles del usuario.
- Filtro nuevo `empresa` (GET) y filtro existente `cliente` (Sede) renombrado en la UI.
- Al elegir empresa, el selector de sedes y equipos se limita a esa empresa.
- MTTR usa el mismo alcance de empresa y respeta las fechas seleccionadas.
- La exportación CSV reutiliza el queryset filtrado.

## 6. Gestión in-app (`/gestion/`)

Rutas principales:

| Ruta | Función |
|---|---|
| `/gestion/` | Resumen y accesos rápidos |
| `/gestion/empresas/` | Listado de empresas |
| `/gestion/empresas/nueva/` | Crear empresa (nombre, NIT, logo, activo) |
| `/gestion/empresas/<id>/editar/` | Editar empresa |
| `/gestion/sedes/` | Listado de sedes, filtrable por empresa |
| `/gestion/sedes/nueva/` | Crear sede |
| `/gestion/sedes/<id>/editar/` | Editar sede |
| `/gestion/supervisores/` | Listado de supervisores |
| `/gestion/supervisores/nuevo/` | Crear supervisor y asignar empresas |
| `/gestion/supervisores/<id>/editar/` | Editar supervisor y asignaciones |

- Todas las vistas requieren staff/superusuario.
- Se usa `base.html` con una pestaña/botón **Gestión** visible solo para staff.
- Se muestran mensajes de éxito y errores de formulario.
- Activación/desactivación por POST, sin borrado físico.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Supervisor accede por URL directa | Middleware centralizado, no solo ocultar botones |
| Órdenes históricas sin empresa | Filtro por relaciones `cliente__empresa` / `equipo__cliente__empresa` |
| Supervisor sin asignaciones | Ve cero datos; el formulario in-app exige al menos una empresa |
| Empresa con sedes/órdenes | `PROTECT`; se desactiva en vez de borrar |
| Admin con `rol='tecnico'` | El mixin de reportes acepta staff/superusuario |

## 8. Verificación

- Tests de modelo, permisos, middleware, scoping, filtros, export y CRUD.
- `manage.py check`
- `makemigrations --check --dry-run`
- Suite completa de tests.
- Verificación manual con admin y supervisor.
