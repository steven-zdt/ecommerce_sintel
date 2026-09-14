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
  **Resuelto en ADK-04 abajo.**

---

# ADK-04 — Support Agents, los 9 perfiles reales (completado)

**Decision de arquitectura (confirmada por el usuario tras una pregunta
explicita, ver AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 8ter):** el routing
real de `ai_engine` es 100% deterministico
(`action_graph.detect_business_intents` + `AgentRegistry.route/
apply_escalation`, regex-based, con reglas de seguridad como "queja SIEMPRE
escala a SupportAgent"). Usar `sub_agents`/transfer LLM-driven (ADK-03) como
router de produccion violaria "ADK ORQUESTA. SINTEL EJECUTA Y CONTROLA" --
**el router deterministico de Sintel decide, ADK solo ejecuta.** El
mecanismo `sub_agents` queda validado como capacidad real (`test_root_workflow.py`,
conservado), sin uso en el runtime de produccion.

`sintel_root_workflow.py` (reescrito):
- `resolve_turn_agent(message)` reutiliza tal cual las funciones reales de
  `action_graph.py`/`agents.AgentRegistry` -- no las copia.
- `get_domain_agent(profile_name)` construye un `LlmAgent` real por cada uno
  de los **9 perfiles reales** (`AccountAgent`, `AdminAgent`,
  `MarketingAgent`, `OrderAgent`, `PaymentAgent`, `RentalAgent`,
  `SalesAgent`, `ServiceAgent`, `SupportAgent`), con sus tools reales
  adaptadas (ADK-02) y su objetivo/personalidad/tono real como instruccion.
- `Runner` explicito + `InMemorySessionService` compartido a nivel de
  modulo, en vez de `InMemoryRunner` -- **hallazgo real**: `InMemoryRunner`
  crea su PROPIO `InMemorySessionService` aislado por instancia (verificado
  leyendo el codigo fuente), lo que romperia la sesion si el agente activo
  cambia de un turno a otro (caso real, no hipotetico, dado el routing
  determinista).

**Bug real encontrado (no sintetico) construyendo los 9 agentes:**
`sintel_adapter.py` no soportaba tools con `**kwargs` real -- 5 tools reales
de `AdminAgent` (`CoreBannerUpdateTool`, `CoreBannerCreateTool`,
`CoreNavbarLinkUpdateTool`, `CoreNavbarLinkCreateTool`,
`CoreBrandSliderUpdateTool`) fallaban con `ValueError: wrong parameter
order`, y arreglado eso, exponian CERO campos opcionales al LLM (bug de
correctness silencioso). Fix: cuando la funcion real tiene `**kwargs`, el
adapter sintetiza parametros keyword-only desde `ToolMetadata.args_schema.
properties` -- la fuente REAL que ya declara esos campos. Ver
`test_sintel_adapter_kwargs.py` (2/2).

**Verificado:** los 9 perfiles construyen correctamente sus `LlmAgent` (33
instancias de tool adaptadas, con reuso real entre perfiles). 16/16 tests
pasando salvo el flake ya documentado de ADK-01 (variabilidad de muestreo
de `llama3.1:8b` local, reproducido 3/3 en aislado -- no una regresion).

## Pendiente para ADK-05+

- El resto del contrato de `ChatResponse` (`tool_calls`, `needs_confirmation`,
  `metrics`) -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio, y si es mas
  o menos confiable que Ollama dado el flake observado (heredado de ADK-01).
- Revisar que quede realmente pendiente de "migrar tools 1 a 1" -- ADK-04 ya
  adapto las 33 instancias de tools reales de los 9 perfiles.
  **Resuelto en ADK-05 abajo.**

---

# ADK-05 — migracion de tools 1 a 1, auditoria del registro completo (completado)

Alcance real: ADK-04 ya probaba que las 33 instancias de tool de los 9
perfiles construian sin excepciones -- eso no probaba que la superficie
expuesta al LLM fuera correcta, solo que no truena. ADK-05 audito el
**registro completo real (29 tools)** cruzando, para cada una, lo que el
wrapper expone contra `ToolMetadata.args_schema.properties`.

**Bug de seguridad real (no hipotetico), encontrado auditando
`OpenSupportTicketTool`:** su funcion real tiene un parametro real
`history: list | None = None` **deliberadamente ausente de `args_schema`**
-- lo inyecta el grafo (Human Handoff), "el LLM jamas lo controla" (comentario
real de `support_tools.py`). El adapter anterior (ADK-02/04) leia
`inspect.signature` directo para los parametros fijos, sin cruzarlos contra
`args_schema` -- eso habria expuesto `history` como campo rellenable por el
LLM, violando un boundary de seguridad ya deliberado del sistema real.

**Fix:** `args_schema.properties` pasa a ser la UNICA fuente autoritativa de
lo que el wrapper expone al LLM, nunca `inspect.signature` cruda. Un
parametro real ausente del schema no se expone; `real_func` usa su propio
default.

**Verificado exhaustivamente:** `test_adk05_tool_registry_audit.py` (31/31)
recorre las 29 tools reales una por una, sin excepciones adicionales mas
alla de `history`. `test_sintel_adapter_hidden_param.py` prueba end-to-end
con Ollama real: el LLM abre un ticket de soporte real y `history` nunca
llega al body HTTP real.

**Conclusion de alcance:** con este fix, las 29 tools reales quedan
adaptadas correcta y exhaustivamente -- "migrar tools 1 a 1" queda cubierto
por ADK-04+ADK-05 combinados, sin trabajo pendiente adicional en ese frente.
48/48 tests pasando.

## Pendiente para ADK-06+

- El resto del contrato de `ChatResponse` (`tool_calls`, `needs_confirmation`,
  `metrics`) -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).

---

# ADK-06 — RAG adapter (completado)

Regla dura: reusar `RetrievalService`/pgvector via `ai_knowledge`, nunca
reintroducir ChromaDB/FAISS. `sintel_rag_adapter.py` reutiliza tal cual
`ai_engine/retrievers.py::retrieve_knowledge_for_chat` -- la misma funcion
real que ya usa `action_graph.py::node_retrieve_knowledge` desde la
migracion ChromaDB->pgvector. Cero logica de retrieval nueva.

**Decision consistente con ADK-04:** retrieval NO es una Tool que el LLM
decide invocar -- es una rama determinista del grafo real
(`intent == "knowledge"`, clasificado por regex). El Root Workflow decide
SI hace retrieval (reusando el router ya determinista) y le INYECTA el
resultado al agente. Routing real: `AgentRegistry` asigna `"knowledge"` a
**SalesAgent** -- verificado en vivo.

**Gobernanza real replicada (Fase 17, hallazgo ya documentado en el codigo):**
sin chunks, se inyecta el marcador EXPLICITO "NINGUNO -- no se encontro
informacion verificada sobre este tema." -- el comentario real documenta el
incidente que lo motivo: sin el, el LLM alucino una respuesta (horario de
atencion) con un chunk irrelevante. `build_knowledge_context()` replica ese
marcador BIT a BIT.

**Mecanismo de inyeccion (API real de ADK):** `LlmAgent.instruction` acepta
un CALLABLE `(ReadonlyContext) -> str`, evaluado por turno. Se setea via
`Runner.run_async(state_delta=...)` -- en turnos que NO son "knowledge" se
limpia explicitamente a `""` para no filtrar RAG de un turno anterior a un
agente de otro dominio en la misma sesion.

**Verificado:** `test_sintel_rag_adapter.py` (3/3, sin Ollama) + 3 tests
nuevos en `test_sintel_root_workflow.py` -- incluye un test con **Ollama
real** que confirma la respuesta queda basada en el hecho inyectado (horario
7:00am-4:30pm), regresion directa del incidente real de Fase 17. 54/54
tests pasando.

**Gotcha real de mocking encontrado:** mockear `retrievers.httpx.AsyncClient`
rompe cualquier test que en el MISMO turno tambien llame a Ollama real --
`retrievers.py` hace `import httpx` (no `from httpx import AsyncClient`),
asi que parcha el modulo `httpx` COMPARTIDO globalmente, incluyendo el
`AsyncClient` interno de litellm. Fix: mockear
`retrievers.retrieve_knowledge_for_chat` directo, no su transporte.

## Pendiente para ADK-07+

- El resto del contrato de `ChatResponse` (`tool_calls`, `needs_confirmation`,
  `metrics`) -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).

---

# ADK-07 — Knowledge Graph adapter (completado)

Reusa `ai_editor.graph_client` (UNICA frontera oficial hacia
`project_knowledge_graph`), nunca serializa el grafo completo -- las 16
operaciones reales ya devuelven dicts/lists acotados, confirmado contra el
grafo REAL (9575 nodos, 20335 aristas, ya construido).

**Hallazgo real importante (afecta ADK-09/10/11):**
`ai_editor.agent.run_autonomous_change_loop()` YA EXISTE como orquestador
completo end-to-end (intent -> resolver -> planner -> generation -> sandbox
-> `APPROVAL_REQUIRED`), con la regla de seguridad garantizada
ESTRUCTURALMENTE (ausencia de import a `generation.promotion`/
`repository.promote`). Esto contradice la lectura inicial de ADK-00. El rol
de ADK para `ai_editor` deberia ser un wrapper delgado sobre este loop ya
existente, NO reimplementar el pipeline como Tools ADK sueltas -- ver
AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 8sexies para el detalle completo.

`sintel_graph_adapter.py`: subconjunto de 9 operaciones de solo lectura,
pensado para un futuro `EngineeringAgent` (preguntas ad-hoc, no propuestas
de cambio). Bug de naming real encontrado: `__name__` real de la funcion no
siempre coincide con el alias exportado (`calculate_impact.__name__ ==
"calculate_change_impact"`) -- normalizado con un wrapper delgado, sin
mutar la funcion real.

**Verificado contra el grafo real (sin mocks):** 5/5 tests, incluye un
`EngineeringAgent` de prueba con Ollama real respondiendo "que modelos
tiene la app orders" citando correctamente los 11 modelos reales. 58/59
tests en `adk_poc/` (el unico fallo es el flake conocido de ADK-01).

## Pendiente para ADK-08+

- Revisar el hallazgo de `run_autonomous_change_loop` antes de disenar
  ADK-09 (HITL para `ai_editor`).
- El resto del contrato de `ChatResponse` -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).

---

# ADK-08 — Session/state: persistente vs efimero (completado)

Mapeo real contra `redis_checkpointer.py`: el sistema real persiste el
estado completo del turno en Redis (TTL 7 dias), reemplazando un
`MemorySaver()` que antes perdia toda conversacion activa en cada reinicio
del contenedor. Tabla de clasificacion completa en
`AUDITORIA/ADK_MIGRATION_AUDIT.md` seccion 8septies.

**Hallazgo de seguridad real, encontrado y corregido en esta misma fase:**
desde ADK-03, el JWT se sembraba directo en `Session.state`. Confirmado que
ADK tiene su propio `DatabaseSessionService` real (bundled con el
framework) que persistiria `state` tal cual -- si ADK-11+ cambiara
`InMemorySessionService` por un backend persistente sin este fix, el JWT
habria quedado escrito ahi, violando la regla real ya vigente en
`action_graph.py` ("el checkpointer persiste el estado; un token no se
persiste"). Fix: `sintel_adapter._EPHEMERAL_TOKENS`, un dict de proceso
indexado por `session_id`, mismo rol que `config["configurable"]` de
LangGraph -- nunca pasa por `Session.state`.

**Verificado:** un test confirma que el JWT real NUNCA aparece en
`Session.state` despues de un turno completo, mientras la tool real SI lo
recibe y lo usa correctamente. 60/61 tests en `adk_poc/` (unico fallo: el
mismo flake de muestreo del modelo local ya documentado).

## Pendiente para ADK-09+

- Elegir el backend persistente real para ADK-11 (Redis vs
  `DatabaseSessionService`/Postgres) -- verificar capacidades disponibles
  antes de elegir (mismo problema real que forzo `RedisCheckpointSaver` a
  evitar RediSearch).
- El resto del contrato de `ChatResponse` -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).

---

# ADK-09 — Human-in-the-loop para ai_editor (completado)

Diseno directamente informado por el hallazgo de ADK-07: como
`run_autonomous_change_loop()` ya orquesta la PROPUESTA de forma segura
(estructuralmente incapaz de promover), este adapter expone 2 Tools con
gating distinto: `propose_code_change` (sin gate -- seguro, solo toca un
sandbox) y `promote_code_change` (`require_confirmation=True` -- unico
punto con acceso a `review_and_promote`, la funcion real que escribe sobre
`WORKSPACE_ROOT`, confirmado que es literalmente `ecommerce_sintel/` el
repo vivo).

**Verificado (4/4):** gating estructural correcto; **chequeo AST** que
confirma que `propose_code_change` no puede referenciar codigo de
promocion por ningun camino; y, con **Ollama real**, un LLM que decide
promover una propuesta -- ADK pausa, `review_and_promote` (mockeado) nunca
se ejecuta sin confirmacion humana.

**Limite deliberado:** ningun test corre `run_autonomous_change_loop()`
real contra un LLM -- es una cadena larga de llamadas LLM + validacion de
sandbox (el propio `loop.py` la describe como la primera vez que TODO su
plan de 60 fases corre contra un LLM real). Se prueba el mecanismo de
gating, no el contenido que produciria el loop real.

64/64 tests en `adk_poc/`.

## Pendiente para ADK-10+

- Elegir el backend persistente real para ADK-11.
- El resto del contrato de `ChatResponse` -- ADK-10, dual run.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).

---

# ADK-10 — Dual run, contra infraestructura REAL (completado)

**Decision de riesgo deliberada:** `docker ps` confirmo toda la
infraestructura real corriendo (`ecommerce_sintel_redis`,
`ecommerce_sintel_ollama`, `ecommerce_sintel_django`,
`ecommerce_sintel_ai`). El dual run usa Redis y Ollama REALES -- pero NO
extrae el `JWT_SECRET_KEY` real ni golpea el Django real (`fetch_user_
context` mockeado en ambos sistemas, `user_id` sintetico `999999`,
limpieza explicita del thread de Redis en un `finally`).

Se compara `intent`/`agent`/si la respuesta vino no vacia -- no el texto
final palabra por palabra (mismo LLM real en ambos lados, no determinista
turno a turno).

**Resultado, 2/2, CONTRA INFRAESTRUCTURA REAL:** OLD (`action_graph.py`) y
NEW (`sintel_root_workflow.py`) coinciden en `intent`/`agent` para un
mensaje de pedido y para una queja con escalamiento real -- 0
discrepancias en ambos casos.

**Hallazgo real importante para ADK-11 (conflicto de dependencias, no de
logica):** `langchain-openai==0.2.14` (necesario para `get_llm()` real, el
`LOCAL_MODEL_CHAIN` real encadena LM Studio como fallback) exige
`openai<2.0.0`; `litellm` (dependencia de ADK) exige `openai>=2.20.0` --
rangos que NO se solapan. **Mientras el sistema OLD siga vivo, no puede
coexistir con ADK/LiteLLM en el MISMO proceso/venv de produccion** -- un
despliegue de transicion real necesita procesos/servicios separados, no
solo "agregar ADK a ai_engine". Desaparece despues de ADK-12.

66/67 tests en `adk_poc/`.

## Pendiente para ADK-11+

- Decidir arquitectura de despliegue para la transicion (procesos
  separados vs. cutover atomico) dado el conflicto de dependencias real.
- Elegir el backend persistente real para sesiones.
- El resto del contrato de `ChatResponse`.
- Flujo de RESUME tras confirmacion real (heredado de ADK-02).
- Verificar `JSON_SCHEMA_FOR_FUNC_DECL=False` contra LM Studio (heredado de
  ADK-01).
