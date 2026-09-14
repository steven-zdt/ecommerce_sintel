# FASE 3 -- Dashboard admin API (CRUD + test connection + discovery)

**Fecha:** 2026-08-13. Ver `FASE1_MODELOS.md`/`FASE2_INTERNAL_API.md` para el dominio
base y el endpoint interno.

## Cambios

- `dashboard/services/admin_orchestrators.py`: `AIProviderAdminOrchestrator` (mismo
  patron -- static methods, imports diferidos -- que `SecurityAdminOrchestrator`/
  `NotificationAdminOrchestrator`). Delega 100% en `ai_provider.services.selectors/
  commands`.
- `dashboard/api/ai_provider_serializers.py` (nuevo, split de `serializers.py` --
  mismo criterio que `services_catalog_views.py`): `AIProviderSerializer` (lectura,
  **nunca** incluye `api_key`, solo `has_api_key`), `AIProviderInputSerializer`
  (escritura, `api_key` write-only opcional), `AIModelSerializer`/
  `AIModelInputSerializer`, `AIChannelConfigSerializer`.
- `dashboard/api/ai_provider_views.py` (nuevo, split de `views.py`):
  `AdminAIProviderViewSet` (`/api/v1/dashboard/ai-providers/`, `lookup_field='uuid'`)
  con CRUD completo + `POST .../test-connection/` + `GET .../discover-models/` +
  `POST .../models/` (agregar modelo) + `DELETE .../models/<uuid>/`.
  `AdminAIChannelConfigViewSet` (`/api/v1/dashboard/ai-channel-config/`) con
  `POST set-primary/` y `POST set-fallback-chain/`.
- `ai_provider/services/connection_probe.py` (nuevo): `probe_provider()` (ping real
  -- Ollama `GET /api/tags`, openai-compatible `GET /models`, anthropic
  `GET /v1/models` -- nunca una generacion completa) y `discover_provider_models()`
  (mismo mecanismo, parsea el catalogo real del proveedor; anthropic no soporta
  descubrimiento dinamico, devuelve `[]`).
- `dashboard/api/urls.py`: `router.register('ai-providers', ...)` /
  `router.register('ai-channel-config', ...)`.

## Permisos

`ADMIN_PERMISSIONS` (= `[IsAuthenticated, IsAdminUser]`, mismo import que el resto de
`dashboard/api/views.py`) -- consistente con el resto del panel admin.

## Tests

`docker exec ecommerce_sintel_django python manage.py test ai_provider -v 1` --
**24/24 PASS** (17 de FASE 1-2 + 7 nuevos): permisos (401 anonimo / 403 no-admin),
`api_key` nunca sale en la respuesta de creacion, update con campo `api_key` ausente
no borra la key existente, delete soft desaparece del list, `test-connection` real
(llamada de red real a `sintel_ollama:11434` desde el test -- el motor esta arriba en
este entorno, se verifica que el resultado se persiste sea cual sea, sin acoplar el
test a que el ping siempre tenga exito), agregar modelo + marcarlo primario via API,
cadena de fallback preserva el orden.

**Bug de test autocorregido (no de produccion):** `set-fallback-chain` con una lista
de UUIDs fallaba con un `ValidationError` real (`"d" no es un UUID valido`) -- causa:
el `APIClient` de DRF usa `multipart` por defecto, que no serializa una lista Python
bajo una sola clave correctamente (la aplano a un string y el codigo la itero
caracter por caracter). Se corrigio pasando `format='json'` explicito en el test --
el endpoint real siempre se probo/pensó para recibir JSON (`request.data.get(...)`),
el bug era enteramente del arnes de pruebas, no del endpoint.

## Siguiente fase

FASE 4 -- AI Engine: loader dinamico. `ai_engine/llm_factory.py::get_llm()` hoy
construye el LLM UNA sola vez en el `lifespan` de FastAPI (`main.py`). Se agregara una
funcion que consulte `GET /api/v1/internal/ai/provider-config/` (FASE 2) y, si la
cadena no esta vacia, la use para reconstruir el modelo -- si esta vacia o la llamada
falla, cae a `LOCAL_MODEL_CHAIN` (bootstrap/emergencia, sin cambios). Se necesita
decidir el mecanismo de refresco (poll periodico vs. endpoint `/refresh-llm` explicito
-- el proyecto ya tiene precedente de un endpoint de refresh manual, `POST /refresh`,
para la base de conocimiento).
