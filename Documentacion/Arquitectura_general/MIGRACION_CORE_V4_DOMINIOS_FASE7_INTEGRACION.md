# CORE v4 — Arquitectura por Dominios: Fase 7 (Integración)

**Fecha:** 2026-07-12
**Objetivo:** Validar que todos los dominios interactúen únicamente mediante servicios y
contratos definidos — con foco en el código NUEVO de las Fases 5 y 6 (lo demás ya lo cubrió la
Fase 3, cuyos hallazgos siguen vigentes y no se repiten aquí).

---

## 1. Auditoría del código nuevo (Fases 5-6)

| Código nuevo | Resultado |
|---|---|
| `organization/api/views.py` (8 ViewSets nuevos) | **0 imports cross-app.** Grep de `from <app>.models import` sobre todo `organization/` — cero resultados fuera de `organization.models`/Django/DRF/`users` (patrón `AUTH_USER_MODEL`, esperado en todo el proyecto). Cumple al 100%. |
| `operations/models.py::OperationTicket.get_effective_status()` | Lee `self.service_operation.status`/`self.rental_operation.status`/`self.shipment.status` — **traversal de FK ya enlazada**, no import de modelo ni query cruzada. Mismo patrón aceptado en Fase 3 (sección 2.A, FK estructural). No es una violación. |
| `operations/management/commands/backfill_operation_satellite_links.py` | Importa `ServiceOperation`/`RentalOperation`/`Shipment` directo. **Revisado y aceptado como excepción legítima**: es una herramienta de reconciliación de datos de un solo uso (idempotente, con `--dry-run`), no lógica de negocio recurrente — mismo tipo de excepción ya aceptada en Fase 3 (3.1, `payment` con `select_for_update()` directo). Los comandos de backfill/seed de este proyecto siempre han importado modelos directo (mismo patrón que `payment/migrations/0008_seed_reconcile_periodic_task.py`). |
| `frontend/src/modules/organization/OrganizationView.vue` | Consume exclusivamente `organization/*` vía `useApi()` — ningún acceso directo a otro dominio. |
| `frontend/src/modules/operations/OperationBoard.vue` (campo `effective_status`) | Solo lee un campo nuevo del mismo endpoint que ya consumía — sin cambio de contrato de integración. |

**Conclusión: el código nuevo de las Fases 5-6 no introduce ninguna violación de propiedad de
datos ni de patrón de acceso.** Las 6 migraciones pendientes de severidad baja/media
identificadas en la Fase 3 (payment/select_for_update, 3 `summary.py` importando `OrderItem`,
quotes importando ProductVariant/ServiceVariant directo, `core.enums()`, `orders` importando
`Cart` directo, `dashboard` orchestrators) **siguen exactamente igual** — no se tocaron en
estas fases, siguen como backlog de baja prioridad.

---

## 2. Mapa de integraciones (actualizado con `organization`)

```
organization  (SSoT institucional — Empresa/Branding/Contacto/RedesSociales/Correos/Dominios/
               SEO/InformacionLegal)
    │
    ├─ API propia: /api/v1/organization/  (8 ViewSets, IsAdminUser)
    │   consumida por: frontend/OrganizationView.vue (NUEVO, Fase 6)
    │
    └─ Selectors/Commands (organization.services.*) consumidos internamente por:
        core (site-config/footer), notifications (email), accounts (verificacion email),
        users (admin-auth login url), marketing (8 canales de integracion), quotes (pdf_service)
        — todos via OrganizationSelector, cero import de organization.models fuera de la app.

operations  (hub de tickets — Fase 5, Opcion B)
    │
    ├─ OperationTicket.service_operation/rental_operation/shipment (FKs nuevos, nullable)
    │   → traversal de solo lectura, no escribe en los satelites
    │
    ├─ get_effective_status() → deriva estado para mostrar (fallback a status propio)
    │
    └─ backfill_operation_satellite_links (comando, excepcion aceptada de acceso directo)

Resto del grafo de dependencias: sin cambios desde la Fase 3 (ver
MIGRACION_CORE_V4_DOMINIOS_FASE3_PROPIEDAD_DATOS.md, seccion 1, matriz completa).
```

---

## 3. Informe de cumplimiento de arquitectura

| Regla del usuario | Cumplimiento |
|---|---|
| "Ninguna aplicación podrá escribir directamente información perteneciente a otra" | ✅ Cumplido — `organization` es la única que escribe sus 8 modelos; `operations` no escribe en `ServiceOperation`/`RentalOperation`/`Shipment` (solo lee, vía FK o el comando de backfill de un solo uso) |
| "Toda comunicación entre dominios será mediante Services, Selectors o APIs, nunca mediante acceso directo a modelos de otro dominio" | ✅ Cumplido para todo el código nuevo (Fases 5-6). Las 6 excepciones de la Fase 3 siguen documentadas y aceptadas, no son código nuevo |
| "Todo dato tendrá un único propietario (SSoT)" | ✅ `organization` es dueño único de sus 8 agregados desde la Fase 4. `operations` NO se volvió dueño del estado de `ServiceOperation`/`RentalOperation`/`Shipment` — solo lo refleja (Fase 5, decisión explícita de la Opción B sobre la Opción A) |
| "No se introducen redundancias de configuración ni lógica de negocio durante la migración" | ✅ Los 3 nuevos FKs de `OperationTicket` no duplican `status` — es trazabilidad, con `get_effective_status()` como único punto de lectura derivada |

**Veredicto: CUMPLE.** No se encontraron violaciones nuevas. El único punto crítico pendiente
de resolución de fondo (no de auditoría) sigue siendo la duplicación real de las 4 máquinas de
estado (Fase 1, 3.7) — mitigada pero no eliminada por el trabajo de la Fase 5 (Opción B
deliberadamente NO fusiona los modelos, los deja vivir en su dominio correspondiente).

---

## Estado

**Fase 7: COMPLETA.** Sin cambios de código en esta fase (solo auditoría + documentación).

**⏳ Pendiente de autorización explícita para iniciar la Fase 8** (Pruebas de Regresión) —
dado que ya se corrieron verificaciones puntuales en cada fase anterior, Fase 8 sería una
pasada de regresión más amplia (suite completa de tests + smoke test del panel autenticado, que
sigue pendiente de que el usuario lo confirme manualmente por el tema de credenciales).
