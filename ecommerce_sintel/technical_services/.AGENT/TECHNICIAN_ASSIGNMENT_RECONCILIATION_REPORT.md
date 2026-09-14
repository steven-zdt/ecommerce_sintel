# Reporte de Reconciliacion — Autoridad de Asignacion de Tecnico

FASE 6-7 del plan `TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md`. Generado
2026-08-14 corriendo `ServiceTechnicianReconciliationSelector.find_divergent_assignments()`
(`technical_services/services/selectors.py`) contra la base de datos real (no la de
tests).

## Metodo

Para cada `Order` con `service_detail` no nulo, compara:
- `ServiceOperation.technician` (fuente real, `technical_services.services.operations`)
- `OrderServiceDetail.technician` (snapshot legacy)

Clasificacion (ver docstring del selector para el detalle completo):

| Caso | Significado | Accion |
|------|-------------|--------|
| (sin listar) | Ambos coinciden (incluye ambos `None`) | Ninguna |
| **B_conflict** | Ambos asignados, a tecnicos **distintos** | Conflicto real -- requiere revision manual |
| **C_operation_only** | Solo `ServiceOperation` tiene tecnico | Esperado desde FASE 4 (asignacion via panel de Servicios/fachada) -- no es error |
| **D_detail_only** | Solo `OrderServiceDetail` tiene tecnico | Residual de ordenes anteriores a que `ServiceOperation` existiera |

## Resultado (2026-08-14)

```
B_conflict:        0
C_operation_only:  3
D_detail_only:     5
```

### B_conflict (0)

Ninguno. No hay ninguna orden donde los 2 sistemas tengan tecnicos **distintos**
asignados simultaneamente -- no se requiere ninguna decision de reconciliacion de
conflicto real en este momento. La politica para cuando aparezca uno (documentada
para referencia futura): favorecer `ServiceOperation.technician` (tiene chequeo real
de conflicto de agenda contra `ProfessionalAvailability`; el legacy no), pero
**nunca sobreescribir automaticamente sin que un admin lo confirme** -- son 2
decisiones humanas potencialmente legitimas divergiendo, no un bug determinista.

### C_operation_only (3)

3 ordenes con tecnico asignado solo via `ServiceOperation` (panel de
Servicios/Operaciones o la fachada `/panel/servicios/solicitudes`, ninguno de los
dos escribe `OrderServiceDetail.technician`). Este es el **estado normal esperado**
del sistema post-FASE 4 -- no requiere accion. `uuid`s en
`ServiceTechnicianReconciliationSelector.find_divergent_assignments()['C_operation_only']`
si se necesita el detalle exacto (no se listan aqui por ser datos operativos que
cambian con cada asignacion nueva).

### D_detail_only (5)

5 ordenes con tecnico asignado solo en el snapshot legacy `OrderServiceDetail.technician`,
sin `ServiceOperation` asociado. Investigadas individualmente:

- Las 5 tienen `created_at` del **2026-06-20** -- antes de que `ServiceOperation`
  existiera como feature en el proyecto (introducida en Fase 7 del modulo,
  2026-07-14 en adelante).
- Las 5 tienen `Order.status = 'pending'` -- nunca se completo el pago, son ordenes
  abandonadas de datos de desarrollo, no compromisos operativos activos.
- Conclusion: **no son un bug de la migracion ni requieren reconciliacion activa**.
  Son residuo historico legitimo de antes de que existiera el dominio operativo
  actual. Si alguna de estas ordenes se retomara (pago confirmado), 
  `ServiceOperationCommands.ensure_for_order()` crearia automaticamente su
  `ServiceOperation` en ese momento, sin necesidad de backfill manual.

## Conclusion FASE 6-7

**No hay conflictos reales (`B_conflict = 0`) que requieran una decision de
reconciliacion humana en este momento.** Los 8 casos de divergencia encontrados son
benignos y explicados: 3 son el comportamiento nuevo esperado, 5 son datos
historicos huerfanos sin actividad. La migracion puede continuar hacia FASE 8+
(lectura unica sancionada, ya implementada como
`ServiceTechnicianReconciliationSelector.get_assigned_technician()`) sin necesidad
de un script de backfill/correccion de datos.

**Recomendacion**: no automatizar un backfill para los casos D -- son ordenes
`pending` sin actividad, y crear un `ServiceOperation` retroactivo para una orden
nunca pagada no aporta valor y podria generar ruido en los paneles operativos
(apareceria en `/panel/servicios/operaciones` como pendiente de planear sin que
nadie vaya a actuar sobre ella). Si en el futuro se decide limpiar datos de
desarrollo antiguos, es una tarea de housekeeping separada, no de esta migracion.
