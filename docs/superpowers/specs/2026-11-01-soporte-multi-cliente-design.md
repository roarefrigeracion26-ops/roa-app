# Diseño Técnico: Soporte Multi-Cliente (Empresas y Sedes) para ROA

- **Fecha:** 2026-11-01
- **Estado:** Propuesto (Pendiente de aprobación)
- **Alcance:** Proyecto (App `inventory`, `operations`, plantillas y flujos móviles)

---

## 1. Contexto e Intención

ROA Refrigeración Ingeniería S.A.S. presta servicios técnicos de mantenimiento preventivo y correctivo para sistemas de Aire Acondicionado y Refrigeración Comercial. La aplicación (`roa-app`) se desarrolló inicialmente orientada a la operación con **Supertiendas Olímpica S.A.**, por lo que varios modelos y pantallas asumían que:
1. Toda sede era una tienda con código numérico obligatorio (ej. 1059).
2. El radicado de la orden de servicio seguía estrictamente el formato `MP` o `MC` seguido de números.
3. El cliente en los encabezados y reportes era siempre Olímpica.

ROA atiende actualmente a **tres clientes comerciales** (Olímpica y dos empresas adicionales). Este proyecto adapta la arquitectura para que ROA gestione múltiples empresas clientes y sus respectivas sedes de forma organizada, sin alterar su estándar de calidad operativa ni el formato documental de reporte.

---

## 2. Objetivos, No-Objetivos y Anti-Objetivos

### Objetivos
- **Jerarquía Empresa → Sedes:** Permitir que cada empresa cliente tenga su propio conjunto de sedes, tiendas o sucursales.
- **Códigos flexibles de sede:** El identificador o código de sede pasa a ser opcional y alfanumérico (ej. "SEDE-NORTE", "1059" o vacío), identificando la sede por nombre y dirección cuando no tenga código.
- **Flujo móvil intuitivo en 2 pasos:** El técnico primero selecciona la Empresa (evitando mezclar sedes de distintos clientes) y luego visualiza las sedes de esa empresa con buscador.
- **Radicado manual flexible:** El técnico digita el número/código de orden según el formato físico o talonario propio de cada cliente.
- **Reporte FT-GM-01 unificado:** Mantener el formato estándar de ROA (`FT-GM-01`, versión 01) con logo ROA y las 10 actividades preventivas fijas, reflejando en el encabezado el nombre de la Empresa en "Cliente" y el nombre/dirección de la sede en "Dir. Cliente".
- **Migración sin pérdida de datos:** Preservar intactas las tiendas y órdenes históricas de Olímpica asociándolas automáticamente a una empresa por defecto "Olímpica S.A.".

### No-Objetivos
- **Multi-inquilino con accesos externos:** Los usuarios de la app son exclusivamente técnicos y supervisores de ROA. No hay portal para usuarios de las empresas clientes.
- **Checklists dinámicos por empresa:** Las 10 actividades preventivas son el estándar de calidad de ROA y aplican a todos los clientes.
- **Firmas digitales en cliente:** Se descartaron por ahora para evitar mantenimiento de catálogos de personal autorizado por empresa.
- **Asignación exclusiva de técnicos:** Todo técnico de ROA puede atender sedes de cualquiera de las empresas.

### Anti-Objetivos
- **Lista plana combinada:** Mostrar sedes de diferentes empresas en una misma lista sin filtrar, lo cual generaría confusiones operativas al técnico.
- **Ruptura de compatibilidad:** Modificar drásticamente las claves foráneas existentes en `OrdenServicio` y `EquipoAA` que obligue a migraciones destructivas.

---

## 3. Enfoques Considerados

### Enfoque 1: Modelo `Empresa` + `Sede` (Seleccionado)
- Se crea una entidad `Empresa` en `inventory/models.py`.
- El modelo actual `Cliente` se relaciona con `Empresa` (`empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT)`).
- `codigo` en `Cliente` pasa a `CharField(max_length=50, blank=True, null=True, unique=False)`.
- El flujo móvil separa: `/empresas/` → `/empresa/<id>/sedes/` → `/sedes/<id>/equipos/`.
- **Razón de elección:** Proporciona integridad referencial limpia, escalabilidad para agregar clientes futuros desde el panel administrativo y coincide con la navegación solicitada por el usuario.

### Enfoque 2: Campo `empresa` plano en el modelo `Cliente` (Descartado)
- Solo agregar un `CharField` con el nombre de la empresa en cada registro.
- **Razón de descarte:** Propenso a errores tipográficos, dificulta la administración centralizada y limita futuras configuraciones específicas por empresa (ej. logos secundarios o datos fiscales).

---

## 4. Decisiones Acordadas con el Usuario

1. **Jerarquía:** 2 niveles (Empresa → Sedes). El técnico selecciona primero la empresa para ver sus sedes.
2. **Códigos de sede:** Opcionales y flexibles. Si no existe código, la sede se identifica por su nombre y dirección.
3. **Flujo técnico:** El flujo operativo se mantiene idéntico tras elegir la sede:
   - "Iniciar Preventivo MP de Sede" (orden global a nivel de sede).
   - "Mantenimiento Correctivo (MC)" seleccionando un equipo específico.
4. **Radicados:** Cada empresa maneja su propia nomenclatura. El técnico ingresa el radicado manualmente.
5. **Actividades preventivas:** Se mantienen las 10 actividades estándar de ROA para todos los clientes.
6. **Equipos y mediciones:** Se mantienen los mismos tipos (UCA con circuitos A/B, UMA/Split con temperaturas, Condensadora Rack con corrientes/presiones).
7. **Reporte PDF:** Se mantiene FT-GM-01 versión 01 con logo de ROA.
8. **Técnicos:** Sin restricciones por empresa; cualquier técnico atiende cualquier sede.

---

## 5. Diseño Detallado de Componentes

### 5.1 Modelos de Datos (`inventory/models.py`)

```python
class Empresa(models.Model):
    """Empresa cliente a la que ROA presta servicios (ej. Olímpica S.A., Éxito, etc.)."""
    nombre = models.CharField(max_length=200, unique=True)
    nit = models.CharField(max_length=50, blank=True)
    logo = models.ImageField(
        upload_to='empresas/logos/', blank=True, null=True,
        verbose_name='Logo de la empresa',
        help_text='Logo corporativo para mostrar en las tarjetas de selección.'
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    """
    Sede, tienda o sucursal de una Empresa donde están instalados los equipos.
    Se mantiene el nombre de clase Cliente para compatibilidad con EquipoAA y OrdenServicio.
    """
    empresa = models.ForeignKey(
        Empresa, on_delete=models.PROTECT, related_name='sedes',
        null=True, blank=True # Nullable temporalmente durante la migración
    )
    codigo = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name='Código de sede/tienda',
        help_text='Opcional. Ej: 1059 para Olímpica o alfanumérico.'
    )
    nombre = models.CharField(max_length=200, verbose_name='Nombre de la sede')
    dir_cliente = models.CharField(max_length=300, blank=True, verbose_name='Dirección')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Sede / Tienda'
        verbose_name_plural = 'Sedes / Tiendas'
        ordering = ['empresa', 'nombre']

    def __str__(self):
        prefijo = f'[{self.codigo}] ' if self.codigo else ''
        empresa_nom = f' — {self.empresa.nombre}' if self.empresa else ''
        return f'{prefijo}{self.nombre}{empresa_nom}'
```

### 5.2 Migración de Datos
1. Migración de esquema: Crear `Empresa` (con campo `logo`), agregar campo `empresa` (nullable) a `Cliente`, alterar `codigo` de `IntegerField(unique=True)` a `CharField(blank=True)`.
2. Migración de datos: Crear automáticamente la `Empresa` con nombre `"OLIMPICA S.A."` y asociarle el logo existente si está disponible, vinculando todos los registros existentes de `Cliente` a dicha empresa.
3. Ajuste de esquema: Marcar `empresa` como no nula (`null=False`).

### 5.3 Formularios y Radicados (`operations/forms.py`)
- Modificar `NuevaOrdenForm`:
  - `radicado`: Pasa a ser un campo de texto completo (`CharField(max_length=30)`), con sugerencia o ayuda según la empresa, pero permitiendo cualquier radicado (ej. `MP9167`, `MC0452`, `OT-1029`).
  - `cliente_nombre`: Se autocompleta con `sede.empresa.nombre`.
  - `dir_cliente`: Se autocompleta con `f"{sede.nombre} — {sede.dir_cliente}"` o el formato que corresponda si tiene código.
- Modificar `NuevaOrdenClienteForm`:
  - Para preventivos de sede, ya no asume obligatoriamente el prefijo 'MP', sino que permite radicar con el código correspondiente.

### 5.4 Vistas, Rutas y Experiencia Móvil
- **Nueva pantalla interactiva `/empresas/` (`EmpresaListView`):**
  - **Cards visuales interactivas:** Cada empresa se presenta como una tarjeta táctil atractiva con sombra suave, esquinas redondeadas y micro-animación al pulsar/hover.
  - **Logo corporativo:** Muestra el logo subido por el administrador desde el panel con tamaño optimizado y fondo blanco neutro. Si la empresa no tiene logo aún, muestra un avatar con las iniciales y el color institucional de ROA.
  - **Contador de sedes:** Muestra cuántas sedes activas tiene registradas cada cliente (ej. "14 sedes registradas").
  - **Alerta de órdenes abiertas:** Si el técnico tiene un MP o MC abierto en cualquier empresa, se destaca en la parte superior para retomarlo rápidamente.
- **Pantalla de Sedes `/empresa/<int:empresa_id>/sedes/` (`SedesEmpresaView`):**
  - Encabezado con el logo o nombre de la empresa seleccionada y botón para volver a Empresas.
  - Buscador reactivo en tiempo real por nombre o código de tienda.
  - Al tocar una sede, pasa a la vista de equipos y preventivo de esa sede (`EquiposClienteView`).
- **Redirección post-login:**
  - Si el técnico tiene una orden abierta, va directamente a ella.
  - Si no tiene orden abierta, se le dirige a `/empresas/` para seleccionar el cliente con el que va a trabajar.
- **Panel de Administración (`inventory/admin.py`):**
  - Formulario con subida y previsualización del logo corporativo de la empresa.
  - Sedes gestionables como `inline` tabular dentro de la misma pantalla de la Empresa para facilitar altas masivas.

### 5.5 Reporte PDF (`templates/operations/reporte_pdf_aa.html`)
- Encabezado:
  - `Cliente:` muestra `orden.cliente_nombre` (la Razón Social de la Empresa, ej. "OLIMPICA S.A.").
  - `Dir. Cliente:` muestra `orden.dir_cliente` (la Sede y Dirección).
  - `Radicado No.:` muestra el radicado tal cual fue digitado.
  - Formato `FT-GM-01` Versión `01` y logo ROA inalterados.

---

## 6. Lo que queda a discreción del Constructor (Builder)
- Diseño CSS específico de las tarjetas de selección de empresa (usando la paleta ROA azul/dorado ya existente).
- Mensajes de validación y placeholders dinámicos en el formulario de orden.
- Configuración en el Django Admin para gestionar Empresas con sus Sedes en `inlines` para mayor comodidad administrativa.
- Actualización de los tests automatizados en `operations/tests.py` y `inventory/tests.py` para reflejar la relación con Empresa.

---

## 7. Plan de Verificación
1. **Tests unitarios:**
   - Ejecutar suite de pruebas de `inventory` y `operations` verificando que no haya regresiones.
   - Probar creación de orden con radicado alfanumérico para distintas empresas.
2. **Navegación móvil:**
   - Login de técnico → Selección de Empresa → Selección de Sede → Inicio de Preventivo o Correctivo.
3. **Generación de PDF:**
   - Verificar que el PDF renderice correctamente con datos de diferentes empresas sin desbordamientos de página.
