# FASE 0 -- Matriz de doble escritura (Migracion a autoridad unica de tecnico)

Plan "Migracion de dos escritores a un unico writer" (2026-08-14), resolviendo
el hallazgo H1 de `SERVICES_ADMIN_FACADE_BASELINE.md`. Auditoria exhaustiva
(grep sobre TODO el repo, no solo `technical_services`) de cada punto donde
se escribe `OrderServiceDetail.technician` o `ServiceOperation.technician`.
Cero cambios de codigo en esta fase.

## Metodo

1. `grep -rn "\.technician\s*=" --include=*.py` sobre todo el repo.
2. Para cada write site encontrado, `grep` de sus llamadores hasta llegar a
   un endpoint HTTP o un caller sin mas llamadores (raiz).
3. Busqueda separada de escrituras que NO pasan por asignacion de codigo
   Python explicita: Django Admin (`admin.py`, `ModelAdmin.readonly_fields`),
   signals, celery tasks, management commands -- ninguno de estos aparece
   en un grep de `\.technician\s*=` porque Django los maneja via
   `ModelForm`/`save()` internos.

## Matriz completa

| Origen | Escribe `technician` en | Panel/caller | Endpoint real | Uso |
|---|---|---|---|---|
| `ServiceAssignmentCommands.assign_technician()`/`unassign_technician()` (`technical_services/services/commands.py:924-988`) | `OrderServiceDetail.technician` | `TechnicianAssignmentBoard.vue` (`/panel/servicios/asignacion-tecnicos`) | `POST orders/service-orders/{uuid}/assign-technician\|auto-assign\|unassign-technician/` (`orders/api/service_orders.py:230-274`) | **Legacy** |
| Django Admin nativo (`OrderServiceDetailAdmin`, `technical_services/admin.py:364-379`) | `OrderServiceDetail.technician` | `/admin/technical_services/orderservicedetail/{id}/change/` (Django admin site, no `/panel/`) | Formulario nativo de Django -- `technician` NO esta en `readonly_fields` | **Legacy, sin auditoria ni validacion** (bypass total: no valida disponibilidad, no libera al tecnico anterior, no crea timeline, no notifica) |
| `ServiceOperationCommands.assign_technician()`/`unassign_technician()`/`reschedule()` (`technical_services/services/operations.py:156-264`) | `ServiceOperation.technician` | `ServiceOperationBoard.vue` (`/panel/servicios/operaciones`) | `POST service-operations/{uuid}/assign-technician\|unassign-technician\|reschedule/` (`technical_services/api/operation_views.py`) | **Nuevo** |
| mismo Command | `ServiceOperation.technician` | `ServiceRequestActionsPanel.vue` (`/panel/servicios/solicitudes`, fachada 2026-08-14) | `POST dashboard/technical-services/requests/{uuid}/assign/` -> `ServiceAdminRequestOrchestrator.assign_technician()` (delegacion de una linea, sin logica propia) | **Nuevo (fachada)** |

**No se encontraron** escrituras a `technician` en: signals (`technical_services/signals.py` solo escucha `ServiceConfiguration`), celery tasks (no existe `technical_services/tasks.py`), management commands, ni scripts. `dashboard/api/views.py`/`dashboard/services/admin_orchestrators.py` solo LEEN `OrderServiceDetail` (confirmado, ver `ServiceAdminRequestSelector`, agregado en el plan de fachada, no escribe nunca este campo).

## Hallazgo nuevo de esta auditoria (no estaba en H1 del baseline anterior)

El **Django Admin nativo** (`/admin/`, distinto del panel `/panel/` construido
en Vue) es una **tercera via de escritura** a `OrderServiceDetail.technician`,
mas peligrosa que las otras dos: no pasa por `ServiceAssignmentCommands` en
absoluto, asi que:
- no valida que el tecnico tenga perfil o este disponible,
- no libera al tecnico anterior (`_release_technician`),
- no crea evento de timeline,
- no dispara ninguna notificacion.

Un superusuario con acceso a `/admin/` puede dejar el sistema en un estado
inconsistente sin que ningun otro componente se entere. Esto debe cerrarse
en FASE 1 (declarar el campo `readonly` en `OrderServiceDetailAdmin`) junto
con la formalizacion de la autoridad unica -- no es un cambio de arquitectura,
es cerrar un agujero de auditoria ya identificado.

## Conteo de escritores activos hoy

- **A `OrderServiceDetail.technician`**: 2 origenes de codigo controlados
  (`ServiceAssignmentCommands` via 1 panel Vue) + 1 origen sin control
  (Django Admin) = **3 vias, 0 de ellas es la fachada nueva**.
- **A `ServiceOperation.technician`**: 1 Command (`ServiceOperationCommands`),
  consumido por **2 paneles Vue** (`ServiceOperationBoard.vue` directo,
  `ServiceRequestActionsPanel.vue` via la fachada) -- ambos ya pasan por el
  mismo Command, no hay divergencia de logica dentro del sistema "nuevo".

## Criterio de la fase -- cumplido

100% de las escrituras identificadas (grep exhaustivo + verificacion manual
de Django Admin, que no aparece en un grep de codigo Python de asignacion
directa). Habilitado avanzar a FASE 1.
