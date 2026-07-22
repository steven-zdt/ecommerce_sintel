# ADR-001 (payment) — Migración a integración API propia con Wompi

**Estado:** Propuesto — pendiente de aprobación del usuario para pasar a Fase 2.
**Fecha:** 2026-07-13
**Fase:** 1 (Diseño). No se ha escrito código en esta fase.
**Insumo:** `payment/.AGENT/docs/AUDITORIA_FASE0_MIGRACION_API_WOMPI.md` (Fase 0, completa).
**Confirmado por el usuario:** el Widget de Wompi se conserva exclusivamente para tokenización de tarjeta (captura PCI); todo lo demás (creación de transacción, seguimiento, confirmación) pasa a ser responsabilidad del backend.

---

## 1. Contexto

Hoy (ver Fase 0): el Widget de Wompi crea la transacción directamente desde el navegador del cliente; el backend es pasivo (solo prepara datos y escucha el webhook). No existe ningún cliente HTTP propio hacia Wompi (a diferencia de Nequi, que sí tiene `NequiApiClient`), no hay tabla de eventos de webhook (idempotencia solo por lock+comparación de estado), la reconciliación automática no alcanza transacciones sin `wompi_id`, y no hay correlación de logs entre los pasos de un mismo pago.

**Objetivo de esta fase:** definir el contrato técnico del nuevo flujo, la máquina de estados, la estrategia de idempotencia/recuperación, el manejo de errores y el modelo de auditoría — sin escribir código todavía. Fase 2 implementará el adaptador; Fase 3 implementará el frontend.

## 2. Advertencia metodológica (aplica a toda la Fase 1)

Varias afirmaciones de este documento sobre el comportamiento exacto de la API de Wompi (endpoints de `payment_sources`, modo de tokenización aislada del widget, deduplicación por `reference` del lado de Wompi) **deben validarse contra `docs.wompi.co` al iniciar la Fase 2**, no asumirse. Esto sigue la misma disciplina ya aplicada en el fix de sincronización de 2026-07-07 (documentado en memoria: *"validated against official Wompi docs, not assumptions"*). Donde este documento no tiene certeza, se marca explícitamente con **[VALIDAR EN FASE 2]**.

---

## 3. Decisión — arquitectura del adaptador (base de la Fase 2)

Se crea `payment/online/wompi_client.py` con una clase `WompiApiClient`, calcada del patrón ya probado en `payment/nequi/client.py::NequiApiClient`:

- URLs sandbox/producción centralizadas según `WOMPI_ENVIRONMENT`.
- Excepción propia (`WompiApiError`, con subclases para error transitorio vs. definitivo — ver §7).
- Sin lógica de negocio dentro del cliente (nada de `Order`, `Transaction`, inventario) — solo HTTP + serialización, igual que `NequiApiClient`.
- Métodos previstos:
  - `get_transaction(wompi_id)` — reemplaza la llamada `requests.get()` cruda hoy embebida en `_sync_wompi_status` (`payment/online/api/views.py`).
  - `create_payment_source(token, customer_email, acceptance_token)` **[VALIDAR EN FASE 2]** — crea una fuente de pago reutilizable a partir de un token de tarjeta, vía el endpoint `POST /payment_sources` de Wompi (mecanismo oficial para cargos posteriores sin repetir el widget).
  - `create_transaction(amount_in_cents, currency, reference, customer_email, payment_source_id \| payment_method, signature)` **[VALIDAR EN FASE 2]** — crea la transacción directamente en Wompi (`POST /transactions`) en vez de que el widget la cree del lado del navegador.
- El resto del sistema (`orders`, `inventory`, `notifications`, `operations`) sigue sin conocer nada de Wompi — sigue interactuando únicamente con `payment/shared/commands.py::confirm_order_payment()`, que no cambia de forma (Fase 2/3 no debe tocar su contrato).

## 4. Decisión — nuevo flujo de creación de transacción (tarjeta)

**Alcance importante:** este rediseño de "backend como único punto de acceso" aplica de forma completa a **pagos con tarjeta** (nuevas y guardadas). **PSE y métodos con redirección bancaria mantienen el flujo de redirect actual** — es un requisito del banco/Wompi que el usuario autentique en su banco, no una limitación del widget que se pueda eliminar. Esto no estaba explícito en el plan original y se deja anotado aquí para que quede claro que "backend único punto de acceso" no es literal al 100% para PSE.

Secuencia objetivo para tarjeta:

1. **Tokenización (Widget, sin cambios de alcance PCI):** el usuario ingresa los datos de tarjeta en el Widget, en su modo de **solo tokenización** **[VALIDAR EN FASE 2: confirmar que el SDK de Wompi soporta un modo de tokenización aislado del checkout completo actual]** → el navegador obtiene un `token` que nunca pasa por el backend en texto plano (igual que hoy, sin retroceso de seguridad).
2. **Registro de la tarjeta:** el frontend envía `token` a un endpoint nuevo del backend (`POST payment/cards/tokenize/`, a definir en Fase 2/3) → el backend llama `WompiApiClient.create_payment_source(...)` y guarda el `payment_source_id` devuelto en `TokenizedCard` (reemplaza el flujo manual actual de `CustomerCardsView.vue`, donde hoy el usuario pega el token a mano — ver Fase 0 §1.2).
3. **Pago (nuevo o con tarjeta guardada):** `POST payment/payments/initialize/` (endpoint existente, comportamiento evolucionado) — en vez de solo crear un `Transaction PENDING` local y devolver claves para que el widget abra el checkout completo, el backend llama `WompiApiClient.create_transaction(...)` **de forma síncrona**, usando el `payment_source_id` (tarjeta guardada) o el `token` recién obtenido (tarjeta nueva). Devuelve al frontend el estado inicial (normalmente `PENDING`, a veces `APPROVED` sincrónicamente) y el `wompi_id` — **inmediatamente conocido**, sin depender del webhook para tenerlo.
4. **Seguimiento:** el frontend sigue usando el mismo patrón de polling ya construido y probado (`transaction-status/`/`confirmation/`, Fase 0 confirma que ya es sólido) — cambia el disparador (ya no se abre un widget de checkout, se empieza a hacer polling apenas vuelve la respuesta de `initialize/`), pero no la lógica de polling en sí.
5. **Confirmación autoritativa:** el webhook sigue siendo la única fuente de verdad para transicionar a `APPROVED`/`DECLINED` — sin cambios de filosofía respecto a hoy (Wompi: *"siempre usar los webhooks para finalizar la integración"*).

**Beneficio estructural directo de este diseño:** al crear la transacción de forma síncrona en el paso 3, `wompi_id` queda disponible **desde el primer momento**, no solo cuando llega el webhook. Esto resuelve de raíz el hallazgo R6 de la Fase 0 (la reconciliación no alcanzaba transacciones sin `wompi_id`) — no como un parche adicional, sino como consecuencia natural de mover la creación al backend.

## 5. Máquina de estados

**Se mantienen exactamente los mismos 5 estados ya validados de Wompi** (`PENDING`, `APPROVED`, `DECLINED`, `VOIDED`, `ERROR`) — no se inventa ningún estado nuevo en `Transaction.status` (repitiendo la lección ya aprendida en 2026-07-07: Wompi no tiene `EXPIRED`, y un timeout de UI no es un estado de negocio).

Lo que sí se agrega es **historial de transiciones**, separado del estado actual:

- Nuevo modelo `TransactionEvent` (Fase 2): `transaction FK`, `source` (`webhook` | `wompi_api_sync` | `wompi_api_create`), `wompi_event_id` (nullable — Wompi puede no enviarlo en todos los payloads, **[VALIDAR EN FASE 2]**), `previous_status`, `new_status`, `raw_payload` (JSON, nunca datos de tarjeta — Wompi no los reenvía, verificado en la Fase 0 que la app nunca los recibe), `correlation_id`, `received_at`, `processed` (bool), `error_detail` (nullable).
- `Transaction.status` sigue siendo el estado *actual* (para todas las queries existentes, sin romper nada); `TransactionEvent` es el *historial* append-only, nunca se edita ni se borra.
- Diagrama de transición (sin cambios respecto al de Wompi, documentado para que quede explícito en el ADR):

```
PENDING ──(webhook/sync: approved)──▶ APPROVED
   │
   ├──(webhook/sync: declined)──▶ DECLINED
   ├──(webhook/sync: voided)────▶ VOIDED
   └──(webhook/sync: error)─────▶ ERROR

APPROVED, DECLINED, VOIDED, ERROR son terminales -- ninguna transicion
sale de ahi (ya validado hoy: "si ya estaba APPROVED y llega APPROVED
otra vez, ignora").
```

## 6. Idempotencia (end-to-end, cierra R3 y R7 de la Fase 0)

1. **Duplicación de orden en reintentos (R3):** `OrderCommands.create_from_cart()` (backend) recibe un `idempotency_key` opcional generado por el frontend (ej. UUID minteado una vez al entrar a `/checkout`, persistido en `sessionStorage` hasta completar o abandonar explícitamente). Si ya existe una orden `PENDING_PAYMENT` con esa clave para el mismo usuario, el backend **devuelve la orden existente** en vez de crear una nueva. Se prefiere idempotencia del lado del backend (no solo del frontend) porque es más robusta ante reintentos de red, doble clic, o pestañas duplicadas.
2. **Transacción hacia Wompi:** antes de llamar `WompiApiClient.create_transaction(...)`, el backend hace `select_for_update()` sobre la `Transaction` local y solo llama a Wompi si sigue `PENDING` sin `wompi_id` — evita doble creación si el mismo request llega dos veces (ej. doble clic en "Pagar").
3. **Webhook:** se mantiene el mecanismo actual (`select_for_update()` + comparación de estado) como primera capa, y se añade `TransactionEvent` como segunda capa/auditoría — deduplicación por `wompi_event_id` cuando esté presente en el payload **[VALIDAR EN FASE 2]**, con fallback al mecanismo de estado ya probado si Wompi no incluye un ID de evento estable.

## 7. Estrategia de recuperación

- **Reconciliación (`reconcile_pending_wompi_transactions`):** sigue corriendo cada 5 minutos (sin cambiar el intervalo, ya validado como razonable), pero el universo de transacciones que puede alcanzar crece automáticamente porque casi todas tendrán `wompi_id` desde el momento de creación (§4, punto 3) — el gap actual (transacciones sin `wompi_id` y sin visita a `/payment/result`) se reduce a casos verdaderamente raros (falla de red entre el `create_transaction` y el guardado local del `wompi_id`, por ejemplo).
- **Transacciones verdaderamente abandonadas** (siguen `PENDING` después de varios ciclos de reconciliación, ej. > 24h): **no se les asigna un estado inventado** — se preserva `status='PENDING'` (fiel al estado real de Wompi) y se marcan para revisión vía un campo operativo nuevo (`Transaction.needs_manual_review`, booleano, o una vista/filtro en el panel admin basado en antigüedad — a decidir el mecanismo exacto en Fase 2, el punto de diseño es que la distinción "pendiente normal" vs. "pendiente sospechoso" no contamine el campo `status` que ya se usa como fuente de verdad de Wompi en todo el sistema).
- **Errores de llamada a Wompi** (creación o consulta): reintentos automáticos solo para errores transitorios (timeout, 5xx) con backoff — nunca reintentar automáticamente un 4xx de negocio (tarjeta rechazada, datos inválidos), eso se resuelve informando al usuario, no reintentando en silencio.

## 8. Manejo de errores

- `WompiApiClient` distingue (mirror del patrón `NequiApiError` ya existente) entre error transitorio (red, timeout, 5xx — reintentable) y error definitivo (4xx, rechazo de negocio — no reintentable, se propaga al usuario).
- El endpoint `initialize/` deja de fallar silenciosamente: si `create_transaction` falla tras agotar reintentos, la `Transaction` local pasa explícitamente a `ERROR` (no queda huérfana en `PENDING` sin ningún rastro) y el frontend recibe un mensaje claro para reintentar — cerrando parte del hallazgo de la Fase 0 sobre errores de red a mitad del checkout.
- El webhook, ante un fallo de procesamiento (excepción no controlada), ya no solo queda en un log de texto — se guarda un `TransactionEvent(processed=False, error_detail=...)` para que Fase 7 (panel admin) pueda mostrar "webhook recibido pero no procesado" como cola de triage manual, en vez de perderse en logs.

## 9. Modelo de auditoría / observabilidad

- **Correlation ID:** se mintea un UUID por intento de checkout (al llamar `initialize/` por primera vez), se propaga en:
  - Los logs (`logger.info(..., extra={'correlation_id': cid})`) de cada paso (creación de orden, creación de transacción, webhook, confirmación, notificación).
  - Cada fila de `TransactionEvent` (§5).
  - La respuesta al frontend (para que aparezca en cualquier reporte de error que el cliente comparta con soporte).
- **`SecurityEvent`:** se agrega `PAYMENT_APPROVED` a `EVENT_CHOICES` (hoy solo existe `PAYMENT_DECLINED`, asimetría real detectada en Fase 0) para que el registro de auditoría de seguridad quede simétrico entre aprobaciones y rechazos.
- **Logging:** se mantiene `logging` estándar de Django (no se introduce `structlog` como dependencia nueva salvo que el usuario lo pida explícitamente — es una decisión de alcance a confirmar, ver §11) pero con `extra={'correlation_id': ...}` consistente en todos los `logger.info/warning/error` de `payment/`, para que sea grepeable de forma fiable incluso sin structlog.

## 10. Contrato técnico — resumen de endpoints (Fase 2/3, no implementado todavía)

| Endpoint | Cambia? | Detalle |
|---|---|---|
| `POST payment/payments/initialize/` | **Sí, evolución de comportamiento** | Antes: crea `Transaction PENDING` + claves para el widget. Ahora: crea la transacción directamente en Wompi (síncrono) y devuelve estado inicial + `wompi_id`. Mismo path, mismo método, contrato de entrada compatible (sigue recibiendo `order_uuid`). |
| `GET payment/payments/transaction-status/` | No | Se mantiene igual (polling liviano, ya sólido). |
| `GET payment/payments/confirmation/` | No | Se mantiene igual (payload completo). |
| `POST payment/payments/webhook/` | Interno únicamente | Sigue siendo el mismo endpoint público hacia Wompi; internamente ahora también escribe `TransactionEvent`. |
| `POST payment/cards/tokenize/` | **Nuevo** | Recibe el `token` del widget en modo tokenización, crea el `payment_source_id` en Wompi, guarda `TokenizedCard`. Reemplaza el formulario manual de `CustomerCardsView.vue`. |
| `POST payment/cards/` (creación manual actual) | A decidir en Fase 3 | ¿Se elimina el flujo manual de pegar el token a mano, o se conserva como fallback interno/QA? Recomendación: eliminarlo una vez el flujo automático esté probado, para no mantener dos caminos de alta de tarjeta. |

## 11. Puntos decididos por el usuario (2026-07-13)

1. **PSE queda excluido** del alcance de "backend único punto de acceso" — mantiene el flujo de redirección bancaria actual tal cual. Confirmado.
2. **No se introduce `structlog`** — se usa `logging` estándar de Django + `extra={'correlation_id': ...}`. Confirmado.
3. **El formulario manual de alta de tarjeta** en `CustomerCardsView.vue` **se elimina** una vez el flujo automático (`POST payment/cards/tokenize/`) esté implementado y probado. Confirmado.

---

## Siguiente paso

**Estado: ADR aprobado**, incluyendo las 3 decisiones de §11.

**Fase 2 (adaptador `WompiApiClient` + conexión a `initialize/`) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE2_ADAPTADOR_WOMPI.md`. Los puntos `[VALIDAR EN FASE 2]` de este documento fueron confirmados contra `docs.wompi.co`. `WompiCommands.initialize_transaction()` y `WompiPaymentViewSet.initialize()` ahora aceptan `card_token`/`payment_source_id` opcionales que activan la creación síncrona en Wompi — **de forma aditiva, sin cambiar el comportamiento del único camino real usado hoy por el checkout en vivo** (el frontend actual nunca envía esos campos; eso es Fase 3). 17 tests nuevos en total, 37/37 en verde en la suite completa de `payment/`.

**Fase 3a (tokenización automática, frontend) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE3A_TOKENIZACION_FRONTEND.md`. Ajuste real encontrado: `TokenizedCard` ya guardaba `token_id` reutilizable — nunca hizo falta `payment_source_id`, así que no se necesitó ningún endpoint backend nuevo, solo automatizar el frontend (`useCardTokenization.js` + `CustomerCardsView.vue`). Bug preexistente encontrado y corregido de paso: `CustomerLayout.vue` nunca mostraba toasts en toda la app de cliente.

**Fase 3b (checkout usa tarjetas, guardadas o nuevas) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE3B_CHECKOUT_TARJETA.md`. Decisión de UX confirmada por el usuario: sub-opciones "Tarjeta"/"PSE / Otros" dentro de "Pago en línea". El pago con tarjeta ya no abre el Widget completo — PSE sigue exactamente igual. **Fase 3 del plan original queda completa.**

**Fase 4 (observabilidad) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE4_OBSERVABILIDAD.md`. `Transaction.correlation_id` + modelo nuevo `TransactionEvent` (historial append-only en los 3 puntos de contacto con Wompi) + `SecurityEvent.PAYMENT_APPROVED` (simetría con `PAYMENT_DECLINED`). Ajuste real encontrado: `extra={}` en logging no funciona con el formatter global del proyecto — se usó interpolación de string (`corr=%s`), mismo patrón ya usado en todo `payment/`. 7 tests nuevos, 44/44 en verde en la suite completa. **Fase 4 del plan original queda completa.**

**Fase 5 (migración gradual / feature flag) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE5_MIGRACION_GRADUAL.md`. `PaymentFeatureFlags` (singleton, editable desde `/admin/` sin deploy) + kill-switch real aplicado en backend (`initialize/` responde 403 con `card_token` si está desactivado, no solo se oculta en la UI) + frontend que falla cerrado ante cualquier duda. El Widget completo (PSE/Otros) nunca se eliminó — la "convivencia temporal" ya existía por diseño desde la Fase 3b. 6 tests nuevos, 50/50 en verde en la suite completa. **Fase 5 del plan original queda completa.** (Durante esta fase se resolvió también un incidente real de producción — `sintel_prod_nginx` en crash-loop — no relacionado con el código de esta fase, ver `feedback_docker_compose_recreate_vs_restart` en memoria.)

**Fase 6 (reconciliación automática mejorada) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE6_RECONCILIACION.md`. Cierra el hueco de la Fase 0: `_sync_wompi_status()` ahora deja `TransactionEvent` en sus dos ramas de error (antes solo un log de texto); `reconcile_pending_wompi_transactions()` gana una segunda pasada que marca (una sola vez, sin re-marcar) transacciones `PENDING` sin `wompi_id` de más de 30 min como "abandonadas" — sin inventar un estado nuevo en `Transaction.status`. 5 tests nuevos, 55/55 en verde en la suite completa. **Fase 6 del plan original queda completa.**

**Fase 7 (panel administrativo con acciones reales) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE7_PANEL_ADMIN.md`. `AdminPaymentViewSet` ganó `resync/`, `events/` y `feature-flags/` (GET/PATCH); `PaymentTransactionsAdminView.vue` ganó botones reales "Reconciliar"/"Historial" en la pestaña Wompi y un switch para el flag de la Fase 5. Bug real encontrado por el propio test (`bool('False') is True` en Python, formato multipart por defecto) y corregido. 8 tests nuevos, 63/63 en verde en `payment`, 50/50 en `dashboard`. Verificado en el navegador con tráfico real (sin tocar la API de Wompi — el botón "Reconciliar" se verificó solo por presencia en el DOM, nunca se hizo clic). **Fase 7 del plan original queda completa.**

**Fase 8 (alertas operativas) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE8_ALERTAS_OPERATIVAS.md`. Decisión clave: se reusó `SecurityEvent` (ya visible en `/panel/seguridad`) en vez de `dispatch_notification`, para no arriesgar notificar por error al cliente vía email (la Fase 6 decidió explícitamente no hacerlo). 2 tipos de evento nuevos: `PAYMENT_TRANSACTION_ABANDONED` (Fase 6) y `PAYMENT_FEATURE_FLAG_CHANGED` (Fase 5/7, ambos caminos: panel Vue y Django admin, solo si el valor realmente cambia). 19 tests nuevos, 69/69 en `payment`, 4/4 en `security`. Verificado en el navegador: el evento aparece de inmediato en `/panel/seguridad` tras un toggle real. **Fase 8 del plan original queda completa.**

**Fase 9 (pruebas E2E y de carga) completada 2026-07-13** — ver `payment/.AGENT/docs/FASE9_PRUEBAS_E2E_CARGA.md`. 3 specs E2E nuevos y permanentes (`frontend/e2e/wompi-checkout.spec.js`), estables tras varias iteraciones reales de depuración (no escritos y asumidos correctos). Hallazgo de infraestructura real más importante del proyecto: Chromium corriendo dentro del contenedor `ecommerce_sintel_frontend` no puede alcanzar `localhost:8000` (topología de red de Docker) — resuelto con un bridge de `page.route()` vía `http.request` crudo de Node hacia `nginx:80` con `Host: localhost` spoofeado (algo que `fetch()` del navegador prohíbe pero el módulo `http` nativo permite). Prueba de carga nueva (`payment-feature-flags-load-node.js`, único endpoint público/sin estado del proyecto): 100% éxito bajo 50 VUs, p99 real de 362ms reportado sin ajustar el umbral para "hacerlo pasar" — anotado como pendiente de verificar en un entorno no compartido antes de asumirlo representativo de producción. **Fase 9 del plan original queda completa.**

**Fase 10 (documentación final) completada 2026-07-13.** `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` (SSoT de la app) actualizado a fondo: nueva sección 10 completa (adaptador `WompiApiClient`, flujo de tarjeta backend-directo, tokenización automática, checkout dual-path, panel admin, feature flag), modelos `TransactionEvent`/`PaymentFeatureFlags` documentados, tabla de migraciones al día, anti-patrones nuevos, y corrección de una discrepancia real que arrastraba el documento desde antes de este proyecto (paso `FulfillmentCommands.ensure_shipment_for_order` nunca documentado en la tabla de `confirm_order_payment()`, encontrado en la Fase 0). `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` actualizado con un resumen de alto nivel y referencia cruzada al documento detallado (sin duplicar el contenido). **Fase 10 del plan original queda completa — el proyecto de 10 fases está terminado.**
