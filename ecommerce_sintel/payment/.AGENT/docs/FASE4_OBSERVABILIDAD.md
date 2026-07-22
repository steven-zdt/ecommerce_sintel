# Fase 4 — Observabilidad (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` §9

## Ajuste de diseño encontrado al implementar

El ADR proponía `logger.info(..., extra={'correlation_id': cid})`. Al implementar se confirmó una restricción real: el formatter global de logging (`ecommerce/settings/base.py`, `'{levelname} {asctime} {module} {process:d} {thread:d} {message}'`) **no referencia ningún campo de `extra`** — pasar `extra={'correlation_id': ...}` habría quedado silenciosamente invisible en los logs (Python no falla, simplemente no lo imprime, salvo que el formatter lo referencie explícitamente). Cambiar el formatter global para incluirlo habría requerido auditar **todas** las llamadas a `logger.*` de las 18+ apps del proyecto (cualquier log que no pase ese campo rompería el formato) — fuera de alcance y de "mínimo impacto". Se optó por interpolar `corr=%s` directamente en el mensaje de log, siguiendo el mismo patrón `"clave=valor | clave2=valor2"` ya usado en todo `payment/` — logra el mismo objetivo (grepeable) sin tocar configuración global.

## Qué se hizo

### 1. `Transaction.correlation_id` (nuevo campo) + `TransactionEvent` (modelo nuevo)

Migración `payment/migrations/0009_transaction_correlation_id_transactionevent.py`.

- `Transaction.correlation_id`: se minta **una vez** en `WompiPaymentViewSet.initialize()` (un UUID por intento de pago) y se guarda en la `Transaction` desde su creación. Todo lo que pase después sobre esa misma transacción (sync por polling, webhook) lee este mismo valor — no hace falta pasarlo explícitamente entre capas.
- `TransactionEvent`: historial **append-only**, separado de `Transaction.status` (que sigue siendo el estado *actual*, sin cambios para nada que ya lo consulte). Campos: `transaction` (FK), `source` (`API_CREATE` / `API_SYNC` / `WEBHOOK`), `previous_status`, `new_status`, `correlation_id`, `raw_payload` (JSON), `processed` (bool), `error_detail`.
- **Deliberadamente sin un campo de "ID de evento de Wompi"**: se investigó contra `docs.wompi.co` en la Fase 2 de este mismo proyecto y el payload de webhook no documenta un identificador de evento único separado del ID de transacción — no se inventó ese campo.

### 2. Escritura de `TransactionEvent` en los 3 puntos de contacto con Wompi

- `WompiCommands._create_transaction_sync()` — un evento `API_CREATE` por cada creación síncrona (éxito con el payload completo de Wompi, o fallo con `processed=False` + `error_detail`).
- `payment/online/api/views.py::_sync_wompi_status()` — un evento `API_SYNC` **solo cuando el status realmente cambia** (evita ruido en cada poll que no trae novedades).
- `WompiCommands.process_webhook_notification()` — un evento `WEBHOOK` por cada notificación procesada, **incluyendo el caso de webhook duplicado** (`processed=False`, para que quede constancia de que Wompi reintentó y por qué se ignoró — antes solo había una línea de log de texto).

### 3. `SecurityEvent.PAYMENT_APPROVED` (nuevo, para simetría con `PAYMENT_DECLINED`)

Se dispara en `PaymentCommands.confirm_payment()`, cubriendo **ambos** caminos (`Order` y `RentalRequest`) — es el mismo método que ya centraliza las 3 formas de llegar a "pago aprobado" (webhook, sync, creación síncrona), así que la cobertura es automática para las tres sin tener que duplicar la llamada en cada sitio.

### 4. Respuesta de `initialize/`

Incluye ahora `correlation_id` (campo nuevo, aditivo — no rompe nada del lado del frontend, que lo ignora si no lo usa).

## Verificación realizada

7 tests nuevos (`payment/tests.py::WompiObservabilityTestCase`): correlation_id presente en la respuesta y en la `Transaction`; `TransactionEvent` correcto en creación síncrona exitosa y fallida; `TransactionEvent` correcto en webhook procesado y en webhook duplicado; `TransactionEvent` correcto cuando `_sync_wompi_status` cambia el estado; `SecurityEvent.PAYMENT_APPROVED` disparado con el `correlation_id` correcto en el metadata.

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.WompiObservabilityTestCase` → **7/7 OK**.
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **44/44 OK** (37 anteriores + 7 nuevos).
- `docker exec ecommerce_sintel_django python manage.py test security` → **4/4 OK** (sin regresión por el nuevo choice `PAYMENT_APPROVED`).

**Nota operativa de la sesión:** un run anterior de la suite completa dejó la base de datos de test en un estado inconsistente (gotcha ya documentado en memoria de este proyecto: un `manage.py test` interrumpido puede dejar `test_sintel_ecommerce` sin poder recrearse). Se resolvió con `DROP DATABASE test_sintel_ecommerce;` directo en Postgres (credenciales del entorno de desarrollo, `DB_USER=postgres`, no las de producción) antes de reintentar — no fue un problema del código de esta fase.

## Qué NO se tocó

- No se introdujo `structlog` (decisión ya confirmada por el usuario en la Fase 1).
- No se cambió el formatter global de logging (ver "Ajuste de diseño" arriba).
- `Transaction.status` — sin cambios de significado ni de valores posibles.
- Ningún endpoint público cambió de contrato (solo campos nuevos, aditivos).

## Siguiente paso

Con esto, la **Fase 4 del plan original de 10 fases queda completa**. Quedan: **Fase 5** (feature flag / migración gradual), **Fases 6-10** (reconciliación mejorada usando `TransactionEvent`/correlation_id, panel admin con acciones reales, alertas operativas, pruebas E2E/carga, documentación final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`).
