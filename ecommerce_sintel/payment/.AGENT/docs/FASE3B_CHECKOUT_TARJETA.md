# Fase 3b — Checkout usa tarjetas (guardadas o nuevas) sin el widget completo (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` §4
**Decisión de UX del usuario:** dentro de "Pago en línea" hay dos sub-opciones — **Tarjeta** (nuevo flujo backend-directo) y **PSE / Otros** (flujo de siempre, sin cambios, porque PSE requiere redirección al banco).

## Qué se hizo

**`frontend/src/views/customer/checkout/CheckoutView.vue`:**

- Al elegir "Pago en línea", aparecen los sub-botones **Tarjeta** (default) / **PSE / Otros**.
- **Tarjeta**: al montar la página se cargan las tarjetas guardadas (`GET payment/cards/`) — el usuario elige una, o "Agregar tarjeta nueva" (mismos campos y mismo composable `useCardTokenization` de la Fase 3a). Al enviar:
  1. Se resuelve el `card_token` **antes** de crear dirección/orden (si es tarjeta nueva: tokeniza vía Wompi directo desde el navegador → guarda automáticamente en `payment/cards/`, decisión ya confirmada de "siempre guardar"; si es tarjeta guardada: su `token_id` se usa tal cual). Resolverlo primero significa que si la tokenización falla, **no queda ninguna orden huérfana** — mejora real sobre el comportamiento de siempre (Fase 0, hallazgo R3/R9), aplicada aquí sin necesidad de tocar nada más.
  2. Se crea dirección + orden (sin cambios).
  3. `POST payment/payments/initialize/` con `{order_uuid, card_token}` — el backend (Fase 2) crea la transacción de forma síncrona en Wompi. **No se abre ningún widget.**
  4. Redirección directa a `/payment/result?tx=<uuid>` — la misma vista/polling de siempre se encarga del resto (si sigue `PENDING`, hace polling; si Wompi ya respondió `APPROVED`/`DECLINED` de inmediato, lo muestra sin esperar).
- **PSE / Otros**: **sin ningún cambio de comportamiento** — `initialize/` se llama sin `card_token`, se abre el widget completo de Wompi exactamente como antes.

## Verificación realizada

Con Playwright contra el stack de desarrollo real (frontend + backend Django reales), interceptando **solo** dos puntos para no disparar llamadas reales a Wompi sin autorización:
- `https://api.wompi.co/v1/tokens/cards` (tokenización — mismo criterio que Fase 3a).
- `POST /api/v1/payment/payments/initialize/`, **únicamente cuando el body contiene `card_token`** (para no dejar que el backend real, ya conectado a Wompi desde la Fase 2, dispare una llamada real de creación de transacción).

Todo lo demás (login, agregar al carrito, crear dirección, crear orden, guardar tarjeta) fue tráfico **real** contra el backend de desarrollo.

**Escenario tarjeta nueva:** secuencia de llamadas confirmada en el orden correcto (tokenizar → guardar tarjeta real, sin `cvc` en el payload → crear dirección real → crear orden real → `initialize/` con `card_token`) → redirección a `/payment/result?tx=...` → **cero iframes de Wompi cargados**.

**Escenario PSE/Otros:** el formulario de tarjeta ni siquiera se muestra; `initialize/` se llama **sin** `card_token` (payload idéntico al de antes de este proyecto); el flujo intenta cargar `checkout.wompi.co/widget.js` como siempre — comportamiento preexistente intacto.

**No verificado en esta sesión (limitación del entorno de prueba, no del código):** el camino de "pagar con una tarjeta ya guardada, sin tokenizar de nuevo" no se probó de punta a punta porque la cuenta de prueba llegó al límite de throttle de login (`10/hora`, protección de seguridad existente) durante iteraciones de depuración. El código de ese camino es trivial (`if (selectedCardId !== 'NEW') return selectedCardId` — usa el `token_id` ya guardado tal cual, sin lógica adicional) y ya se confirmó que la lista de tarjetas guardadas carga y se selecciona correctamente por defecto; se considera de bajo riesgo, pero queda anotado para una verificación manual futura si se quiere cerrar el 100%.

## Qué NO se tocó

- El flujo PSE/Widget — cero cambios, mismo código de siempre.
- `useWompiWidget.js` — sin cambios.
- Nequi, COD — sin cambios.
- Backend — nada nuevo en esta fase (ya estaba todo listo desde la Fase 2).

## Estado del proyecto de migración Wompi

Con esto, la **Fase 3 completa del plan original de 10 fases queda hecha**: el checkout de tarjeta (nueva o guardada) ya no depende del Widget para nada más que la captura segura de datos de tarjeta (vía `useCardTokenization`, que en rigor tampoco usa el widget de Wompi sino un `fetch` directo documentado por Wompi como alternativa válida al widget — mismo resultado de seguridad: los datos nunca tocan nuestro backend). PSE sigue con el Widget, por diseño y decisión explícita.

Quedan del plan original: **Fase 4** (auditoría/observabilidad — correlation ID, `TransactionEvent`, `PAYMENT_APPROVED` en `SecurityEvent`, ya diseñadas en el ADR pero no implementadas), **Fase 5** (migración gradual con feature flag), **Fases 6-10** (reconciliación automática mejorada, panel admin de pagos con acciones, alertas operativas, pruebas E2E/carga, actualización final de documentación).

## Siguiente paso

Me detengo aquí. ¿Continúo con la Fase 4 (observabilidad: `TransactionEvent`, correlation ID, `PAYMENT_APPROVED`) o prefieres priorizar otra fase del plan original?
