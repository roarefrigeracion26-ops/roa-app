# Fotos por equipo en dos columnas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar las fotos de cada equipo intervenido en dos columnas (Antes a la izquierda, Después a la derecha) en el formulario de intervención.

**Architecture:** Cambio solo de plantilla. La tarjeta de cada equipo pasa de dos bloques apilados a un `row` Bootstrap con dos `col-md-6`. El parcial `_bloque_fotos.html` gana una cabecera de etapa con color de marca y se estira a la altura de la columna.

**Tech Stack:** Django templates, Bootstrap 5.3, CSS de la marca ROA.

## Global Constraints

- Sin em dash en texto nuevo (regla antislop R-02).
- Reutilizar la paleta existente: `--roa-blue` para Antes, `--roa-gold` para Después.
- No tocar vistas, modelo, URLs, JS ni PDF.
- En móvil las columnas se apilan (Antes arriba, Después abajo).

---

### Task 1: Cabecera de etapa y layout de columna en el parcial de fotos

**Files:**
- Modify: `templates/operations/_bloque_fotos.html`
- Modify: `templates/operations/formulario_orden.html` (bloque `extra_css`)

**Interfaces:**
- Consumes: contexto `etapa` (`'antes' | 'despues'`), `titulo`, `count`, `max_fotos`, `fotos`, `momento`, `orden`, `ei`.
- Produces: marcado con clases `.foto-bloque-head`, `.foto-bloque-head--antes`, `.foto-bloque-head--despues`.

- [ ] **Step 1: Añadir estilos en `extra_css`**

```css
.foto-bloque {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
}

.foto-bloque-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #fff;
    padding: 0.4rem 0.65rem;
    border-radius: 7px 7px 0 0;
}

.foto-bloque-head--antes {
    background: var(--roa-blue);
}

.foto-bloque-head--despues {
    background: var(--roa-gold);
}
```

- [ ] **Step 2: Reemplazar la cabecera interna del parcial por la cabecera de etapa**

En `_bloque_fotos.html`, cambiar el `<div class="foto-bloque p-2 mt-2">` y su cabecera por:

```html
<div class="foto-bloque h-100">
    <div class="foto-bloque-head foto-bloque-head--{{ etapa }}">
        <span><i class="bi {% if etapa == 'antes' %}bi-camera{% else %}bi-check2-circle{% endif %} me-1"></i>{{ titulo }}</span>
        <span class="badge bg-light text-dark">{{ count }}/{{ max_fotos }}</span>
    </div>
    <div class="p-2 d-flex flex-column flex-grow-1">
        {# contenido existente: miniaturas o estado vacío, y formulario o alerta #}
    </div>
</div>
```

- [ ] **Step 3: Pasar `etapa` y quitar el toggle de estilos del badge**

Ajustar el cuerpo del parcial para que el bloque interior (miniaturas, formulario, alerta) viva dentro del `div.p-2 ...` y usar `etapa` en la llamada.

- [ ] **Step 4: Verificar en local**

Recargar `http://localhost:8000/orden/1/formulario/` y confirmar cabeceras azul (Antes) y dorada (Después).

- [ ] **Step 5: Commit**

```bash
git add templates/operations/_bloque_fotos.html templates/operations/formulario_orden.html
git commit -m "style: cabecera de etapa en el bloque de fotos"
```

---

### Task 2: Tarjeta de equipo en dos columnas

**Files:**
- Modify: `templates/operations/formulario_orden.html` (bucle `{% for ei in equipos_intervenidos %}`)

**Interfaces:**
- Consumes: `_bloque_fotos.html` con `etapa`.
- Produces: marcado `row g-3` con dos `col-12 col-md-6 d-flex`.

- [ ] **Step 1: Actualizar la prueba de plantilla (falla)**

En `operations/tests.py`, actualizar `test_formulario_renderiza_bloques_de_fotos` para esperar `col-md-6` y los títulos `Antes` y `Después`.

- [ ] **Step 2: Correr la prueba y ver que falla**

Run: `python manage.py test operations.tests.FotosViewsTests.test_formulario_renderiza_bloques_de_fotos`
Expected: FAIL (no encuentra `col-md-6`).

- [ ] **Step 3: Sustituir los dos `{% with %}` por un row de dos columnas**

```html
<div class="row g-3 mt-1">
    <div class="col-12 col-md-6 d-flex">
        {% with fotos=ei.fotos_antes titulo='Antes' etapa='antes' momento=momento_antes count=ei.fotos_antes|length %}
            {% include 'operations/_bloque_fotos.html' %}
        {% endwith %}
    </div>
    <div class="col-12 col-md-6 d-flex">
        {% with fotos=ei.fotos_despues titulo='Después' etapa='despues' momento=momento_despues count=ei.fotos_despues|length %}
            {% include 'operations/_bloque_fotos.html' %}
        {% endwith %}
    </div>
</div>
```

- [ ] **Step 4: Correr la suite**

Run: `python manage.py test operations`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/operations/formulario_orden.html operations/tests.py
git commit -m "style: fotos por equipo en dos columnas (antes/después)"
```

## Self-Review

- Spec: fotos en dos columnas, móvil apilado, marca ROA, solo plantilla. Cubierto por Task 1 y 2.
- Placeholders: ninguno.
- Consistencia: variable `etapa` definida y consumida con los mismos nombres.
