---
description: Layout del shell principal, padding estandar y espaciado entre secciones.
metadata:
  domain: design_system
  supersedes: FRONTEND_UI_RULES.md (seccion 4)
---

# Spacing y layout

## Shell principal (`AppShell.vue`)

```
┌──────────────────────────────────────────┐  100vh
│ Sidebar (270px, fijo)  │  Content area   │
│                        │  ─────────────  │
│                        │  Navbar 70px    │
│                        │  ─────────────  │
│                        │  main-content   │  flex:1, overflow-y:auto
│                        │  p-4            │  background: #f8fafc
└──────────────────────────────────────────┘
```

- Sidebar: `min-width: 270px; max-width: 270px` — nunca escalar.
- Mobile: sidebar en offcanvas Bootstrap, toggle con hamburger en Navbar (`d-none d-lg-flex` en
  desktop, `offcanvas offcanvas-start` para mobile — detalle de breakpoints en
  [../ux/responsive.md](../ux/responsive.md)).

## Padding estandar de pagina

```html
<main class="main-content container-fluid p-4">
```

## Espaciado entre secciones

```html
<div class="mb-4"> <!-- entre header y card principal -->
<div class="mb-3"> <!-- entre campos de formulario -->
<div class="gap-2"> <!-- entre botones de accion -->
```
