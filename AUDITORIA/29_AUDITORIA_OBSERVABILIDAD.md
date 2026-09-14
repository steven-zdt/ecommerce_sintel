# 29 — Auditoría Enterprise: Observabilidad (Fase 15)

> **Fase 15 completada y cerrada 2026-08-03** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[28](28_AUDITORIA_OPERATIONS.md). Última fase de
> alcance real de la sesión (la Fase 16, Pruebas, fue declinada explícitamente por el usuario
> desde el inicio). Foco cross-módulo: logging, health checks, error tracking, métricas —
> no un módulo de negocio específico.

## P1 — El HEALTHCHECK de Docker en producción era un falso positivo total

`ecommerce/urls.py::health_check` (consultado por el `HEALTHCHECK` del servicio `django` en
`docker-compose.prod.yml:115`, vía `curl -f`) devolvía `{"status": "ok"}`
**incondicionalmente**, sin verificar nada. Mientras tanto ya existía un chequeo real y completo
— `security/services/selectors.py::SecuritySelector.get_health_snapshot()` (verifica
`connection.ensure_connection()` para Postgres, `cache.set`/`get` para Redis, y
`celery_app.control.inspect().ping()` para Celery) — pero solo estaba expuesto detrás de auth de
admin en `/api/v1/security/health/`, y **ningún monitoreo automatizado lo consultaba**.

Resultado real: Docker podía reportar el contenedor `django` como "healthy" (sin reiniciarlo,
vía `restart: unless-stopped`) mientras Postgres o Redis eran inalcanzables **desde Django
específicamente** (credenciales rotas, pool de conexiones agotado, partición de red) — un
escenario distinto y no cubierto por los healthchecks independientes que sí tienen los
contenedores `redis`/`db` (esos verifican que el proceso de Redis/Postgres esté vivo, no que
Django pueda alcanzarlo).

**Resuelto:** `health_check` ahora reusa `SecuritySelector.get_health_snapshot()` (sin duplicar
lógica) y responde `503` si `db` o `redis` fallan — `curl -f` interpreta cualquier status ≥400
como fallo, activando correctamente la política de reinicio de Docker. Celery se reporta en el
payload pero no bloquea el status: el servicio `celery_worker` ya tiene su propio `HEALTHCHECK`
independiente (`celery -A ecommerce inspect ping`), acoplarlo aquí duplicaría esa
responsabilidad.

## P2 — El formato de logs no distinguía entre 9 módulos con el mismo nombre de archivo

`ecommerce/settings/base.py::LOGGING` usaba `{module}` en el formatter — da solo el nombre del
archivo (ej. `tasks`), no el logger completo. **9 apps distintas tienen su propio `tasks.py`**
(`support`, `notifications`, `marketing`, `orders`, `payment`, `quotes`, `renting`, `accounts`,
`operations`) — todas indistinguibles entre sí en los logs crudos de producción (mismo problema
para `views.py`/`consumers.py`, presentes en múltiples apps). Sin agregación de logs
(Loki/ELK) en este proyecto, correlacionar un `.info()` de `support/tasks.py` con el módulo
correcto vía `docker logs` era prácticamente imposible — incluyendo los `.info()` agregados en
fases previas de esta misma auditoría (9, 14).

**Resuelto:** `{module}` → `{name}` — el logger completo (`logging.getLogger(__name__)`, ya
usado consistentemente en todo el proyecto sin necesidad de tocar código de aplicación), ej.
`support.tasks`/`notifications.tasks` en vez de `tasks` para ambos.

## Verificado como correcto o fuera de alcance (no requiere cambio)

- **Propagación de loggers al root INFO**: confirmado en vivo (`django.setup()` en el contenedor)
  que `logging.getLogger('support'/'notifications'/'ai_engine').getEffectiveLevel()` da `20`
  (INFO) — los `.info()` de fases anteriores sí se emiten y sí llegan a stdout/Docker. La
  hipótesis inicial ("logger huérfano cae a WARNING silencioso") **no se confirmó**.
- **Sin Sentry ni ningún error tracker**: confirmado por ausencia total (`grep -i sentry` sin
  resultados relevantes en todo el repo) — decisión de infraestructura/costo (requiere una
  cuenta y DSN reales), no un bug de código. **Decidido no implementar en esta sesión** (el
  usuario declinó esta opción explícitamente al elegir el alcance de la fase).
- **Métricas de infraestructura del AI Engine**: `ai_engine/observability.py` (`TurnMetrics`)
  sí captura latencia, tokens y errores de tools por turno vía logging estructurado — pero el
  propio código ya documenta que la integración Prometheus/Grafana está "preparada pero no
  instalada". No es un hallazgo oculto, ya está declarado en el código; fuera de alcance de un
  fix incremental.
- **Sin tests que verifiquen el propio logging**: confirmado (`grep -r "assertLogs\|caplog"` sin
  resultados en support/notifications/ai_engine). Nivel de rigor razonable para este proyecto —
  no se agregaron tests de logging por logging mismo, serían de bajo valor frente a los tests
  reales del endpoint de health check (que sí verifican comportamiento observable).

## Verificación

- 4 tests nuevos para `/api/v1/health/`: 200 cuando db/redis están sanos, 503 cuando redis
  falla, 503 cuando db falla, sin requerir autenticación (el `curl` de Docker no envía
  credenciales).
- `ecommerce/tests.py` + `security/tests.py`: **10/10**.
- Probado en vivo dentro del contenedor dev: `curl http://localhost:8000/api/v1/health/` →
  `{"status": "ok", "db": true, "redis": true, "celery": true}`, HTTP 200.
- `manage.py check`: limpio.

## Resumen ejecutivo

El hallazgo más importante de esta fase fue el healthcheck de Docker como falso positivo total
en producción — un riesgo real de disponibilidad silencioso (un contenedor "healthy" que en
realidad no puede hablar con su base de datos). Se cerró reusando por completo una función que
ya existía y ya estaba probada (`SecuritySelector.get_health_snapshot()`), sin inventar
arquitectura nueva — exactamente el patrón que esta auditoría ha seguido en las 15 fases
anteriores. El fix de formato de logs es de una línea pero de alto valor diagnóstico dado que
9 apps comparten nombres de archivo de logging.

## Roadmap — estado final

| Fase | Estado |
|------|--------|
| 1-10 | Hechas — ver documentos 15-25 |
| 11 — Seguridad | Hecha — ver [23](23_AUDITORIA_SEGURIDAD.md) |
| 12 — Core | Hecha — ver [26](26_AUDITORIA_CORE.md) (sin hallazgos) |
| 13 — Marketing/CRM | Hecha — ver [27](27_AUDITORIA_MARKETING.md) (ImportError P0 + P1 + P2) |
| 14 — Operations | Hecha — ver [28](28_AUDITORIA_OPERATIONS.md) |
| 15 — Observabilidad | **Hecha (este documento) — healthcheck P1 + formato de logs P2** |
| 16 — Pruebas | Hecha — ver [30](30_AUDITORIA_PRUEBAS_E2E.md) |

Con esto se cierran las 16 fases planeadas de la auditoría enterprise del módulo de soporte
omnicanal.
