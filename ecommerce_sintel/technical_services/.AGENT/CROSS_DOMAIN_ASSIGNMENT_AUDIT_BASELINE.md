# Cross-Domain Assignment Audit — Baseline (FASE R0)

Fecha: 2026-08-14
Branch: `fix/audit-p0-remediation`
Commit HEAD: `5a9f642819759206c70e7321c5ce1fae7b6f2adf`

## Estado Git al iniciar

`git status --short` (repo completo) muestra un volumen grande de cambios sin
commitear que **preceden a esta auditoría** (ya presentes al inicio de la sesión,
ver snapshot de `gitStatus` del entorno) — incluye archivos borrados de
`ai_engine/AI_MANIFESTS/`, `ai_engine/APP_MEMORY/`, documentación de `AUDITORIA/`,
y trabajo de sesiones anteriores en `frontend/`, `dashboard/`, `technical_services/`.
No son parte de esta auditoría ni se tocan aquí.

Cambios relevantes a los dominios de esta auditoría (`technical_services/`,
`orders/`, `dashboard/`, `renting/`, `operations/`, `frontend/`) ya presentes antes
de arrancar R0: resultado de la migración "autoridad única de técnico" (FASE 0-9,
misma sesión, ver `TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md` y
`ARQUITECTURA_COMPLETA_SERVICES.md` §23) — `technical_services/services/operations.py`,
`technical_services/services/commands.py`, `technical_services/services/selectors.py`,
`technical_services/admin.py`, `technical_services/api/serializers.py`,
`orders/api/service_orders.py`, y los docs asociados.

**Ningún archivo de `renting/` u `operations/` fue tocado en esa migración previa**
— confirmado por `git status --short -- renting operations` (sin cambios en esas
dos apps al momento de iniciar esta auditoría).

## Punto de partida conocido (de la migración ya cerrada esta sesión)

- `technical_services.ServiceOperation.technician` = fuente de verdad operativa
  para Services (ya confirmado, no re-auditar desde cero — ver R4).
- `orders.OrderServiceDetail.technician` = snapshot legacy/compatibility, ya sin
  escritores independientes (Django Admin bloqueado FASE 1, endpoints legacy de
  Orders delegan desde FASE 4).
- 0 conflictos reales encontrados en la reconciliación de Services corrida contra
  la base de datos real (`TECHNICIAN_ASSIGNMENT_RECONCILIATION_REPORT.md`).
- **Renting NO fue tocado por esa migración** — su relación (si alguna) con
  `OrderServiceDetail.technician` no ha sido verificada todavía. Ese es el
  hallazgo principal que esta auditoría cross-domain debe determinar.

## Alcance de esta auditoría

Confirmar o refutar, con evidencia de código (no supuestos), si existe algún cruce
indebido entre Services/Renting/Orders/Operations en mecanismos de asignación de
técnico, despachador, vehículo o transporte. Fases R1-R14 son de descubrimiento y
clasificación puro — sin modificar código de dominio. R15+ solo se ejecuta si se
confirma un doble-writer real no resuelto.
