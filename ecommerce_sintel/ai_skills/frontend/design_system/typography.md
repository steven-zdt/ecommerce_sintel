---
description: Tipografia — fuente, escalas de titulo/label y formato de datos en UI (precios, fechas, UUIDs).
metadata:
  domain: design_system
  supersedes: FRONTEND_UI_RULES.md (seccion 3, 9)
---

# Typography

## 1. Escalas

| Uso | Especificacion |
|---|---|
| Fuente del panel | Inter (heredada de Bootstrap + Google Fonts) |
| Titulos de pagina | `<h4 class="fw-bold m-0">` |
| Labels de formulario | `class="form-label small fw-bold"` |
| Labels de seccion sidebar | `0.63rem, letter-spacing: 2.5px, uppercase, fw-700` |
| Texto auxiliar | `class="text-muted small"` o `.smaller { font-size: 0.8rem }` |
| Codigo/slug | `<code class="small text-muted">` |
| Nombre de modulo sidebar | `0.92rem, fw-500` |
| Ruta fuente sidebar (grp-src) | `0.6rem, monospace, opacity .35` |

**Regla:** No agregar `font-family` en `<style scoped>` — Bootstrap ya aplica Inter via `index.html`.

## 2. Formato de datos en UI

| Tipo | Formato | Codigo |
|---|---|---|
| Precio colombiano | `$ 1.299.000` | `new Intl.NumberFormat('es-CO').format(num)` |
| UUID corto (ordenes) | `ORD-550e8400` | `'ORD-' + order.uuid?.slice(0, 8)` |
| Fecha | `15/01/2024` | `new Date(iso).toLocaleDateString('es-CO')` |
| Datetime | `15/01/2024 10:30` | `toLocaleString('es-CO')` |
| Datetime-local (inputs) | `yyyy-MM-ddTHH:mm` | `iso.substring(0, 16)` |

Formato completo de precios (con simbolo de moneda) en
[../components/forms.md](../components/forms.md#input-de-precio).
