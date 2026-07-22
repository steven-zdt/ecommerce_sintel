# Fase 3a — Tokenización automática de tarjetas (frontend, completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md` §4, ajustado tras inspección real de `TokenizedCard`.
**Decisión del usuario:** una tarjeta nueva usada en cualquier flujo **siempre se guarda** automáticamente (sin checkbox opcional).

## Ajuste de diseño encontrado antes de implementar

El ADR (Fase 1) asumía que se necesitaría `payment_source_id` (`POST /payment_sources`) para tarjetas guardadas. Al inspeccionar el modelo real `TokenizedCard` (`payment/models.py`), se confirmó que **ya guarda un `token_id` reutilizable directamente** — este proyecto nunca necesitó el concepto de `payment_source_id`. Consecuencia: **no hizo falta ningún endpoint backend nuevo** — `POST payment/cards/` (`TokenizedCardViewSet.create`, ya existente y sin cambios) ya acepta exactamente los campos que la respuesta de tokenización de Wompi provee. El trabajo real de esta fase fue enteramente de frontend: automatizar lo que hoy el usuario hacía a mano (pegar el token).

## Qué se hizo

1. **`frontend/.env.development` y `frontend/.env.production`** — nueva variable `VITE_WOMPI_PUBLIC_KEY` (misma llave pública que el backend ya usa — segura de exponer en el bundle por diseño, es literalmente para eso que existen las llaves públicas).
2. **`frontend/src/composables/useCardTokenization.js`** (nuevo) — `tokenizeCard()` hace un `fetch()` **directo desde el navegador hacia `https://api.wompi.co/v1/tokens/cards`**, con la llave pública. Deliberadamente **no usa `useApi()`/axios** (nuestro cliente hacia nuestro propio backend) — los datos crudos de tarjeta nunca deben acercarse a nuestro servidor, requisito explícito de Wompi confirmado en su documentación oficial.
3. **`frontend/src/views/customer/account/CustomerCardsView.vue`** — el formulario "Agregar tarjeta" pasó de campos manuales (pegar token, número enmascarado a mano, marca por selector) a campos reales de tarjeta (número, MM, AA, CVC, titular). Al enviar: tokeniza vía Wompi → mapea la respuesta a los campos que `POST payment/cards/` ya esperaba → limpia el formulario **incondicionalmente** (éxito o error), para que datos crudos (número, CVC) nunca queden en memoria más tiempo del necesario.
4. **Bug real encontrado y corregido (no relacionado con la tokenización en sí):** `CustomerLayout.vue` nunca montaba `<ToastManager />` — **ningún toast de éxito/error se mostraba jamás en TODA la app de cliente** (`/mi-cuenta/*`, `/tienda`, checkout, etc.), solo en el panel admin (`AppShell.vue`). Es un bug de infraestructura preexistente que afecta a toda la superficie de cliente, no algo introducido por este cambio, pero bloqueaba verificar visualmente el propio flujo que se estaba construyendo — se corrigió agregando `<ToastManager />` a `CustomerLayout.vue` (mismo componente ya usado en el panel, sin cambios propios).

## Verificación realizada

Con Playwright contra el Vite dev server real, interceptando **únicamente** la llamada a `https://api.wompi.co/v1/tokens/cards` (respuesta simulada — ver "Pendiente" abajo) y dejando pasar sin interceptar la llamada real a nuestro propio backend (`POST /api/v1/payment/cards/`):

- El formulario nuevo se renderiza (5 campos reales, cero rastro del formulario manual viejo).
- El payload hacia Wompi es exactamente el esperado (`number` sin espacios, `exp_month`/`exp_year` como strings de 2 dígitos, `cvc`, `card_holder`, header `Authorization: Bearer pub_test_...`).
- El payload hacia **nuestro** backend (interceptado ahí sí de verdad, request real) mapea correctamente los campos y **nunca incluye el CVC**.
- La tarjeta se guarda de verdad (persistida en BD) y aparece en la lista.
- Ante un error de Wompi (422 simulado), nuestro backend **nunca se llama** — comportamiento correcto.
- El formulario se limpia por completo tras éxito y tras error.
- Tras el fix de `ToastManager`: toast de éxito ("Tarjeta guardada correctamente") y toast de error visibles de verdad en el DOM, en `/mi-cuenta/tarjetas` y confirmado sin regresiones en `/`, `/tienda`, `/servicios`.

## Pendiente — no se hizo sin autorización explícita

**No se hizo ninguna llamada real a la API de Wompi** (ni siquiera de sandbox) — todas las pruebas interceptaron `https://api.wompi.co/v1/tokens/cards` con una respuesta simulada. Esto significa que el **formato exacto de la request/response real de Wompi para tokenización no está 100% confirmado por una prueba real** (la documentación consultada durante la Fase 2 tenía al menos una inconsistencia aparente en un ejemplo de `exp_month`/`exp_year`). Antes de considerar este flujo listo para producción, se recomienda una prueba manual real contra el sandbox de Wompi (con un número de tarjeta de prueba publicado por Wompi) — es una acción aparte a autorizar explícitamente, igual que se decidió en la Fase 2 para las llamadas del backend.

## Siguiente paso

Con la tokenización automatizada y guardado de tarjetas funcionando, falta la **Fase 3b**: usar estas tarjetas guardadas en el checkout real (`CheckoutView.vue`) — listar tarjetas guardadas, permitir pagar con una de ellas (o agregar una nueva inline) llamando a `initialize/` con `card_token`, y saltarse el Widget completo de Wompi para el método de pago con tarjeta (PSE sigue igual, sin cambios, según lo ya confirmado).
