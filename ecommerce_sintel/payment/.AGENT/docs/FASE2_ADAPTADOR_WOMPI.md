# Fase 2 — Capa de integración con Wompi (adaptador, completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` §3
**Alcance de este paso:** construir y probar `WompiApiClient` en aislamiento. **No se modificó ningún endpoint existente** (`initialize/`, `transaction-status/`, `confirmation/`, `webhook/` siguen exactamente igual que antes) — el cliente nuevo todavía no está conectado a ningún flujo real. Ver "Siguiente paso" para la decisión pendiente sobre eso.

## Qué se hizo

### 1. Validación contra la documentación real de Wompi (no asumida)

Antes de escribir código se confirmaron, contra `docs.wompi.co`, los puntos que el ADR había marcado `[VALIDAR EN FASE 2]`:

| Punto | Confirmado |
|---|---|
| `POST /transactions` y `POST /payment_sources` — ¿qué llave? | **Llave privada** (Bearer), no la pública. |
| `acceptance_token`/`accept_personal_auth` — ¿se piden una vez o en cada llamada? | Son JWT **presignados con expiración** (`GET /merchants/{public_key}`, llave pública, sin Bearer) — deben pedirse **frescos en cada** creación de `payment_source` o transacción, no se cachean indefinidamente. |
| Tokenización de tarjeta — ¿existe un modo del widget solo para tokenizar? | Sí: `widget.js` soporta `data-widget-operation="tokenize"`, separado del checkout completo — confirma la premisa del ADR de que el Widget puede limitarse a esa función. La tokenización (`POST /tokens/cards`) **nunca** debe pasar por el backend — confirmado explícitamente en la documentación oficial de Wompi. |
| ¿Wompi deduplica por `reference`? | **No.** Reintentar con el mismo `reference` devuelve **422 "Duplicate reference"** — Wompi no crea una segunda transacción ni devuelve la existente. Esto se traduce en `WompiDuplicateReferenceError`, una excepción específica para que el código que la reciba sepa que debe reconciliar contra la transacción ya conocida, no tratarlo como un fallo nuevo. |
| ¿El webhook trae un ID de evento único, separado del ID de transacción? | **No confirmado como existente** en la documentación consultada (`event`, `data`, `environment`, `signature`, `timestamp`, `sent_at` — sin campo de ID de evento explícito). El diseño de `TransactionEvent` (Fase futura) deberá ajustarse a esto, no asumir un campo que no está documentado. |
| Política de reintentos de webhook | Confirmada: hasta 3 reintentos en 24h (30min, 3h, 24h) si el endpoint no responde 200 — ya coincide con el contrato actual del webhook (siempre responde 200 si la firma es válida, sin importar el resultado del procesamiento). |

### 2. `payment/online/wompi_client.py` (nuevo)

`WompiApiClient`, calcado del patrón de `payment/nequi/client.py::NequiApiClient` (cliente HTTP aislado, sin lógica de negocio de Sintel adentro):

- `get_acceptance_tokens()` — `GET /merchants/{public_key}`.
- `create_payment_source(card_token, customer_email)` — `POST /payment_sources`.
- `create_transaction(...)` — `POST /transactions`, acepta `payment_source_id` (tarjeta guardada) o `card_token` (tarjeta nueva), mutuamente excluyentes.
- `get_transaction(wompi_id)` — `GET /transactions/{wompi_id}` (mismo propósito que la llamada hoy embebida en `_sync_wompi_status`, pero encapsulada).
- Excepciones: `WompiApiError` (definitivo, no reintentable), `WompiApiTransientError` (red/5xx, reintentable), `WompiDuplicateReferenceError` (422 específico de referencia duplicada).
- **A propósito, este cliente NO expone ningún método de tokenización** — refuerza en el código mismo la regla de que los datos de tarjeta nunca deben pasar por el backend.

### 3. Tests (`payment/tests.py`, clase `WompiApiClientTestCase`, 11 tests nuevos)

Cierra el hueco de cobertura que la Fase 0 había señalado explícitamente (ningún cliente HTTP de `payment/`, ni siquiera `NequiApiClient`, tenía tests aislados propios hasta ahora). Cubre: parseo de acceptance tokens, error si falta el token, payload correcto de `create_payment_source`, las dos variantes de `create_transaction` (fuente guardada vs. token nuevo), validación de exactamente-un-origen-de-pago, detección de referencia duplicada (422), errores transitorios (5xx, excepción de red) vs. definitivos (4xx), y el uso correcto de la llave privada en cada llamada autenticada.

**Nota de honestidad sobre la detección de "referencia duplicada":** el formato exacto del cuerpo JSON de error 422 de Wompi para este caso específico no está garantizado por la documentación consultada — la detección actual (`_looks_like_duplicate_reference`) es una búsqueda de texto tolerante (`"reference"` + `"duplicate"`/`"unique"` en el cuerpo de la respuesta), marcada con un comentario explícito en el código para revisarla contra una respuesta real de sandbox antes de depender de ella en un camino crítico.

## Verificación realizada

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.WompiApiClientTestCase` → **11/11 OK**.
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **31/31 OK** (20 tests preexistentes + 11 nuevos, sin regresiones).
- **No se hicieron llamadas reales a la API de Wompi** (ni siquiera al sandbox) — todos los tests mockean `requests.request`. Se decidió así deliberadamente: hacer llamadas reales, incluso de solo lectura, habría creado efectos secundarios en el sandbox real de Wompi asociado a las llaves de este proyecto sin que el usuario lo pidiera explícitamente. Si se quiere una prueba de humo contra el sandbox real de Wompi, es una acción aparte a autorizar explícitamente.

## Qué NO se tocó (a propósito)

- `payment/online/api/views.py` (`WompiPaymentViewSet`, `_sync_wompi_status`, `initialize/`, etc.) — sigue exactamente igual. El cliente nuevo existe en paralelo, no reemplaza nada todavía.
- `payment/online/services/commands.py` (`WompiCommands`, `PaymentCommands`) — sin cambios.
- Ningún modelo, ninguna migración.
- El frontend — sin cambios (fuera de alcance de esta fase de todas formas).

## Continuación (misma Fase 2) — `WompiApiClient` conectado a `initialize/`

**Hallazgo importante antes de implementar:** el diseño del ADR (§4) asume que el backend puede crear la transacción de forma síncrona en Wompi usando un `card_token`/`payment_source_id` — pero **el frontend actual nunca tiene un token en el momento en que llama a `initialize/`**: hoy el Widget captura los datos de tarjeta *después* de que `initialize/` responde, no antes. Conectar el adaptador de forma literal ("que `initialize/` cree la transacción en Wompi") **no es posible sin que el frontend cambie primero** para tokenizar antes de llamar a `initialize/` — y ese cambio de frontend es exactamente el alcance de la Fase 3, todavía no ejecutada.

**Solución adoptada — extensión aditiva, cero riesgo para el checkout en vivo:**

- `WompiCommands.initialize_transaction()` (`payment/online/services/commands.py`) ahora acepta dos parámetros **opcionales y mutuamente excluyentes**: `card_token` y `payment_source_id`.
  - **Si ninguno se pasa** (el único caso real hoy, porque el frontend actual nunca los envía): el comportamiento es **byte por byte idéntico al de antes** — solo se crea la `Transaction` local con su firma de integridad, tal como siempre.
  - **Si se pasa alguno**: se llama a `WompiApiClient.create_transaction(...)` de forma síncrona; `wompi_id`/`status`/`payment_method_type` se actualizan de inmediato en la `Transaction` local (sin esperar el webhook); si el `status` devuelto ya es `APPROVED`, se dispara `PaymentCommands.confirm_payment(...)` en el mismo request (mismo patrón que ya usa `_sync_wompi_status`).
  - Si la llamada a Wompi falla (`WompiApiError`, incluye los casos transitorio/definitivo/referencia duplicada), la `Transaction` local pasa explícitamente a `ERROR` y la excepción se re-propaga — nunca queda una transacción huérfana en `PENDING` sin rastro.
- `WompiPaymentViewSet.initialize()` (`payment/online/api/views.py`) ahora lee `card_token`/`payment_source_id` (opcionales) del body, los pasa al comando, y agrega `wompi_id` a la respuesta (campo nuevo, aditivo — no rompe nada del lado del frontend actual, que simplemente lo ignora). Errores de Wompi devuelven **502**; pasar ambos parámetros a la vez devuelve **400**.

**Por qué esto es seguro hoy:** ningún llamador real (el checkout en vivo de `CheckoutView.vue`) envía `card_token` ni `payment_source_id` todavía — esa rama de código es **código muerto en producción** hasta que la Fase 3 (frontend) empiece a alimentarla. El primer test de la nueva suite (`test_initialize_without_new_params_keeps_legacy_behavior`) existe específicamente para proteger esto como regresión.

### Tests (`payment/tests.py`, clase `WompiSyncTransactionCreationTestCase`, 6 tests nuevos)

Cubre: comportamiento legacy sin cambios (regresión más importante), creación síncrona exitosa con `card_token`, con `payment_source_id` (incluye la verificación de que se envía como `int`, no como el string que llega crudo del body HTTP — se encontró y corrigió este detalle real durante el propio test, ver abajo), error 400 si se pasan ambos parámetros a la vez, marcado de `Transaction.status='ERROR'` + 502 ante un fallo de Wompi, y disparo de `PaymentCommands.confirm_payment` cuando Wompi aprueba de inmediato.

**Bug real encontrado y corregido por el propio test, no por inspección manual:** `payment_source_id` llega desde `request.data` como string (`'3891'`, típico de un body HTTP), pero la API de Wompi lo espera como entero (`3891`, ver ejemplo de la documentación oficial). El test `test_initialize_with_payment_source_id_creates_transaction_synchronously` falló con `'3891' != 3891` en la primera corrida — corregido en la vista con `int(payment_source_id_raw) if payment_source_id_raw else None`.

## Verificación final

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.WompiSyncTransactionCreationTestCase` → **6/6 OK** (tras el fix del cast a `int`).
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **37/37 OK** (31 anteriores + 6 nuevos), sin regresiones.

## Estado real del checkout en vivo tras este cambio

**Sin cambios observables.** Cualquier usuario que pague hoy (modo Wompi TEST) sigue exactamente el mismo camino: `initialize/` sin `card_token`/`payment_source_id` → Widget completo → webhook. La rama nueva existe, está probada, y queda inerte hasta que la Fase 3 (frontend) la active.

## Siguiente paso

Con el adaptador construido, probado, y conectado (de forma aditiva y seguro) a `initialize/`, la Fase 2 del plan original queda completa. El siguiente paso natural es la **Fase 3 (Nuevo flujo de checkout, solo frontend)** — implementar la tokenización vía Widget en modo `tokenize`, el endpoint nuevo `POST payment/cards/tokenize/` (que todavía no se construyó — usa `WompiApiClient.create_payment_source`, no se hizo en este paso porque no fue parte de lo pedido explícitamente), y adaptar `CheckoutView.vue`/`useWompiWidget.js` para enviar `card_token`/`payment_source_id` a `initialize/` en vez de abrir el Widget completo.
