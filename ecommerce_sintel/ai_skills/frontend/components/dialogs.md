---
description: Confirmacion de eliminacion inline en tabla. No existen modales flotantes en el proyecto — no importar Modal.
metadata:
  domain: components
  supersedes: FRONTEND_UI_RULES.md (seccion 5.5)
---

# Dialogs

## Regla — NO hay componente Modal

```
import { Modal } from '@/components/ui/Modal.vue'   // NO EXISTE — no inventar
```

Este proyecto **no usa modales flotantes para confirmaciones**. Toda confirmacion destructiva
(eliminar, cancelar, rechazar) reemplaza la fila normal de la tabla con una fila inline. Excepcion
conocida: paneles de accion más elaborados (ej. `RentalRequestActionsPanel`) tambien usan el mismo
mecanismo de fila expandida, no un modal aparte.

## Confirmacion inline de eliminacion

```html
<tr v-if="pendingDelete?.uuid === item.uuid" class="bg-danger-subtle">
  <td colspan="N" class="p-0">
    <div class="d-flex align-items-center gap-3 px-3 py-2">
      <i class="bi bi-exclamation-triangle-fill text-danger"></i>
      <span class="small">¿Eliminar <strong>{{ item.name }}</strong>?</span>
      <div class="ms-auto d-flex gap-2">
        <button class="btn btn-sm btn-danger" @click="executeDelete(item)" :disabled="actionLoading">
          <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Confirmar
        </button>
        <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
      </div>
    </div>
  </td>
</tr>
```

`pendingDelete` es un `ref(null)` que guarda el item pendiente de confirmar. Se compara por
`uuid` en el `v-if` de cada fila (ver [datatable.md](datatable.md)).

## Ver tambien

- [datatable.md](datatable.md) — patron de tabla completo donde se integra esta fila
- [offcanvas.md](offcanvas.md) — receta List component con `executeDelete`/`pendingDelete` implementados
