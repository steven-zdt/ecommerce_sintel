---
description: Stack de estilos, alcance de CSS global y mapeo de estados a clases semanticas Bootstrap. Punto de entrada del dominio design_system/.
metadata:
  domain: design_system
  supersedes: FRONTEND_UI_RULES.md (seccion 1, 2.5)
---

# Design Tokens — Stack y alcance

> Todo codigo Vue nuevo debe seguir estas reglas antes de escribir una sola linea de HTML.
> Cuando haya conflicto entre `design_system/` y cualquier otro doc, `design_system/` prevalece
> en temas de UI/visual.

## 1. Stack de estilos

| Capa | Tecnologia | Notas |
|---|---|---|
| Framework CSS | Bootstrap 5.3.3 (CDN) | Clases utilitarias base |
| Iconos | Bootstrap Icons 1.11.3 (CDN) | `class="bi bi-*"` — ver [icons.md](icons.md) |
| Fuente | Inter (Google Fonts, pesos 300-800) | Cargada en `index.html` |
| Estilos de componente | `<style scoped>` por cada `.vue` | No hay archivo CSS global de la app |
| Variables CSS globales | `src/style.css` | Solo aplica a la landing publica — **NO** al panel admin |

**Regla:** `src/style.css` contiene CSS del template Vite (landing). Los componentes del panel
admin usan **unicamente** Bootstrap + sus propios `<style scoped>`. No agregar `font-family` en
`<style scoped>` del panel — ya viene de Bootstrap via `index.html`.

## 2. Semanticos Bootstrap usados

| Estado | Clase Bootstrap | Uso |
|---|---|---|
| Activo / exito | `bg-success` | Badges `is_active=true`, toast success |
| Inactivo | `bg-secondary` | Badges `is_active=false` |
| Error / eliminar | `bg-danger`, `text-danger` | Confirmaciones, trash icon |
| Advertencia | `bg-warning text-dark` | Estados intermedios |
| Info / accion | `bg-primary`, `text-primary` | Botones principales, edit icon |
| Sutil | `bg-*-subtle text-*` | Badges de estado en tablas |

No agregar `style="color: X"` inline cuando existe clase Bootstrap equivalente.

## 3. Dark mode — solo panel admin (2026-07-11)

Implementado via el mecanismo nativo de Bootstrap 5.3 (`data-bs-theme="dark"|"light"` en
`<html>`), no una libreria propia. Alcance actual: **solo `AppShell.vue` + `Navbar.vue`**
(el shell del panel admin). El portal customer (landing/tienda/etc.) sigue sin dark mode.

- `composables/useTheme.js` — `init()` (localStorage > `prefers-color-scheme` > `'light'`),
  `toggle()`, `setTheme(value)`. Persiste en `localStorage.sintel_theme`.
- Toggle en `Navbar.vue` (icono sol/luna, junto a notificaciones).
- Componentes que usan clases Bootstrap reales (`.card`, `.table`, `.btn-light`, `.form-control`,
  `.badge`) se re-teman **automaticamente** al cambiar `data-bs-theme` — no hace falta tocar los
  ~190 componentes admin uno por uno.
- Piezas 100% CSS custom (no clases Bootstrap) necesitan su propio override con el selector
  `:global([data-bs-theme="dark"]) .clase-custom { ... }` dentro de `<style scoped>` — ya hecho
  para `.main-content` (AppShell) y `.sintel-navbar`/`.icon-btn`/etc. (Navbar). `Sidebar.vue` no
  necesito override — ya es oscuro por diseño (`#0a0a0a`) independiente del theme.
- **No cubierto:** el resto de los ~190 componentes custom-styled del panel (cada `List.vue`,
  `Form.vue`, etc.) puede tener texto/fondos hardcodeados en `<style scoped>` que no reaccionan a
  `data-bs-theme` — se re-teman los elementos Bootstrap-nativos que usan, pero cualquier CSS
  100% custom ahi (poco comun, la mayoria usa clases Bootstrap) quedaria en modo claro.
- Verificado: 5 tests unitarios reales en `useTheme.test.js` (persistencia, fallback a SO,
  toggle, valores invalidos). **No verificado visualmente en el navegador** — el login de prueba
  disponible (`admin@sintel.com` en `notas.txt`) resulto invalido contra este entorno dev, no se
  pudo hacer login para un screenshot real del panel en dark mode.

## Ver tambien

- [colors.md](colors.md) — paleta hex completa (sidebar, navbar, modulos)
- [typography.md](typography.md)
- [spacing.md](spacing.md)
- [icons.md](icons.md)
