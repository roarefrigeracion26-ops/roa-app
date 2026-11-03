# Gestión in-app y supervisores por empresa — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el admin ROA gestione empresas, sedes y supervisores desde la app, restringir a cada supervisor a sus empresas y agregar filtro por empresa al dashboard.

**Architecture:** Nueva M2M `Tecnico.empresas_visibles`; helpers de permisos y middleware para supervisores; scoping del queryset de reportes; nueva app `gestion` con CRUD staff-only y botón en el header.

**Tech Stack:** Django 5.2, SQLite/PostgreSQL, Bootstrap 5, tests de Django.

## Global Constraints

- No ejecutar `migrate` contra la base real desde desarrollo; las migraciones se aplican al desplegar.
- No borrar empresas/sedes: usar `activo`.
- El admin ROA (`is_staff`/`is_superuser`) siempre ve todo.
- Supervisores de cliente: solo `/reportes/` y su exportación.
- Mantener el flujo actual de técnicos.
- Ejecutar tests con `venv\Scripts\python.exe manage.py test`.

---

### Task 1: Modelo `empresas_visibles` y migraciones

**Files:**
- Modify: `users/models.py`
- Create: `users/migrations/0002_tecnico_empresas_visibles.py`
- Modify: `users/admin.py`
- Test: `users/tests.py`

**Interfaces:**
- Produces: `Tecnico.empresas_visibles` (M2M a `inventory.Empresa`, related_name `supervisores`).

- [ ] **Step 1: Escribir test de asignación**

```python
def test_supervisor_puede_tener_empresas_visibles(self):
    empresa = Empresa.objects.create(nombre='Empresa Test')
    supervisor = Tecnico.objects.create_user(
        username='sup_test', password='clave123', rol='supervisor'
    )
    supervisor.empresas_visibles.add(empresa)
    self.assertIn(empresa, supervisor.empresas_visibles.all())
```

- [ ] **Step 2: Ejecutar test y verificar que falla**

Run: `venv\Scripts\python.exe manage.py test users.tests`
Expected: FAIL por campo inexistente.

- [ ] **Step 3: Implementar M2M y migraciones**

Agregar el campo, generar migración de esquema y migración de datos que asigne todas las
empresas existentes a los usuarios con `rol='supervisor'`.

- [ ] **Step 4: Ejecutar test**

Run: `venv\Scripts\python.exe manage.py test users.tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add users/models.py users/migrations users/admin.py users/tests.py
git commit -m "feat(users): add empresas visibles for supervisors"
```

---

### Task 2: Permisos, mixin y middleware

**Files:**
- Create: `users/permissions.py`
- Create: `users/middleware.py`
- Modify: `users/mixins.py`
- Modify: `config/settings.py`
- Test: `users/tests.py`

**Interfaces:**
- Produces: `es_admin_roa(user)`, `empresas_visibles(user)`, `StaffRequiredMixin`,
  `RestringirSupervisoresMiddleware`.

- [ ] **Step 1: Escribir tests**

- Admin ROA obtiene todas las empresas activas.
- Supervisor obtiene solo sus empresas activas.
- Técnico obtiene queryset vacío.
- Supervisor no-staff es redirigido de `/empresas/` a `/reportes/`.
- Supervisor no-staff accede a `/reportes/`.
- Staff con rol supervisor accede a `/empresas/`.

- [ ] **Step 2: Verificar que fallan**

Run: `venv\Scripts\python.exe manage.py test users.tests analytics.tests`
Expected: FAIL/ImportError.

- [ ] **Step 3: Implementar helpers, mixin y middleware**

`empresas_visibles`: todas si admin; asignadas y activas si supervisor; vacío si técnico.
Middleware después de `AuthenticationMiddleware`, con allowlist de reportes/login/logout/estáticos.

- [ ] **Step 4: Verificar**

Run: `venv\Scripts\python.exe manage.py test users.tests analytics.tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add users/permissions.py users/middleware.py users/mixins.py config/settings.py users/tests.py analytics/tests.py
git commit -m "feat(users): restrict client supervisors to scoped reports"
```

---

### Task 3: Scoping y filtro Empresa en analytics

**Files:**
- Modify: `analytics/views.py`
- Modify: `templates/analytics/dashboard.html`
- Create: `analytics/tests.py`

**Interfaces:**
- Consumes: `empresas_visibles(user)`.
- Produces: GET `empresa`, contexto `empresas`, `empresa_seleccionada`.

- [ ] **Step 1: Escribir tests de analytics**

- Supervisor ve solo órdenes de su empresa.
- Admin ve órdenes de todas las empresas.
- Filtro `empresa` limita la tabla.
- Filtro `cliente` sigue funcionando dentro de la empresa.
- CSV de supervisor solo contiene sus órdenes.
- MTTR no incluye correctivos de otras empresas.

- [ ] **Step 2: Verificar que fallan**

Run: `venv\Scripts\python.exe manage.py test analytics.tests`
Expected: FAIL (sin scoping ni filtro empresa).

- [ ] **Step 3: Implementar scoping, filtros y plantilla**

Filtrar el queryset base por empresas visibles; agregar `empresa`; limitar sedes/equipos;
aplicar el mismo alcance y fechas al MTTR; agregar selector Empresa y renombrar Cliente→Sede;
ocultar PDF a supervisores no-staff.

- [ ] **Step 4: Verificar**

Run: `venv\Scripts\python.exe manage.py test analytics.tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analytics/views.py analytics/tests.py templates/analytics/dashboard.html
git commit -m "feat(analytics): scope reports and add empresa filter"
```

---

### Task 4: App `gestion` y CRUD

**Files:**
- Create: `gestion/__init__.py`, `gestion/apps.py`, `gestion/forms.py`,
  `gestion/views.py`, `gestion/urls.py`, `gestion/tests.py`
- Create: `templates/gestion/*.html`
- Modify: `config/settings.py`, `config/urls.py`, `templates/base.html`

**Interfaces:**
- Consumes: `Empresa`, `Cliente`, `Tecnico`, `StaffRequiredMixin`.
- Produces: namespace `gestion` con índice, CRUD de empresas/sedes/supervisores.

- [ ] **Step 1: Escribir tests de acceso y CRUD**

- Técnico/supervisor no-staff reciben redirección en `/gestion/`.
- Staff accede a índice, listados y formularios.
- Crear empresa, sede y supervisor con empresas asignadas.
- Editar asignaciones y activar/desactivar.

- [ ] **Step 2: Verificar que fallan**

Run: `venv\Scripts\python.exe manage.py test gestion.tests`
Expected: FAIL por app/URL inexistente.

- [ ] **Step 3: Implementar app, formularios, vistas, URLs y plantillas**

Formularios con `enctype="multipart/form-data"` para logo; creación de supervisor con
`UserCreationForm` y asignación obligatoria de al menos una empresa; botón Gestión en header.

- [ ] **Step 4: Verificar**

Run: `venv\Scripts\python.exe manage.py test gestion.tests`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gestion templates/gestion config/settings.py config/urls.py templates/base.html
git commit -m "feat(gestion): add in-app management for empresas sedes and supervisors"
```

---

### Task 5: Verificación integral

**Files:**
- Modify según hallazgos.

- [ ] **Step 1: Checks**

```bash
venv\Scripts\python.exe manage.py check
venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

- [ ] **Step 2: Suite completa**

```bash
venv\Scripts\python.exe manage.py test
```

Expected: 0 failures.

- [ ] **Step 3: Revisión de código**

Dispatch subagent reviewer against the branch diff; fix Critical/Important findings.

- [ ] **Step 4: Commit final y push**

```bash
git add -A
git commit -m "test: verify gestion and supervisor scoping"
git push -u origin feature/gestion-supervisores
```
