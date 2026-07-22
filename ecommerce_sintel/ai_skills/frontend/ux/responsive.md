---
description: Breakpoints y comportamiento responsive del panel admin (desktop-first).
metadata:
  domain: ux
  supersedes: FRONTEND_UI_RULES.md (seccion 8)
---

# Responsive

El panel admin es **desktop-first**. Los breakpoints relevantes:

| Breakpoint | Comportamiento |
|---|---|
| `< lg` (< 992px) | Sidebar se oculta (`d-none d-lg-flex`), aparece hamburger en Navbar |
| `< lg` | Sidebar mobile usa offcanvas Bootstrap (`offcanvas offcanvas-start bg-black`) |
| Formularios | `row g-2` con `col-6`, `col-8`, `col-4` segun el campo |
| Tabla | Siempre dentro de `table-responsive` para scroll horizontal en mobile |

El portal customer (landing, tienda, alquiler, servicios) no tiene una tabla de breakpoints
documentada de forma separada — sigue las mismas convenciones de Bootstrap 5 (`sm`/`md`/`lg`/`xl`)
componente por componente; ver ejemplos en `FeaturedCarousel` (mobile: scroll horizontal snap,
desktop ≥768px: CSS grid) en [../components/cards.md](../components/cards.md#33-modulos-de-negocio).

Layout del shell principal: [../design_system/spacing.md](../design_system/spacing.md).

## Limitacion conocida — selector Desktop/Tablet/Mobile en `/panel/home-config`

El panel de Home Config (`HomeConfigView.vue`) tiene botones para simular
Desktop/Tablet/Mobile en su Vista Previa (`previewDevice`, clases
`.hcb-preview-frame--tablet`/`--mobile`). **Solo encogen el ancho del contenedor** — no crean un
viewport de navegador real. Las `@media (max-width:...)` de los componentes reales
(`HeroSection`, `ModuleGrid`, etc., ver [../components/cards.md](../components/cards.md)) evaluan
el ancho de la ventana del navegador, no el del `<div>` contenedor, asi que seleccionar "Mobile"
en un monitor grande **no** aplica el layout mobile real — solo comprime el layout desktop en una
caja angosta.

**Decision explicita (auditoria `enterprise_sync` Fase 5, 2026-07-11):** no se corrige (opciones
evaluadas: iframe con ancho real, o migrar a CSS Container Queries — ambas descartadas por
costo/riesgo frente al beneficio en ese momento). El selector sirve como referencia aproximada
unicamente. **Para validar responsive real, probar la Landing en `/` directamente en un
viewport/dispositivo real** — desde la Fase 3, Landing y Vista Previa comparten el mismo
`HomeRenderer`, asi que el comportamiento responsive verificado en `/` aplica igual a lo que la
Vista Previa mostraria si tuviera un viewport real. Detalle completo:
[../editor/home_render_audit_2026_07_11.md](../editor/home_render_audit_2026_07_11.md#fase-5--responsive).
