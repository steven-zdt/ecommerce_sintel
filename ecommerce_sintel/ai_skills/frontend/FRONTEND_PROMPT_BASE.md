---
description: Prompt base copy-paste para cualquier tarea de frontend Vue 3 en Sintel. Punto de entrada de ai_skills/frontend/.
metadata:
  domain: root
  last_audited: "2026-07-11"
---

# Sintel Frontend — Prompt Base

Copia y pega este bloque al inicio de cualquier tarea de frontend Vue 3. Reemplaza las secciones
`[EN_MAYUSCULAS]` con el contexto especifico. Ver [INDEX.md](INDEX.md) para el mapa completo de
dominios.

---

## PROMPT BASE (copiar completo):

```
Actua como un desarrollador senior Vue 3 experto en el proyecto Sintel E-Commerce.

## LECTURA OBLIGATORIA ANTES DE ESCRIBIR CODIGO

Lee estos archivos en este orden antes de generar cualquier codigo:

1. ai_skills/frontend/components/cards.md
   -> Unicos imports validos (componentes, layouts, cards)
   -> Firmas exactas de props/emits
   -> Lista de lo PROHIBIDO

2. ai_skills/frontend/architecture/vue_patterns.md
   -> Composables (useApi, useToast, useOffcanvas, useAuth, useEnums...)
   -> Estructura de modulo, script setup obligatorio

3. ai_skills/frontend/architecture/state_management.md
   -> Stores Pinia disponibles y sus firmas exactas

4. ai_skills/frontend/architecture/routing.md
   -> Nombres de ruta validos (siempre router.push({ name: '...' }))

5. ai_skills/frontend/design_system/colors.md + typography.md + icons.md
   -> Paleta, Bootstrap 5.3, Bootstrap Icons (bi-*)

6. [ARCHIVO DE LA VISTA O COMPONENTE DONDE SE INTEGRARA]
   -> Para conocer imports existentes y no duplicar

7. [STORE O COMPOSABLE QUE USARA EL NUEVO COMPONENTE]
   -> Para firmas exactas de actions/getters

## REGLAS QUE NO SE NEGOCIAN

- <script setup> SIEMPRE. Options API prohibido.
- import useApi from '@/composables/useApi'   <- default, sin llaves
- import { useToast } from '@/composables/useToast'   <- named
- import { useCartStore } from '@/store/cart'   <- named con prefijo 'use'
- NUNCA importar Badge, Button, Icon, Rating, Checkbox, Modal, Table (no existen — ver components/cards.md)
- NUNCA hardcodear /api/v1/ en URLs (useApi lo agrega)
- NUNCA POST/PATCH/DELETE a endpoints publicos (shop/products/, renting/equipment/, etc.)
- Precios: Intl.NumberFormat('es-CO', {style:'currency', currency:'COP', maximumFractionDigits:0})
- Bootstrap 5.3 utility classes primero, <style scoped> solo para lo que Bootstrap no cubre
- Bootstrap Icons: <i class="bi bi-nombre-icono"></i>
- Confirmacion de borrado: fila inline bg-danger-subtle, NO modales flotantes
- Debounce 400ms en todo input de busqueda
- try/catch con toast.error() en TODA llamada async
- router.push({ name: 'route-name' }) — NUNCA push('/ruta/hardcodeada')

## TAREA

[DESCRIPCION DETALLADA DE LO QUE SE DEBE IMPLEMENTAR]

## ARCHIVOS A CREAR O MODIFICAR

- [ruta/del/archivo.vue] -> [crear | modificar]
- [ruta/del/otro.vue] -> [crear | modificar]

## INTEGRACION

[DONDE SE IMPORTA Y USA EL NUEVO COMPONENTE — archivo + linea aproximada]

## CRITERIO DE EXITO

[QUE DEBE FUNCIONAR EXACTAMENTE — comportamiento observable, no "que el codigo compile"]
```

---

## CHECKLIST PRE-ENTREGA (el AI debe responder SI/NO a cada punto)

```
[ ] Todos los imports usan rutas @/ correctas de components/cards.md
[ ] useApi es default import (sin llaves)
[ ] No hay componentes inventados (Badge, Button, Icon, Rating, etc.)
[ ] Los stores usan el nombre correcto (useCartStore, no cartStore)
[ ] Las URLs de escritura van a dashboard/ (salvo excepcion documentada — ver architecture/frontend_architect.md)
[ ] Los precios usan Intl.NumberFormat('es-CO', ...)
[ ] Hay try/catch con toast.error() en cada llamada async
[ ] El componente nuevo se integra explicitamente en la vista padre
[ ] No hay Options API (data(), methods{}, computed{})
[ ] Bootstrap Icons correctos (bi-nombre, verificar en design_system/icons.md)
```

---

## USO CON EL AI ENGINE INTERNO

Si el proyecto usa el AI engine con ChromaDB (`ai_engine/`), estos archivos ya estan bajo
`CODEBASE_PATH` (`ecommerce_sintel/`) y se indexan automaticamente via
`ai_engine/loaders.py` (glob recursivo `ai_skills/frontend/**/*.md`). No hace falta listar rutas
manualmente al reindexar — ver [editor/synchronization.md](editor/synchronization.md) para el
detalle del mecanismo y por que la ubicacion importa.

Una vez indexados, el AI engine los recupera automaticamente cuando el prompt menciona
"frontend", "Vue", "componente", "tienda", "carrito", etc.

---

*Ver tambien: `ai_skills/drf/DRF_PROMPT_BASE.md` (raiz del repo) para el equivalente de backend
Django/DRF — nota: esa carpeta no esta confirmada como indexada por el AI Engine, ver
[editor/synchronization.md](editor/synchronization.md).*
