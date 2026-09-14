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

## Pendiente para ADK-02+ (no resuelto en el POC de ADK-01, resuelto abajo)

- Verificar el mismo fix (`JSON_SCHEMA_FOR_FUNC_DECL=False`) contra LM Studio
  (el proveedor real de produccion, `openai-compatible`, no Ollama) -- no
  probado aqui.
- Confirmar si `Workflow` puede envolver un `LlmAgent` con sub-agentes
  anidados (la limitacion "Workflow cannot yet be used as an LlmAgent
  sub-agent" documentada en ADK-00 sigue sin probarse en la practica).
  **Resuelto en ADK-03 abajo -- no aplica al patron de routing de Sintel.**

---

# ADK-02 — SINTEL Tool Adapter (completado)

`sintel_adapter.py`: `adapt_sintel_tool(registered_tool) -> FunctionTool`.
Toma una `RegisteredTool` REAL de `ai_engine.tools.registry` (ToolMetadata +
funcion async `(ctx, **args) -> dict`) y produce una `FunctionTool` de ADK
real, **sin reescribir la logica de la tool** -- el adapter importa
`ai_engine/tools/*` via `sys.path` (no copia ni un archivo) y llama a la
funcion original tal cual.

Mapeo: `ToolMetadata.name/description` -> nombre/descripcion de la
`FunctionTool`; `ToolMetadata.requires_confirmation` -> `FunctionTool(...,
require_confirmation=...)` (mapeo 1:1 directo); `ToolContext(user, token)` de
Sintel se reconstruye desde `tool_context.state` de ADK (sembrado en la
sesion -- la resolucion de identidad real completa es responsabilidad de
ADK-03, aqui solo se demuestra el mecanismo de paso de contexto).

## Verificado end-to-end, con Tools REALES de ai_engine (sin mocks salvo el bridge HTTP)

**`test_sintel_adapter.py`** -- adapta `OrderStatusTool` (real,
`ai_engine/tools/orders_tools.py`, sin `requires_confirmation`). Flujo
completo: Ollama decide llamar la tool -> ADK invoca el wrapper del adapter
-> el wrapper reconstruye `ToolContext(token="fake-jwt-para-el-poc", ...)`
-> llama a `orders_tools.order_status_tool()` REAL -> esta llama a
`django_internal_get()` (unico punto mockeado, mismo criterio que la propia
suite de `ai_engine`) -> el resultado mockeado vuelve al LLM -> respuesta
final coherente con los datos reales devueltos. Se verifico explicitamente
que `registered.func is orders_tools.order_status_tool` (la funcion
invocada es la real, no una copia) y que el token de la sesion de ADK llego
intacto hasta la llamada HTTP simulada.

**`test_sintel_adapter_hitl.py`** -- adapta `RequestKycUpgradeTool` (real,
`side_effects=True`, `requires_confirmation=True`,
`ai_engine/tools/kyc_tools.py` -- una tool de ESCRITURA real). Confirma que
`require_confirmation=True` **efectivamente pausa la ejecucion**: el LLM
decide llamar la tool, ADK emite un evento con
`requested_tool_confirmations` (`ToolConfirmation(hint="Please approve or
reject...", confirmed=False)`) **y la escritura real
(`django_internal_post`) nunca se ejecuta** -- verificado con
`mock_write.assert_not_called()`-equivalente. Este es el mismo principio
estructural que `ai_editor.repository.promote_to_workspace()` ya exige del
lado Sintel (ver `AUDITORIA/ADK_MIGRATION_AUDIT.md` seccion 4) -- ADK puede
sostener ese mismo gate para tools normales de `ai_engine`.

**Gotcha de mocking real encontrado (no un bug del adapter):** parchear
`tools.http_bridge.django_internal_get` NO tiene efecto -- `orders_tools.py`
hace `from tools.http_bridge import django_internal_get`, asi que tiene su
propia referencia local vinculada en tiempo de import. Hay que parchear
donde se USA (`tools.orders_tools.django_internal_get`), no donde se define.
Aplica igual a cualquier mock futuro de las tools reales de `ai_engine`.

**Nota de riesgo:** el mecanismo de confirmacion completo
(`FeatureName.TOOL_CONFIRMATION`) tambien esta marcado **EXPERIMENTAL** en
ADK 2.9.0 (warning propio del framework) -- igual que `JSON_SCHEMA_FOR_FUNC_DECL`.
No asumir estabilidad de API entre versiones de ADK para este mecanismo.

## Pendiente para ADK-03+

- Resolucion de identidad real (que llena `tool_context.state` con el JWT
  real del usuario autenticado) -- aqui se sembro a mano en
  `create_session(state=...)`, en el Root Workflow real vendria de Django/
  WebSocket/WhatsApp. **Resuelto en ADK-03 abajo.**
- Probar el flujo de RESUME tras una confirmacion real (enviar la
  `ToolConfirmation(confirmed=True)` de vuelta y confirmar que
  `django_internal_post` SI se ejecuta entonces) -- este POC solo probo la
  mitad "pausa", no el resume.
- Generalizar el adapter a tools con `**kwargs` reales (ej.
  `CreateRentalRequestTool`, que ya usa `**kwargs` del lado Sintel segun
  `tools/registry.py::invoke()`) -- el adapter actual asume que
  `inspect.signature(tool.func)` da parametros concretos, no verificado
  contra una tool `**kwargs`.
- Verificar el mismo fix (`JSON_SCHEMA_FOR_FUNC_DECL=False`) contra LM Studio
  (el proveedor real de produccion, `openai-compatible`, no Ollama) -- no
  probado aqui.
- Confirmar si `Workflow` puede envolver un `LlmAgent` con sub-agentes
  anidados (la limitacion "Workflow cannot yet be used as an LlmAgent
  sub-agent" documentada en ADK-00 sigue sin probarse en la practica).
  **Resuelto en ADK-03 abajo -- no aplica al patron de routing de Sintel.**

---

# ADK-03 — Root Workflow (completado)

**Hallazgo central: la limitacion "`Workflow` no puede usarse aun como
sub-agente de `LlmAgent`" NO aplica al patron Root -> Support/Sales/
Operations.** Ese patron usa `BaseAgent.sub_agents: list[BaseAgent]` +
`LlmAgent.disallow_transfer_to_parent/disallow_transfer_to_peers` --
delegacion LLM-driven (`transfer_to_agent`) real, no deprecada, y separada
del motor de grafo `Workflow`.

**Verificado en vivo (`test_root_workflow.py`, 2/2, Ollama real, sin mocks
de LLM):** un Root Agent con `sub_agents=[support_agent, sales_agent]`
enruta la pregunta de pedidos a `support_agent` y la de catalogo a
`sales_agent`, sin cruces -- routing real decidido por el LLM.

**Hallazgo arquitectonico: el "AIContext" que el plan proponia crear como
pieza nueva ya existe, con otro nombre.** `ai_engine/auth.py` ya resuelve
identidad completa: `decode_django_jwt()` (JWT HS256 local) +
`fetch_user_context()` (reenvia el token a Django
`/internal/ai-context/`, unica autoridad real de perfil).
`sintel_root_workflow.py::resolve_identity()` reutiliza ese boundary tal
cual, no lo duplica.

**Sesion:** el patron real de `action_graph.run_action_chat` (`thread_id =
f"{user_id}:{conversation_id}"`) se replico 1:1 como `session_id` de ADK
(`build_session_id()`). Verificado que un segundo turno con el mismo
`conversation_id` reusa la misma sesion (no se recrea).

`sintel_root_workflow.py::run_sintel_turn()` -- alcance deliberado: solo
`support_agent` (envolviendo `OrderStatusTool` + `KycStatusTool`, ya
probadas en ADK-02). El resto de las ~28 tools reales de `ai_engine`
(10 dominios) y los agentes Sales/Operations/Engineering quedan para
ADK-04/ADK-05 -- no se inventa logica de dominio antes de tener tools
reales migradas.

**Verificado end-to-end (`test_sintel_root_workflow.py`, 3/3):** JWT real
firmado con PyJWT (sin mock) -> `decode_django_jwt` real -> Django
mockeado (`fetch_user_context`) -> Root Agent enruta a `support_agent` ->
`OrderStatusTool` real ejecuta (bridge HTTP mockeado) -> respuesta final
coherente. Test negativo: JWT con firma invalida falla cerrado
(`IdentityResolutionError`), nunca degrada a turno anonimo.

## Pendiente para ADK-04+

- El resto del contrato de `ChatResponse` (`intent`, `tool_calls`,
  `needs_confirmation`, `metrics`) -- este runtime solo cubre identidad/
  sesion/routing/eventos, no reemplaza `/chat` todavia (eso es ADK-10,
  dual run).
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Generalizar el adapter a tools `**kwargs` reales (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio, no solo
  Ollama (heredado de ADK-01).
- Migrar el resto del registro real de tools (~28, 10 dominios) y separar
  Sales/Operations/Engineering como sub-agentes reales.
