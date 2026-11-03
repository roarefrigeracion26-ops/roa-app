# Levantamiento de Requerimientos: Soporte Multi-Cliente para ROA

Este documento recopila las observaciones técnicas del sistema actual y las decisiones clave para permitir que ROA atienda a sus tres clientes (Olímpica y las dos empresas adicionales) desde la misma aplicación.

> **Instrucciones:** Puedes responder directamente debajo de cada punto en el espacio marcado con `**Tu respuesta:**`. Cuando termines, guarda el archivo y avísame para continuar.

---

## 1. Estructura de Clientes y Sedes (Jerarquía)

### Contexto actual
Hoy el modelo se llama `Cliente`, pero en la práctica guarda tiendas individuales con un "Código de tienda" (ej. Olímpica Calle 72, código 1059).

### Propuesta
Separar en dos niveles:
1. **Empresa (Cliente Comercial):** Olímpica S.A., Empresa 2, Empresa 3.
2. **Sedes / Tiendas:** Las sucursales o puntos de atención pertenecientes a cada empresa.

### Preguntas:
1. ¿Cuáles son los nombres de las otras dos empresas?
2. ¿Te parece bien esta separación de 2 niveles (Empresa -> Sedes) o prefieres mantener una sola lista plana donde el nombre indique la empresa?

**Tu respuesta:**


---

## 2. Códigos de Tienda / Identificación de Sedes

### Contexto actual
El campo `codigo` es un número obligatorio y único en el modelo actual (`unique=True`), pensado para los números de tienda de Olímpica.

### Observación
Las otras empresas pueden no usar códigos numéricos, o podrían repetir números de Olímpica, o usar códigos con letras (alfanuméricos), o simplemente no tener código (solo nombre y dirección).

### Propuesta
Hacer que el código de sede sea **opcional** y no requiera ser numérico ni único a nivel global (único solo si la empresa lo usa). Si una sede no tiene código, se identifica por su nombre y dirección.

### Preguntas:
1. ¿Las otras empresas usan algún identificador o código de sede, o se identifican solo por nombre/dirección?
2. ¿Estás de acuerdo con hacer el código opcional?

**Tu respuesta:**


---

## 3. Flujo del Técnico en el Móvil

### Contexto actual
El técnico hace login y ve directamente la lista de tiendas. Al tocar una tienda, puede:
- "Iniciar Preventivo MP de Tienda"
- O elegir un equipo para "Mantenimiento Correctivo (MC)"

### Preguntas:
1. Al entrar a la app, ¿prefieres que el técnico primero elija la Empresa (ej. botón grande para Olímpica, Empresa 2, Empresa 3) y luego vea sus sedes, o que vea un buscador general donde escriba el nombre o código de la sede?
Seria bueno para no tener en la misma lista sedes de diferentes proveedores, primer haber seleccionado el cliente y segun eso salga su lista de sedes regiustradas en la base de datos
2. ¿El flujo de trabajo sigue siendo igual (Iniciar Preventivo global de sede o Correctivo por equipo individual)?
si

**Tu respuesta:**


---

## 4. Radicados de las Órdenes (MP y MC)

### Contexto actual
Las órdenes tienen un radicado tipo `MP9167` o `MC1234`. El técnico digita los números en un campo de texto con prefijo automático.

### Preguntas:
1. ¿El consecutivo del radicado se maneja de forma global para todo ROA, o cada cliente les exige un consecutivo independiente?
Cada empresa tiene su propio consecutivo pero en olimpica es mp y mc y para las otras empresas es otro tipo de codigo pero la consluion en aque si o si tienen codigo pero en difernete formato
2. ¿El técnico sigue digitando el número de orden de su talonario/formato físico, o te gustaría que el sistema genere el consecutivo automáticamente?
que el tecnico tenga que hacerlo manualmente
**Tu respuesta:**


---

## 5. Actividades del Mantenimiento Preventivo (Checklist)

### Contexto actual
En el archivo `operations/models.py` hay una lista fija de 10 actividades preventivas:
1. Lavado de evaporadores y condensadores
2. Revisión y limpieza de drenaje de bandeja evaporador
3. Revisión y ajuste de correas, ventiladores, poleas y tornillería
4. Revisión y limpieza de contactos y cajas eléctricas
5. Revisión y limpieza de filtros de AA
6. Revisión de fuga de refrigerante y aceite
7. Revisión, limpieza y engrase de rodamientos
8. Revisión funcionamiento de resistencia
9. Revisión de temperaturas de evap. y condensación
10. Revisión de amperajes y voltajes de equipos

### Preguntas:
1. ¿Estas mismas 10 actividades aplican para las otras dos empresas, o cada empresa requiere su propia rutina de actividades?
its ok

**Tu respuesta:**


---

## 6. Tipos de Equipos y Mediciones

### Contexto actual
La aplicación registra equipos de Aire Acondicionado:
- **UCA:** presiones de baja y alta por circuito (A y B) antes y después.
- **UMA / SPLIT:** temperaturas de suministro y retorno antes y después.
- **Condensadora Rack:** presiones, corrientes y temperaturas de lavado de rack.

### Preguntas:
1. Para las otras dos empresas, ¿los servicios son sobre estos mismos tipos de equipos de AA/refrigeración, o manejan equipos distintos que requieran otras mediciones?
los roa manejan AA y refrigeracion asi que sfuen siendo os mismos toos de quipos

**Tu respuesta:**


---

## 7. Formato PDF (FT-GM-01) y Firmas

### Contexto actual
El reporte PDF lleva en el encabezado:
- Logo de ROA
- "ROA REFRIGERACIÓN INGENIERÍA S.A.S."
- Formato: `FT-GM-01`, Versión: `01`
- Cliente: `{{ cliente_nombre }}`
- Dir. Cliente: `{{ dir_cliente }}`

### Preguntas:
1. ¿El código `FT-GM-01` y la versión `01` es el mismo para todos los clientes? si
2. En la casilla "Dir. Cliente" del PDF, ¿qué te gustaría que aparezca exactamente para las otras empresas (ej. "Nombre Sede — Dirección")? si
3. ¿Se requiere incluir firmas digitales o nombres de quien recibe por parte del cliente al cerrar la orden? no por ahora porque si escala la app despues tendremos que actualizar seguido estas personas que firman por empresa

**Tu respuesta:**


---

## 8. Asignación de Técnicos

### Contexto actual
Cualquier técnico registrado puede acceder a cualquier tienda y registrar órdenes. si

### Preguntas:
1. ¿Los técnicos de ROA pueden trabajar indistintamente con cualquiera de los 3 clientes, o hay técnicos asignados exclusivamente a una empresa en particular?
si pueden trabajar indistintamente con cualquiera de los 3 clientes

**Tu respuesta:**

