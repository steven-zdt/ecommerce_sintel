---
description: Paleta de colores completa — sidebar, colores de modulo, navbar, content area. Fuente de verdad hex.
metadata:
  domain: design_system
  supersedes: FRONTEND_UI_RULES.md (seccion 2.1-2.4)
---

# Paleta de colores

## 1. Sidebar (navegacion oscura)

| Token | Hex / Valor | Uso |
|---|---|---|
| sidebar-bg | `#0a0a0a` | Fondo del sidebar |
| sidebar-brand-gradient | `linear-gradient(135deg, #fff 0%, #38bdf8 100%)` | Texto "Sintel UI" |
| link-default | `rgba(255,255,255,.55)` | Color de links en reposo |
| link-hover-bg | `rgba(255,255,255,.07)` | Fondo al hover |
| link-active-bg | `#1e3a8a` | Fondo del link de ruta activa |
| link-active-shadow | `rgba(30,58,138,.45)` | Box-shadow del link activo |
| section-label | `rgba(255,255,255,.3)` | Labels de seccion (Panel, Modulos, Sistema) |
| submenu-border | `var(--c, rgba(255,255,255,.12))` | Borde izquierdo del submenu (CSS var por modulo) |

## 2. Colores de modulo (sidebar groups)

Cada grupo del sidebar tiene un color que se pasa como variable CSS `--c`:

| Modulo | Color | Hex |
|---|---|---|
| Tienda (`shop/`) | Azul | `#3b82f6` |
| Operaciones (`orders/`, `inventory/`, `quotes/`) | Esmeralda | `#10b981` |
| Serv. Tecnicos (`technical_services/`) | Ambar | `#f59e0b` |
| Renta (`renting/`) | Violeta | `#8b5cf6` |
| Marketing (`marketing/`) | Rosa | `#ec4899` |

> El sidebar tiene 7 grupos colapsables en total: `shop`, `ops`, `quotes`, `ts`, `renting`, `mkt`,
> `fulfillment` (este ultimo agrupa Operaciones/Despachadores/Asignacion de tecnicos).

## 3. Colores de acento — cards horizontales customer

| Componente | Color accent | Hex |
|---|---|---|
| `ServiceHorizontalCard` | Ambar | `#d97706` (fallback imagen sobre `#fffbeb`) |
| `EquipmentHorizontalCard` | Violeta | `#7c3aed` |

## 4. Navbar

| Token | Valor |
|---|---|
| navbar-bg | `rgba(255,255,255,.88)` con `backdrop-filter: blur(12px)` |
| navbar-height | `70px` |
| navbar-border | `rgba(0,0,0,.06)` |
| avatar-bg | `#1e3a8a` |
| avatar-shadow | `rgba(13,110,253,.4)` |

## 5. Content area

| Token | Valor |
|---|---|
| main-bg | `#f8fafc` (slate-50) |
| card-shadow | Bootstrap `shadow-sm` |
| card-footer-bg | `bg-white` |
| table-header | Bootstrap `table-light` |
| delete-row-bg | Bootstrap `bg-danger-subtle` |

Mapeo de estados a clases Bootstrap: ver [tokens.md](tokens.md#2-semanticos-bootstrap-usados).
