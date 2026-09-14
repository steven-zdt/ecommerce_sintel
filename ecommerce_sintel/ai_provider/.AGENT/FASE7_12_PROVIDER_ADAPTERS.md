# FASE 7-12 -- Provider Adapters, Connection Test, Model Discovery

**Fecha:** 2026-08-13. Plan "AI Provider Runtime". Ver `AI_PROVIDER_RUNTIME_AUDIT.md`
(FASE 0) y `FASE1_MODELOS.md` a `FASE5_FRONTEND.md` (campaña previa, FASE 1-6 de
"CONFIGURACION DINAMICA DE MODELOS LOCALES").

## Cambios

- `ai_provider/services/providers/base.py`: `BaseProviderAdapter` (ABC) --
  `test_connection()`/`list_models()`/`validate_model()`/`build_runtime_config()`/
  `get_provider_health()`. `ConnectionTestResult` (dataclass) con la forma exacta
  de FASE 11: `success, provider, base_url, model, latency_ms, http_status,
  error_code, error_message_safe, timestamp`. Codigos de error categorizados:
  `DNS, CONNECTION_REFUSED, TIMEOUT, UNAUTHORIZED, NOT_FOUND, MODEL_NOT_FOUND,
  INVALID_RESPONSE, TOOL_CALLING_UNSUPPORTED, UNKNOWN, SUCCESS`.
- `providers/ollama.py`: `OllamaAdapter`. `_classify_connection_error()` distingue
  DNS vs CONNECTION_REFUSED inspeccionando el texto de la causa real de
  `requests.exceptions.ConnectionError` (ambos casos llegan como la misma
  excepcion de `requests`, se diferencian por el mensaje envuelto de urllib3).
- `providers/openai_compatible.py`: `OpenAICompatibleAdapter` -- cubre LM Studio/
  vLLM/llama.cpp/LocalAI/OpenAI/DeepSeek sin una clase por motor (mismo criterio
  que ya tenia `llm_factory.py::_build_model()`). 401/403 -> `UNAUTHORIZED`.
- `providers/anthropic.py`: `AnthropicAdapter` -- header `x-api-key` (nunca
  `Authorization: Bearer`, protocolo distinto). `list_models()` siempre `[]`
  (sin catalogo dinamico publico estable) -- `validate_model()` acepta cualquier
  identifier no vacio, el error real (si no existe) aparece en el primer `/chat`
  real, no aqui (documentado explicitamente, no fabricado como "validado").
- `providers/__init__.py`: `get_adapter(provider) -> BaseProviderAdapter`
  (factory por `provider.kind`).
- `services/connection_test.py` (FASE 11): `AIProviderConnectionTestService.test()`
  -- reemplaza `connection_probe.py::probe_provider()` de la campaña previa.
- `services/model_discovery.py` (FASE 12): `discover_models()` -- reemplaza
  `connection_probe.py::discover_provider_models()`.
- `connection_probe.py` **eliminado** (0 referencias restantes, confirmado con
  grep antes de borrar) -- `dashboard/services/admin_orchestrators.py::
  test_connection()`/`discover_models()` ahora llaman los modulos nuevos.
- `admin.py`: refleja los campos nuevos (`is_default`, `temperature`, `max_tokens`,
  `slug` readonly, `enabled` en `AIChannelConfig`).

## Tests

`ai_provider/tests_providers.py` (nuevo, 15 tests) + suite completo de
`ai_provider`: **47/47 PASS**, incluye llamadas REALES (no mockeadas) contra
`sintel_ollama` (`test_connection_success`, `test_discover_models_delegates_...`
-- confirma `llama3.1:8b` real en el catalogo) y llamadas mockeadas para casos
que no se pueden provocar de forma real de forma barata (timeout, 401, DNS).

## Decision explicita (no fabricada como "resuelta")

`TOOL_CALLING_UNSUPPORTED` (codigo de error) esta definido pero **no se evalua
todavia en `test_connection()`** -- verificar `.bind_tools()` real requeriria una
llamada de generacion completa (costo/latencia real, especialmente en
proveedores de pago), y el plan maestro separa esto en su propia fase (FASE 27
"Tool Calling", distinta de FASE 11 "Connection Test"). Se implementara como
metodo separado (`test_tool_calling()`), invocado explicitamente, no como parte
del boton "Probar conexion" -- evita una regresion de costo/latencia silenciosa
en la accion mas usada del panel.

## Siguiente fase

FASE 13-14 -- Dashboard Orchestrator + rutas API ya existen desde la campaña
previa (`AIProviderAdminOrchestrator`, `/api/v1/dashboard/ai-providers/`) --
namespace distinto al que pide el plan actual (`/api/v1/dashboard/support/ai/...`,
anidado). Decision ya tomada en FASE 0: mantener el namespace plano existente
(probado, consumido por el frontend real) en vez de renombrar sin necesidad
funcional.
