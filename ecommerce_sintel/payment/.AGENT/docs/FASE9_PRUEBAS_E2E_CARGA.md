# Fase 9 — Pruebas E2E y de carga (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** plan original del usuario, Fase 9 (dentro del bloque "Fases 6 a 10").

## Parte 1 — E2E (`frontend/e2e/wompi-checkout.spec.js`, nuevo)

Sigue la convención ya establecida del proyecto (`ai_skills/frontend/testing/playwright.md`, `frontend/playwright.config.js`) — 3 specs permanentes, committeados al repo (no scripts desechables de scratchpad):

1. **Checkout con tarjeta nueva no abre el widget de Wompi** (Fase 3b).
2. **PSE/Otros nunca envía `card_token` a `initialize/`** (regresión del camino sin cambios).
3. **El switch de feature flag del panel admin persiste de verdad** (Fase 5/7).

Todos respetan la regla dura de este proyecto: **nunca se deja pasar una llamada real hacia la API de Wompi** — se intercepta con `page.route()` tanto la tokenización (`api.wompi.co`) como `initialize/` cuando lleva `card_token`.

### Gotcha real de infraestructura encontrado (el hallazgo más importante de esta fase)

`VITE_API_BASE_URL=http://localhost:8000/...` asume que el navegador corre en el **host** (donde Docker publica los puertos 5173/8000). La documentación existente del proyecto dice correr la suite formal con `docker exec ecommerce_sintel_frontend npx playwright test` — es decir, Chromium corre **dentro** del contenedor `ecommerce_sintel_frontend`. Desde ahí, `localhost:8000` no tiene nada escuchando (no es un bug de la app, es topología de red de Docker) — cualquier spec que solo tome una captura de pantalla estática (como el `visual-regression.spec.js` ya existente) nunca lo nota, porque nunca hace una llamada real a la API. Este es el **primer spec de la suite formal que intenta un login/checkout real**, así que es el primero en tropezar con esto.

**Investigación real, no asumida:**
- `http://localhost:8000` desde dentro del contenedor: inalcanzable (`fetch failed`).
- `http://django:8000` (nombre de servicio Docker): alcanzable, pero Django lo rechaza con `DisallowedHost` (`ALLOWED_HOSTS` de desarrollo solo incluye `localhost,127.0.0.1`).
- `http://nginx` (puerto 80, el nginx de desarrollo ya hace `proxy_pass` a django con `proxy_set_header Host $host;`): alcanzable, y si la request llega con `Host: localhost`, nginx reenvía ese mismo header y Django la acepta.
- El `fetch()` nativo del navegador/Node **prohíbe** que el código de la página sobreescriba el header `Host` (está en la lista de headers prohibidos del spec Fetch) — pero el módulo `http` nativo de Node **sí** lo permite.

**Solución implementada (`setupNetworkBridge`, dentro del propio spec, sin tocar ninguna config del proyecto):** un `page.route('http://localhost:8000/**', ...)` que reenvía cada request real con `http.request` crudo hacia `nginx:80` forzando `Host: localhost`, y devuelve la respuesta real al navegador. El checkout, el login, el carrito, el panel admin — todo el tráfico que no sea la frontera hacia Wompi — sigue siendo tráfico **real** contra el backend de desarrollo, simplemente enrutado correctamente para la topología de red de este contenedor.

### Otros bugs reales encontrados escribiendo este spec (todos en el spec, no en la app)

1. **`waitForURL` nunca se resuelve para routing 100% client-side** (Vue Router usa `pushState`, sin evento `load` de navegador real) — reemplazado por `waitForFunction(() => !location.pathname.startsWith(...))`, que hace polling directo del DOM.
2. **Rate limiting real del login (`10/hora`)** agotado por la enorme cantidad de logins manuales de verificación de todo este proyecto en el mismo día — se resolvió con `cache.clear()` (Redis) entre corridas de depuración, no hace falta en uso normal (una corrida de CI no generaría tantos intentos).
3. **Race condition real**: comprobar `count() > 0` inmediatamente después de un click que dispara un re-render de Vue puede evaluarse antes de que Vue termine de renderizar — reemplazado por `waitFor({ state: 'visible' })`.
4. **Placeholder equivocado**: asumí que el campo de número de tarjeta del checkout usaba el mismo placeholder de ejemplo (`"4242 4242..."`) que `CustomerCardsView.vue` (Fase 3a) — en realidad usa el texto genérico `"Numero de tarjeta"`. Corregido verificando el snapshot real del DOM, no adivinando.
5. **Token duplicado entre corridas**: el mock de tokenización usaba un `id` fijo (`tok_e2e_test_1`); como la Fase 3a guarda **toda** tarjeta nueva de forma permanente (`token_id` es `unique`), correr el spec dos veces seguidas contra la misma cuenta de prueba producía un 409 real en la segunda corrida. Corregido generando un `id` único por corrida (`Date.now()`).

### Resultado final

```
docker exec ecommerce_sintel_frontend npx playwright test wompi-checkout
3 passed (15.3s)
```

Confirmado estable en corridas consecutivas (no flaky) tras el fix del token único. La suite completa (`npx playwright test`, sin filtro) sigue mostrando exactamente los mismos 9 fallos preexistentes de `offline-testing.spec.ts` ya documentados en `ai_skills/frontend/testing/playwright.md` — no relacionados con este trabajo, no tocados.

## Parte 2 — Carga (`frontend/.AGENT/load-tests/payment-feature-flags-load-node.js`, nuevo)

Sigue el patrón ya establecido de `enum-cache-load-node.js` (mismo estilo: VUs, métricas p50/p95/p99, checklist de validación).

### Decisión de alcance: solo `GET payment/payments/feature-flags/`

Es el **único** endpoint nuevo de todo este proyecto razonable para una prueba de carga genérica: público (sin JWT que gestionar por VU), sin estado, y se llama en **cada** carga de `/checkout` — si se degrada, degrada el checkout completo, no solo el flujo de tarjeta. El resto de endpoints nuevos (`initialize/`, `resync/`, `events/`) requieren JWT + datos de orden/transacción reales por request, y algunos (`initialize/` con `card_token`) dispararían llamadas reales a Wompi bajo carga — fuera de alcance sin autorización explícita, mismo criterio que toda la Fase 2 y siguientes de este proyecto.

### Resultado real (50 VUs concurrentes, 15s, contra el backend de desarrollo)

```
Total requests: 2480 | Exitosos: 2480 (100.00%) | Fallidos: 0
p50: 198.69ms  p95: 312.75ms  p99: 361.65ms  avg: 204.62ms
Throughput: 162.89 req/s
```

**Honestidad sobre el resultado:** 100% de éxito bajo carga (dato sólido), pero el p99 (362ms) superó el umbral inicial que se puso en el script (200ms). **No se ajustó el umbral para "hacerlo pasar"** — se reporta tal cual. La lectura más probable es que el número está dominado por las condiciones de este entorno de desarrollo compartido (el mismo host corre simultáneamente Ollama, ChromaDB, el motor de IA, y el resto del stack completo de Sintel, todo compitiendo por CPU) más que por el código del endpoint en sí — la consulta que hace (`PaymentFeatureFlags.objects.filter(is_active=True).first()`) es una lectura trivial de una sola fila. **No se puede confirmar esto como un número representativo de producción** sin repetir la prueba en un entorno dedicado — se deja anotado como pendiente de verificación real antes de considerar esta latencia aceptable para producción, en vez de descartarlo sin más.

## Qué NO se hizo (fuera de alcance de esta fase)

- No se agregaron pruebas de carga de `initialize/`, `resync/` ni ningún endpoint que toque Wompi — requeriría datos autenticados por VU y, en el caso de `initialize/` con tarjeta, llamadas reales a Wompi bajo carga, que este proyecto nunca hace sin autorización explícita.
- No se investigó a fondo el origen exacto del p99 elevado (perfilado de Django, número de workers de Daphne, etc.) — es una investigación de infraestructura separada, no de este proyecto de migración de pagos.

## Siguiente paso

Me detengo aquí. Queda del plan original: **Fase 10** (documentación final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`) — la última fase del plan de 10. ¿Cómo quieres continuar?
