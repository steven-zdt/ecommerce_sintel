# Fase 5 — Migración gradual / feature flag (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** plan original del usuario, Fase 5: *"Permitir convivir temporalmente Widget/API personalizada. Habilitar un feature flag para cambiar entre ambos sin desplegar código nuevo."*

## Qué se hizo

### 1. `PaymentFeatureFlags` (modelo nuevo, singleton)

`payment/models.py`, migración `payment/migrations/0010_paymentfeatureflags.py`. Sigue el mismo patrón singleton ya usado en `organization`/`core` en este proyecto (guardar un registro con `is_active=True` desactiva cualquier otro) — **duplicado localmente, no importado entre apps**, siguiendo la convención ya existente del proyecto de no crear dependencias cruzadas para un mixin de 3 líneas.

- Campo único por ahora: `card_api_flow_enabled` (default `True`).
- `PaymentFeatureFlags.get_active()` — selector de conveniencia que crea el singleton por defecto si no existe ninguno (self-healing, sin necesidad de migración de datos).
- **Editable desde `/admin/` de Django** (`PaymentFeatureFlagsAdmin`, registrado en `payment/admin.py`) — un admin puede togglear esto sin ningún deploy.

### 2. Kill-switch real, no solo cosmético

- **Backend:** `GET /api/v1/payment/payments/feature-flags/` (público, `AllowAny` — se consulta antes de que el usuario inicie sesión/pague) expone `{"card_api_flow_enabled": bool}`.
- **`WompiPaymentViewSet.initialize()`** ahora **rechaza con 403** cualquier request con `card_token`/`payment_source_id` si el flag está desactivado — esto es deliberado: el flag no es solo una señal para que el frontend oculte un botón, es una verificación real del lado del servidor. Si alguien llamara a `initialize/` directamente con `card_token` (saltándose la UI), igual sería bloqueado.
- **Frontend (`CheckoutView.vue`):** consulta el flag al montar (`fetchFeatureFlags()`). Si está desactivado, el sub-selector "Tarjeta"/"PSE / Otros" ni siquiera aparece — el checkout se comporta como si esta fase nunca hubiera existido, con el Widget completo como único camino (que ya incluye tarjeta). Falla también "cerrado, no abierto": si la llamada al endpoint de flags falla por cualquier motivo (red, endpoint caído), se asume desactivado — se prefiere el camino más antiguo y probado ante cualquier duda.

### 3. Resultado: "convivencia temporal" ya lograda por diseño, no por casualidad

El Widget completo (camino "PSE / Otros") **nunca se eliminó** — sigue siendo un camino de pago con tarjeta totalmente funcional y accesible incluso hoy, sin tocar el flag. El flag no activa/desactiva la existencia del Widget (que siempre está ahí para PSE), sino la **visibilidad y disponibilidad del nuevo flujo backend-directo**. Esto significa que la "reversión instantánea sin deploy" pedida por el plan ya funciona con lo construido en las Fases 2-4, y esta fase solo necesitaba agregar el interruptor.

## Verificación realizada

6 tests nuevos (`payment/tests.py::PaymentFeatureFlagsTestCase`): creación automática del singleton por defecto (habilitado), que guardar un nuevo registro activo desactiva el anterior, que el endpoint público refleja el estado real (habilitado y deshabilitado), que `initialize/` con `card_token` es **bloqueado con 403** cuando el flag está desactivado, y que el camino **sin** `card_token` (PSE/Otros) **nunca se ve afectado** por el estado del flag.

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.PaymentFeatureFlagsTestCase` → **6/6 OK**.
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **50/50 OK** (44 anteriores + 6 nuevos).

## Incidente operativo durante esta sesión (no relacionado con el código de esta fase)

Mientras se trabajaba en esta fase, se reportó y resolvió un incidente real de producción: `sintel_prod_nginx` estaba en crash-loop porque el contenedor había sido creado antes de que se agregara el mount de `nginx-common.conf` (Fase 2 del proyecto de aislamiento de dominio del panel) a `docker-compose.prod.yml`. Se resolvió con `docker compose -f docker-compose.prod.yml --env-file .env.production up -d nginx` (recrea el contenedor con la config actual — un simple restart no alcanza). Verificado con `nginx -t` real y un `GET /api/v1/health/` real a través de nginx→Django. Confirmado que Django en producción usa una imagen con código horneado (sin bind mount de fuente) — la recreación del contenedor de Django (efecto colateral de `depends_on`) no aplicó ninguna migración nueva de esta sesión a la base de datos de producción. Detalle completo en la memoria de la sesión (`feedback_docker_compose_recreate_vs_restart`).

Por separado, el stack de **desarrollo** completo se cayó (`Exited 137`, probablemente un reinicio de Docker Desktop/WSL2 no relacionado) y se volvió a levantar con `docker compose up -d` sin pérdida de datos ni cambios de código.

## Estado del proyecto de migración Wompi

Con esto, la **Fase 5 del plan original de 10 fases queda completa**. Quedan: **Fases 6-10** — reconciliación automática mejorada (aprovechando `TransactionEvent`/`correlation_id` de la Fase 4), panel administrativo de pagos con acciones reales (hoy es de solo lectura, ver Fase 0), alertas operativas, pruebas E2E/de carga, y actualización final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`.

## Siguiente paso

Me detengo aquí. ¿Continúo con las Fases 6-10, o prefieres priorizar algo puntual de esa lista?
