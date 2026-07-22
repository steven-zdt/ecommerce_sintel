# Auditoría Fase 0 — Migración a integración API propia con Wompi

**Fecha:** 2026-07-13
**Alcance:** Solo lectura. Ningún archivo de código fue modificado en esta fase.
**Objetivo del proyecto completo (10 fases, propuestas por el usuario):** pasar de "el Widget de Wompi maneja todo el flujo de pago" a "el backend propio es el único punto de acceso a Wompi", manteniendo el Widget únicamente para tokenización segura (captura de datos de tarjeta, PCI compliance), con mejor idempotencia, observabilidad y reconciliación.

---

## 0. Validación del plan recibido

Antes de auditar, se contrastó el plan pedido contra el código real:

- **Los componentes que el plan nombra existen y están vigentes:** `useWompiWidget.js`, `PaymentResultView.vue`, `WompiPaymentViewSet`, `PaymentCommands`, webhook, polling, tarea Celery de reconciliación, logs. Ninguno es un nombre obsoleto o inventado.
- **Inconsistencia real detectada en el texto del plan, a resolver antes de ejecutar Fase 3:** la "Fase 3 — Nuevo flujo de checkout" dice *"Eliminar dependencias del flujo actual basadas en el Widget"*, pero la sección "Mi recomendación" del mismo mensaje dice lo contrario: *"no eliminaría inmediatamente el Widget: lo mantendría solo para la tokenización"*. Ambas no pueden ser ciertas a la vez tal como están escritas. **Se adopta la segunda interpretación** (mantener el Widget solo para tokenización) porque es la técnicamente correcta según la propia documentación de Wompi: la app captura datos de tarjeta hoy exclusivamente vía Widget (nunca los recibe el backend en texto plano), y reemplazar eso por un formulario propio implicaría entrar en alcance PCI-DSS — fuera de lo que este proyecto debería asumir. Se deja anotado para que el usuario confirme esta interpretación antes de Fase 3.
- **`IMPLEMENTATION_SUMMARY(6).md`**, mencionado como documento a actualizar en la Fase 10, **no existe en el repo** (mismo hallazgo que en el proyecto de aislamiento de dominio del panel — solo existe `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`, sin numeración). Si el usuario tiene una versión "(6)" en otro lugar, indicarla; si no, se asume que se refiere al único archivo existente.
- El resto del plan (Fases 0-2, 4-9) es técnicamente coherente con el estado real del código, según el detalle de abajo.

---

## 1. Estado actual (resumen ejecutivo)

### 1.1 Flujo hoy: Widget hace todo, backend es pasivo

`CheckoutView.vue` crea la `Order` primero (`POST orders/orders/create_from_cart/`), luego pide al backend `POST payment/payments/initialize/` (que solo crea una `Transaction PENDING` + calcula `integrity_signature`, sin llamar a Wompi todavía) y **el frontend abre el Widget de Wompi directamente en el navegador del cliente** (`useWompiWidget.js`). Es el Widget — no el backend — quien realmente se comunica con Wompi para procesar la tarjeta y crear la transacción del lado de Wompi. El backend se entera del resultado por dos vías independientes y de fiabilidad distinta:
- **Webhook** (`POST /api/v1/payment/payments/webhook/`) — la fuente de verdad real, con verificación HMAC de firma.
- **Callback del Widget en el navegador** — usado solo para UX inmediata (mostrar un toast y navegar a `/payment/result`), el código ya documenta explícitamente que nunca se usa como fuente de verdad de negocio.

### 1.2 No existe hoy ningún camino de pago 100% backend

Ni siquiera para tarjetas ya tokenizadas: `CustomerCardsView.vue` es un CRUD de tarjetas donde el usuario debe **pegar manualmente** el `token_id` que devolvería el Widget — no hay integración automática, y ningún checkout (`CheckoutView`, `ServiceCheckoutModal`, `RentalConfirmationView`) ofrece la opción de pagar con una tarjeta ya guardada. Esto confirma que las Fases 2-3 del plan son terreno genuinamente nuevo, no una extensión de algo que ya funcione parcialmente.

### 1.3 Wompi no tiene un cliente HTTP encapsulado (Nequi sí)

`payment/nequi/client.py::NequiApiClient` es exactamente el patrón que el plan pide crear para Wompi en su Fase 2 ("adaptador desacoplado") — ya existe como precedente funcionando en el mismo repo. Wompi, en cambio, tiene su única llamada saliente (`_sync_wompi_status`) con `requests.get()` crudo, URLs hardcodeadas inline y manejo de errores ad-hoc, embebida dentro de `payment/online/api/views.py` junto a la lógica del ViewSet.

### 1.4 Idempotencia real hoy: solo lock + comparación de estado, sin registro de eventos

El webhook usa `select_for_update()` + "si ya estaba `APPROVED` y llega `APPROVED` otra vez, ignora" — funciona (hay un test de concurrencia real con threads que lo confirma), pero **no hay una tabla de eventos webhook procesados** (sin `event_id` de Wompi, sin dedupe explícito más allá del estado). Si Wompi reenvía un webhook con datos distintos a los ya guardados, se reprocesaría sin protección adicional.

### 1.5 Observabilidad real hoy: logging de texto plano, sin correlación

No hay `structlog`, no hay JSON estructurado, no hay `request_id`/`correlation_id`/`trace_id` en ningún punto de `payment/`. La única forma de seguir un pago a través de los logs es grepear manualmente por `reference`/`order.uuid`/`wompi_id`. Sí existe un sistema de auditoría aparte y más confiable — `security.SecurityEvent` — pero cubre solo 3 eventos puntuales de pagos (firma inválida, pago rechazado, tarjeta eliminada), no un log de negocio completo.

### 1.6 Panel admin de pagos: 100% de solo lectura

`PaymentTransactionsAdminView.vue` + `AdminPaymentViewSet` (backend) solo listan transacciones (Wompi/Nequi/COD) con filtros. No hay ningún botón de reconciliación manual, ni acción de admin sobre una transacción atascada — confirma que la Fase 7-8 del plan ("panel administrativo de pagos", "alertas operativas") es trabajo nuevo real, no una mejora incremental.

### 1.7 Reconciliación automática: existe, con una limitación de diseño documentada

`reconcile_pending_wompi_transactions` corre cada 5 minutos (confirmado leyendo la migración `0008_seed_reconcile_periodic_task.py`, no asumido) y solo alcanza transacciones que **ya tienen `wompi_id`** — el propio docstring documenta que Wompi no ofrece búsqueda por `reference`, así que una transacción que nunca recibió webhook NI el usuario volvió a `/payment/result` (por lo que nunca se hizo `_sync_wompi_status` con el hint) queda huérfana sin ningún mecanismo de recuperación. Este es probablemente el gap más concreto que la Fase 6 del plan ("reconciliación automática") debería cerrar.

### 1.8 Frontend: cero cobertura de tests en el flujo de pagos

Ningún test cubre `useWompiWidget.js`, `CheckoutView.vue`, `PaymentResultView.vue`, `NequiPendingView.vue`, `ServiceCheckoutModal.vue` ni `CustomerCardsView.vue`. Esto es un riesgo real para cualquier fase que toque el frontend (Fase 3 en adelante): no hay red de seguridad automatizada.

### 1.9 Riesgo de duplicación en el checkout actual (independiente del proyecto de migración, pero relevante)

`CheckoutView.vue::submitOrder()` crea dirección + orden ANTES de abrir el Widget. Si el usuario cierra el Widget sin pagar y pulsa "Pagar" de nuevo, **se crea una segunda dirección y una segunda orden** — no hay detección de orden huérfana ni idempotencia en el frontend. No es parte del alcance original de "aislar el dominio del panel" ni fue introducido por trabajo reciente; es deuda preexistente que la Fase 1 (diseño del nuevo flujo) debería resolver explícitamente, ya que el plan menciona "idempotencia" como objetivo de diseño.

---

## 2. Riesgos

| # | Riesgo | Severidad | Detalle |
|---|---|---|---|
| R1 | **Sistema de pagos en producción real** (aunque hoy en modo TEST de Wompi) | Alta (por naturaleza del dominio) | Cualquier bug introducido en el nuevo flujo puede significar dinero real cobrado/no cobrado incorrectamente una vez se pase a llaves `prod_...`. Cada fase debe probarse exhaustivamente en modo test antes de considerar producción. |
| R2 | **Cero tests de frontend en el flujo de checkout** | Alta | Ver §1.8. Cualquier cambio en Fase 3 se hace sin red de seguridad automatizada — se recomienda escribir tests de regresión ANTES de tocar `CheckoutView.vue`/`useWompiWidget.js`, no después. |
| R3 | **Duplicación de orden/dirección en reintentos** (§1.9) | Media-Alta | Preexistente, no introducido por este proyecto, pero el nuevo diseño de Fase 1 debe resolverlo explícitamente o el problema persiste en el nuevo flujo. |
| R4 | **`WOMPI_EVENTS_SECRET` sin configurar deja pasar webhooks sin validar firma** (con solo un `SecurityEvent CRITICAL` como constancia, sin bloquear) | Media (mitigado en este entorno) | Confirmado que en `.env.production` real el secreto **sí está configurado** (aunque en modo `test`, ver Wompi en modo TEST — decisión ya tomada por el usuario, roadmap Fase 16). El código igual debería considerarse endurecer esto en Fase 4 (fallar cerrado en vez de abierto cuando falta el secreto, o al menos que sea imposible desplegar a producción sin él). |
| R5 | **Nequi: lado "order" sin liberación en pago rechazado** (gap documentado en el propio código, `payment/nequi/services/commands.py:100-106`) | Media | Solo el lado `rental_request` libera el slot al fallar el pago; una `Order` normal con Nequi rechazado no libera nada. Fuera del alcance directo de "migración Wompi", pero como el plan toca idempotencia/estados de forma transversal, vale la pena que la Fase 1 decida si se corrige junto o se documenta como excluido explícitamente. |
| R6 | **`OrderConfirmedView.vue` parece código huérfano** que duplica lógica de `PaymentResultView.vue` sin polling automático, y ningún flujo real navega hacia él | Baja | No es un riesgo del proyecto en sí, pero conviene que el usuario confirme si sigue en uso antes de que la Fase 3 lo modifique o lo deje divergir aún más del flujo real. |
| R7 | **Sin idempotency key por evento webhook** (§1.4) | Media | Funciona hoy gracias al lock + comparación de estado, pero es más frágil que un registro explícito de eventos procesados — la Fase 1 (diseño del nuevo flujo) debería decidir si se agrega una tabla de eventos, según el plan ya lo contempla ("Idempotencia" como punto de diseño explícito). |
| R8 | **Sin correlación de logs** (§1.5) | Baja-Media | No bloquea nada hoy, pero dificulta debug de incidentes reales de pago. Coincide exactamente con el objetivo de la Fase 4 del plan ("Correlation ID, Request ID, logs estructurados"). |

---

## 3. Dependencias

- **`NequiApiClient`** (`payment/nequi/client.py`) — patrón de referencia ya validado en producción para construir el adaptador de Wompi (Fase 2 del plan). Reutilizar su forma (cliente HTTP aislado + excepción propia + URLs sandbox/prod centralizadas), no reinventar.
- **`_sync_wompi_status`, `_verify_wompi_event_signature`, `_build_rental_confirmation`** (`payment/online/api/views.py`) — lógica a extraer hacia el futuro adaptador; hoy viven acopladas al ViewSet.
- **`payment/shared/commands.py::confirm_order_payment()`** — SSoT real de "qué pasa cuando un pago se aprueba" (fulfillment, inventario, notificación), compartida por Wompi/Nequi. Cualquier cambio de Fase 1-3 debe seguir pasando por aquí, no reimplementar el flujo de confirmación en el nuevo adaptador.
- **`security.SecurityEvent`/`SecurityCommands.log_event()`** — sistema de auditoría ya existente; la Fase 4 (observabilidad) debería decidir si lo extiende (agregar `PAYMENT_APPROVED`, eventos de reconciliación) en vez de crear un sistema de auditoría paralelo.
- **`django_celery_beat.DatabaseScheduler`** — cualquier tarea nueva de reconciliación/observabilidad debe registrarse vía migración de datos (`PeriodicTask`/`CrontabSchedule`), igual que `payment/migrations/0008_seed_reconcile_periodic_task.py`. Un `CELERY_BEAT_SCHEDULE` en `settings.py` es ignorado en este proyecto.
- **`NotificationCommands.dispatch_notification()`** — mecanismo ya centralizado (11 apps lo usan) para cualquier notificación nueva que la Fase 4/6 quiera agregar (ej. notificar al cliente cuando un pago es rechazado, que hoy no ocurre — ver hallazgo en auditoría backend, sección 6 del reporte de subagente).

---

## 4. Archivos afectados por fase (mapa, ninguno tocado todavía)

| Archivo/módulo | Fase que probablemente lo toque |
|---|---|
| `payment/online/api/views.py`, `payment/online/services/commands.py` | Fase 2 (extraer adaptador), Fase 1 (diseño) |
| Nuevo módulo, ej. `payment/online/wompi_client.py` (a definir en Fase 1) | Fase 2 |
| `payment/models.py` (posible tabla de eventos webhook / campos de auditoría) | Fase 1 (diseño), Fase 4 (observabilidad) |
| `frontend/src/composables/useWompiWidget.js`, `CheckoutView.vue` | Fase 3 |
| `frontend/src/views/payment/PaymentResultView.vue` | Fase 3-4 |
| `frontend/src/views/customer/account/CustomerCardsView.vue` | Fase 3 (si se conecta tokenización automática del Widget) |
| `payment/tasks.py`, nueva migración de `PeriodicTask` | Fase 5-6 |
| `dashboard/api/views.py::AdminPaymentViewSet`, `frontend/.../PaymentTransactionsAdminView.vue` | Fase 7 |
| `security/models.py` (posibles nuevos `EVENT_CHOICES`) | Fase 4, Fase 8 (alertas) |
| `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md`, `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` | Fase 10 |
| Tests nuevos: `payment/tests.py` (backend, ya con 20 tests de base) y tests de frontend (hoy en cero) | Todas las fases que toquen código, especialmente antes de Fase 3 |

---

## 5. Impacto esperado

- **Modo TEST actual de Wompi (`WOMPI_ENVIRONMENT=test`):** ninguna fase de este proyecto debería requerir cambiar esto — es una decisión ya tomada por el usuario (roadmap Fase 16) y no está en el alcance de "migrar el mecanismo de integración". El proyecto puede y debe probarse completo en modo test antes de considerar producción.
- **Clientes finales:** ningún cambio visible hasta la Fase 3 (nuevo flujo de checkout) — Fases 0-2 son extracción/preparación de backend sin tocar UI.
- **Reintentos y checkout duplicado (R3):** si la Fase 1 lo resuelve, es una mejora de UX real (menos órdenes huérfanas en BD) sin downside.
- **Feature flag de Fase 5:** permite reversión inmediata si el nuevo flujo API muestra problemas en producción — reduce el riesgo de las fases posteriores significativamente, buena decisión de secuencia ya presente en el plan del usuario.

---

## 6. Plan de migración (validado, con el ajuste de la sección 0)

Se valida el plan de 10 fases del usuario, con dos ajustes:

1. **Fase 3** se interpreta como: *"eliminar la dependencia del Widget para el flujo completo de creación/gestión de la transacción, pero conservarlo exclusivamente para la captura tokenizada de datos de tarjeta (PCI)"* — no "eliminar el Widget" a secas, resolviendo la inconsistencia de §0.
2. Se sugiere que la Fase 1 (diseño) incluya explícitamente una decisión sobre R3 (duplicación de orden en reintentos) y R7 (tabla de eventos webhook vs. solo lock+estado), ya que ambos son prerequisitos naturales de "idempotencia" y "estrategia de recuperación", que el propio plan ya lista como entregables de esa fase.

Las Fases 0, 2, 4, 5 y 6-10 tal como las planteó el usuario son técnicamente sólidas y coherentes con el estado real del código (verificado en esta auditoría) — no requieren cambios.

---

## Siguiente paso

Según las reglas del propio encargo: **me detengo aquí y solicito tu aprobación** antes de avanzar a Fase 1 (Diseño del nuevo flujo API — contrato técnico, máquina de estados, idempotencia, estrategia de recuperación, manejo de errores, modelo de auditoría — sin escribir código todavía).

Puntual: ¿confirmas la interpretación de la Fase 3 (§0) — Widget se conserva solo para tokenización, no se elimina por completo?
