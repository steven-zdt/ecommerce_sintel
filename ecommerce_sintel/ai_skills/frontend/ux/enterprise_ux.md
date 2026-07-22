---
description: Reglas transversales de UX enterprise — prohibiciones absolutas, contrato de errores, expectativas de CRUD. Cruza con Fase 8 (Enterprise SaaS Review) del editor.
metadata:
  domain: ux
  supersedes: FRONTEND_UI_RULES.md (seccion 10), FRONTEND_COMPONENT_REGISTRY.md (seccion 8/12 "prohibiciones")
---

# Enterprise UX — reglas transversales

## 1. Prohibiciones absolutas

```
NUNCA importar:
  - Badge, Button, Icon, Rating, Checkbox, Modal, Dropdown, Table, Card, Input, Drawer, Spinner
    ← ninguno existe. Ver componentes reales en ../components/cards.md
  - import { useApi } from '@/composables/useApi'           ← useApi es DEFAULT export
  - import { cartStore } from '@/store/cart'                ← debe ser useCartStore
  - import { wishlistStore } from '@/store/wishlist'        ← no existe wishlist store

NUNCA usar:
  - float para precios — siempre Decimal (backend) / parseFloat con cuidado (frontend)
  - emojis en archivos .py (regla global del proyecto, no solo frontend)
  - router.push('/ruta/hardcodeada')                        ← siempre { name: '...' }
  - POST/PATCH/DELETE a rutas de lectura publica (shop/products/, renting/equipment/, etc.) ← 405
  - Options API (data(), methods{}, computed{})              ← solo <script setup>
  - Alpine.js, jQuery, ni manipulacion directa del DOM
  - axios directamente en componentes                        ← siempre useApi()
  - modales flotantes para confirmaciones                    ← fila inline, ver ../components/dialogs.md
  - provide/inject para estado de autenticacion               ← siempre Pinia authStore
  - font-family inline en <style scoped> del panel            ← ya viene de Bootstrap
  - style="color: X" inline cuando existe clase Bootstrap equivalente
  - console.log en componentes de produccion                  ← si en composables debug
  - importar Bootstrap JS directamente                        ← ya esta en CDN en index.html
```

## 2. Contrato de errores — obligatorio en TODA llamada async

```js
try {
  await api.post('dashboard/recurso/', payload);
  toast.success('Accion exitosa');
} catch (e) {
  toast.error(e.response?.data?.detail || e.response?.data?.campo?.[0] || 'Error generico');
}
```

Sin `try/catch` + `toast.error(...)`, la tarea no esta completa. Detalle de extraccion de errores
DRF: [../components/forms.md](../components/forms.md#manejo-de-errores-drf--toast).

## 3. Expectativas de CRUD completo (modulo admin)

Cada modulo admin nuevo debe cubrir, salvo excepcion documentada:

- Listado con paginacion server-side (`count`/`next`/`previous` de DRF)
- Crear / Editar via offcanvas (ver [../components/offcanvas.md](../components/offcanvas.md))
- Eliminar con confirmacion inline (ver [../components/dialogs.md](../components/dialogs.md))
- Estado activo/inactivo con badge (ver [../design_system/colors.md](../design_system/colors.md))
- Loading + empty state en la tabla (ver [loading_states.md](loading_states.md))

**Gaps conocidos** (no asumir que existen salvo verificacion puntual en el modulo): filtros
avanzados, exportacion, acciones masivas, historial/auditoria visible en UI. Ver
[../editor/architecture_audit.md](../editor/architecture_audit.md) para el detalle por modulo.

## Ver tambien

- [../components/cards.md](../components/cards.md) — inventario de imports validos
- [accessibility.md](accessibility.md), [responsive.md](responsive.md), [loading_states.md](loading_states.md), [animations.md](animations.md)
