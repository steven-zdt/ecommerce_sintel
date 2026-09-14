# adk_poc — ADK-01, POC aislado de Google ADK

Ver `AUDITORIA/ADK_MIGRATION_AUDIT.md` (ADK-00) para el contexto completo de la
mision. Este directorio es **deliberadamente aislado** del stack productivo de
Sintel: venv propio (`.venv/`, no versionado), sin Dockerfile, sin entrada en
ningun `docker-compose*.yml`, no importado desde `ecommerce_sintel/` ni desde
`ai_engine/`. No se toco ningun contenedor ni imagen para crear esto.

## Como correrlo

```bash
cd adk_poc
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe -m pytest test_adk_poc.py -v -s
```

Requiere Ollama real alcanzable (por default `http://localhost:11434`, el
mismo contenedor `sintel_ollama` del stack de Sintel expone ese puerto al
host) con el modelo `llama3.1:8b` disponible (`ollama pull llama3.1:8b`).
Configurable via `ADK_POC_OLLAMA_URL`/`ADK_POC_OLLAMA_MODEL`.

## Resultado: 5/5 tests pasando, contra un Ollama real (sin mocks)

Verifica el checklist completo de ADK-01: instalacion, `LlmAgent`,
`InMemoryRunner`, `Workflow`, `FunctionTool`, session, event, HITL
(`require_confirmation`), modelo real via `LiteLlm`, ejecucion async.

## Hallazgo real mas importante: bug de tool-calling con ADK+LiteLlm+Ollama

**ADK 2.9.0 trae activada por default una feature experimental
(`JSON_SCHEMA_FOR_FUNC_DECL`) que rompe el tool-calling nativo cuando el
modelo es `LiteLlm(model="ollama_chat/...")`.** Con la feature activa, el
modelo NUNCA dispara una llamada de funcion real -- el LLM (`llama3.1:8b`,
que SI soporta tool-calling nativo, confirmado con una llamada `litellm.
completion()` cruda que aisla el problema a la capa de ADK, no a Ollama ni a
litellm) simplemente devuelve la declaracion de la tool como texto plano
(`'{"name": "lookup_order_status", "parameters": {...}}'`), y `Event.
get_function_calls()` queda vacio.

**Fix confirmado:**

```python
from google.adk.features._feature_registry import FeatureName, override_feature_enabled
override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)
```

**Debe ejecutarse ANTES de importar `google.adk.agents`/`google.adk.tools`/
`google.adk.models.lite_llm`** -- llamarlo despues de esos imports (aunque sea
antes de construir el `Agent` real) no tiene efecto, verificado
experimentalmente. El flag se resuelve en tiempo de import/definicion de
clase, no en cada invocacion.

**Impacto real para la migracion:** cualquier agente de Sintel que use
`LiteLlm` + Ollama (o, sin verificar todavia, LM Studio openai-compatible en
produccion) para tool-calling nativo necesita este override global al arrancar
el proceso, o las tools jamas se invocan de verdad -- el agente "alucina" una
respuesta de texto en vez de ejecutar la tool real. Este es exactamente el
tipo de hallazgo que ADK-01 existe para descubrir antes de comprometerse a la
migracion.

## Otros hallazgos de API real (vs. lo asumido en el plan original)

- `FunctionTool` no tiene un atributo publico `require_confirmation` -- el
  valor crudo vive en `_require_confirmation` (privado); la forma soportada de
  consultarlo en runtime es el metodo `check_require_confirmation(args,
  tool_context)`.
- `InMemoryRunner` requiere crear la sesion explicitamente antes de
  `run_async()`: `await runner.session_service.create_session(app_name=...,
  user_id=..., session_id=...)` -- no se auto-crea.
- Confirmado en vivo (no solo por docstring): `SequentialAgent`/
  `ParallelAgent`/`LoopAgent` siguen siendo importables y funcionales hoy
  (2.9.0), solo emiten el aviso de deprecacion -- no estan eliminadas
  todavia, pero no deben usarse como arquitectura de referencia para
  Sintel.

## Pendiente para ADK-02+ (no resuelto en este POC, fuera de su alcance)

- Verificar el mismo fix (`JSON_SCHEMA_FOR_FUNC_DECL=False`) contra LM Studio
  (el proveedor real de produccion, `openai-compatible`, no Ollama) -- no
  probado aqui.
- Confirmar si `Workflow` puede envolver un `LlmAgent` con sub-agentes
  anidados (la limitacion "Workflow cannot yet be used as an LlmAgent
  sub-agent" documentada en ADK-00 sigue sin probarse en la practica).
- Probar el flujo completo de `ToolContext.requestConfirmation()` (pausa +
  resume real), no solo que la API existe.
