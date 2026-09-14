# FASE 2 -- Internal API (AI Engine lee config via HTTP)

**Fecha:** 2026-08-13. Ver `FASE1_MODELOS.md` para el dominio base.

## Cambio

`GET /api/v1/internal/ai/provider-config/?channel=support_chat` (nuevo, registrado en
`ecommerce/internal_ai_urls.py`) -- `AiProviderConfigView`
(`ai_provider/api/internal_ai.py`). Devuelve la cadena resuelta primary+fallback
(`AIChannelConfigSelector.get_resolved_chain()`, FASE 1) en el formato que FASE 4
consumira para reconstruir el equivalente de `LOCAL_MODEL_CHAIN`.

Cadena vacia (`{"channel": "...", "chain": []}`) es la señal explicita de "no hay
config real todavia -> el motor debe caer a LOCAL_MODEL_CHAIN" -- no un error.

## Decision de permisos (distinta al resto de /internal/ai/*)

Los demas endpoints en `ecommerce/internal_ai_urls.py` actuan EN NOMBRE de un usuario
(forwardean su JWT, `IsAdminUser`/`IsAuthenticatedActiveUser`). Este es config de
infraestructura del propio motor, sin turno de chat ni usuario de por medio -- usa
`AllowAny` explicito, documentado en el docstring del modulo, consistente con la
decision YA establecida en este proyecto de que el aislamiento real de `/internal/*`
es de RED (confirmado en FASE 0: nginx bloquea `/api/v1/internal/*` en produccion,
`nginx-common.conf`; en dev depende de la topologia Docker), no de permisos Django.

**La vista SI devuelve `api_key` descifrada** -- necesaria para que AI Engine
construya el cliente LLM real, mismo nivel de confianza que ya existia (la key vivia
en texto plano en `.env`, ahora vive cifrada en Postgres y se descifra solo para este
consumidor interno sancionado). La regla del plan maestro de nunca exponer la API key
aplica al FRONTEND (FASE 3: esa vista solo expone `has_api_key`, nunca el valor real).

**Bug real autocorregido antes de commitear:** la primera version de este archivo
tenia una contradiccion -- el docstring afirmaba "nunca se serializa api_key en texto
plano" mientras el codigo SI la devolvia. Corregido antes de continuar: docstring
ahora explica correctamente por que la vista debe devolverla.

## Tests

`docker exec ecommerce_sintel_django python manage.py test ai_provider -v 1` --
**17/17 PASS** (13 de FASE 1 + 4 nuevos: cadena vacia, forma de la respuesta, api_key
descifrada al consumidor interno, default de canal). `APIClient` SIN autenticar
(confirma AllowAny real, no solo declarado).

## Validacion en vivo

Con el servidor real corriendo (`DEV_RELOAD` recargo el archivo nuevo automaticamente,
sin restart manual):
```
GET /api/v1/internal/ai/provider-config/?channel=support_chat
-> {"channel":"support_chat","chain":[]}                              (antes de configurar nada)
-> {"channel":"support_chat","chain":[{"model_id":"llama3.1:8b", ...}]} (tras crear un
   AIProvider real apuntando a sintel_ollama:11434 + AIModel + set_primary)
```
Datos de prueba reales creados y dejados en la BD dev (utiles para FASE 4): provider
"Ollama Docker (real)" (`kind=ollama-nativo`, `base_url=http://sintel_ollama:11434`),
modelo `llama3.1:8b`, configurado como primario de `support_chat`.

## Siguiente fase

FASE 3 -- Dashboard admin API: ViewSets CRUD (`/api/v1/dashboard/ai-providers/`,
`IsAdminUser`), accion "probar conexion" (llamada real al proveedor, guarda resultado
via `AIProviderCommands.record_test_result`), descubrimiento de modelos (ej. `GET
/api/tags` de Ollama).
