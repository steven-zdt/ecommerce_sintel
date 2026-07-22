---
description: Auditoria real ejecutada 2026-07-11 — fixes puntuales de alto impacto aplicados (SintelOffcanvas, Navbar). NO es certificacion WCAG 2.2 AA completa — sigue habiendo gaps reales sin resolver en ~190 componentes.
metadata:
  domain: ux
  status: auditoria-parcial-fixes-de-alto-impacto-aplicados
---

# Accessibility

> **Sigue sin existir una auditoria WCAG 2.2 AA formal/completa del proyecto.** El 2026-07-11 se
> hizo una pasada real (no exhaustiva) enfocada en el componente de mayor apalancamiento
> (`SintelOffcanvas`, usado por casi todos los modulos CRUD admin) + el chrome global (`Navbar`).
> No se revisaron los ~190 componentes admin uno por uno. No afirmar "cumple WCAG 2.2" — sigue
> siendo falso.

## 1. Fixes aplicados 2026-07-11 (verificados: build + `npm test` en verde)

- **`SintelOffcanvas.vue`** (el componente compartido de mayor impacto — usado por casi todo
  modulo CRUD admin):
  - `role="dialog"`, `aria-modal="true"`, `:aria-label="title"` en el panel.
  - `aria-label="Cerrar"` en el boton `.btn-close` (antes sin nombre accesible).
  - **Manejo de foco real:** al abrir, mueve el foco al panel (`panelEl.focus()`); al cerrar,
    lo devuelve al elemento que disparo la apertura (`document.activeElement` guardado antes de
    abrir). Antes no habia ningun manejo de foco.
  - De paso: se eliminaron 3 `console.log` de debug (`onMounted`/`onUnmounted`/`watch`) que
    quedaron en el componente compartido — no es un fix de accesibilidad, pero estaba ahi mismo.
- **`Navbar.vue`**: `aria-label` en los 3 botones icon-only que no lo tenian (toggle sidebar
  mobile, toggle dark mode, notificaciones) + `aria-hidden="true"` en sus iconos `<i>` (evita que
  el screen reader lea el nombre de la clase del icono ademas del label).

**No incluye** focus-trap completo (Tab no queda atrapado dentro del offcanvas todavia — solo se
mueve el foco inicial y se restaura al cerrar) — un focus trap real (evitar que Tab escape del
panel mientras esta abierto) queda pendiente.

## 2. Lo que ya existia (baseline heredado, sin cambios)

- Bootstrap 5 provee estados de foco visibles por defecto en inputs/botones.
- Los formularios usan `<label>` asociado a `id` (ver `for="switchId"` en
  [../components/forms.md](../components/forms.md)) en los switches; verificar caso a caso en
  inputs de texto que el `<label>` tenga `for` correcto antes de asumirlo.
- Los spinners de carga (`spinner-border`) llevan `role="status"` en la mayoria de usos
  documentados en [loading_states.md](loading_states.md).
- Botones de accion icon-only en las tablas List (editar/eliminar, ver
  [../components/datatable.md](../components/datatable.md)) llevan `title="..."` — da accessible
  name basico, pero **no** `aria-label` explicito. No se toco (son ~15+ archivos `List.vue`, fuera
  de alcance de esta pasada; `title` SI funciona como accessible-name fallback en la mayoria de
  lectores de pantalla, no es "sin nombre accesible" como se afirmaba antes en este doc, solo es
  menos robusto que `aria-label`).

## 3. Gaps conocidos — no resueltos, no asumir que lo estan

- **Los ~15+ `List.vue` del panel** (BrandList, CategoryList, ProductList, etc.) siguen usando
  solo `title=` en botones icon-only, no `aria-label`. `SintelOffcanvas` (el contenedor) ya tiene
  buen soporte; el contenido especifico de cada modulo no se reviso uno por uno.
- Sin focus-trap completo en `SintelOffcanvas` (ver arriba).
- Sin skip-links ni landmarks ARIA (`role="navigation"`, `role="main"`) en `AppShell`/
  `CustomerLayout`.
- Sin contraste verificado formalmente contra WCAG AA en la paleta de
  [../design_system/colors.md](../design_system/colors.md) (ej. `link-default:
  rgba(255,255,255,.55)` sobre `sidebar-bg: #0a0a0a` no esta medido con una herramienta real).
- Sin navegacion por teclado con flechas en tabs custom
  ([../components/forms.md](../components/forms.md#tabs-dentro-del-offcanvas)) — son `<button>`
  nativos (ayuda con Tab/Enter), pero no siguen el patron ARIA Authoring Practices de flechas
  para tabs.
- El portal customer (landing, tienda, checkout) **no se toco en absoluto** en esta pasada — el
  foco fue exclusivamente el panel admin.

## 4. Que hacer al escribir componentes nuevos

- Preferir HTML semantico nativo (`<button>`, `<label for>`, `<table>`).
- Todo boton icon-only nuevo lleva `aria-label` (no solo `title`) + `aria-hidden="true"` en el
  `<i>` del icono — patron ya aplicado en `Navbar.vue`, copiar de ahi.
- Modales/paneles nuevos tipo dialog: replicar el manejo de foco de `SintelOffcanvas.vue`
  (guardar `document.activeElement`, mover foco al abrir, restaurar al cerrar).
- No afirmar "cumple WCAG 2.2" en ningun PR o doc sin una auditoria real y una herramienta de
  verificacion (axe, Lighthouse) — seguir marcando como pendiente lo que no se ha medido.

## Ver tambien

- [../editor/architecture_audit.md](../editor/architecture_audit.md) — resumen del alcance real
  de esta pasada (parcial, no una certificacion)
