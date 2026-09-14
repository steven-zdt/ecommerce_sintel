# ADK_MIGRATION_AUDIT.md — ADK-00

**Fecha:** 2026-09-14. Mision "ADK-SINTEL": migracion controlada de la orquestacion de
agentes hacia Google Agent Development Kit (ADK) Python. Este documento es **ADK-00**
unicamente — auditoria de solo lectura, **cero codigo modificado**, tal como exige la
propia mision (seccion 6: "No modificar codigo en esta fase").

Ubicacion: se genera en `AUDITORIA/` (convencion ya establecida en este repo para
auditorias de arquitectura, ver `AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md`,
completada hoy mismo unas horas antes de esta mision) en vez de `docs/ai/` (el path que
pedia el prompt original) — `docs/ai/` no existe en este repo y no hay otra convencion
que lo use; se prioriza consistencia con lo que ya existe sobre el path literal pedido.

## 0. Guardrail obligatorio: ADK 2.x vs ejemplos legacy

**Verificado contra el repositorio real `google/adk-python` (no contra blogs ni memoria):**

- **`SequentialAgent`, `ParallelAgent`, `LoopAgent` estan oficialmente DEPRECADOS.**
  Confirmado leyendo los docstrings reales del codigo fuente actual: los tres llevan
  `.. deprecated::` explicito ("deprecated in favor of Workflow and will be removed in a
  future version"), `LoopAgent` ademas con decorador `@deprecated` en la clase. **Cualquier
  ejemplo historico (blog, doc antigua, entrenamiento del modelo) que use estas tres clases
  como arquitectura de referencia esta desactualizado.** No copiar esos ejemplos sin
  verificar primero contra el codigo real bajo `src/google/adk/`.
- La API vigente es un **motor de grafo `Workflow`** (`src/google/adk/workflow/`):
  `Workflow(BaseNode)` compila `edges: list[EdgeItem]` en un `Graph` y lo ejecuta
  START → nodos listos (via `NodeRunner`) → nodos terminales. Tipos de nodo: funcion, tool,
  join, parallel-worker, retry, wrapper de `LlmAgent`.
- **Limitacion real y actual, relevante para el diseno de Root Agent → Support/Sales/Ops
  (seccion 4/6 del plan):** el propio codigo indica que `Workflow` **todavia no puede
  usarse como sub-agente de un `LlmAgent`** ("Workflow cannot yet be used as an LlmAgent
  sub-agent"). Esto condiciona como se implementa la delegacion Root → Agentes de dominio
  en ADK-03/05 — hay que validarlo explicitamente en el POC (ADK-01), no asumir que la
  composicion anidada funciona igual que con agentes simples.
- `LlmAgent`/`BaseAgent` siguen siendo los primitivos de agente vigentes (no deprecados).
- **Paquete real:** `pip install google-adk` (PyPI, no `adk-python` ni otro nombre),
  ultima version publicada verificada: **2.9.0** (2026-09-10). Requiere **Python 3.10+**
  (compatible con Python 3.12 de `ai_engine` y 3.13 de Django en este proyecto).
- **Model-agnostico, confirmado:** `src/google/adk/models/` incluye `lite_llm.py`
  (wrapper LiteLLM — el camino generico no-Gemini), `anthropic_llm.py`, `gemma_llm.py`,
  ademas de `google_llm.py`. La pagina oficial (adk.dev) lista soporte explicito para
  Claude/OpenAI/**Ollama**/vLLM/LiteLLM — compatible con el stack actual de Sintel
  (Ollama en dev, LM Studio OpenAI-compatible en prod), **no ata el proyecto a Gemini**.
  No verificado en esta pasada: la firma exacta de `LiteLlm.__init__()` y un snippet
  literal de uso con Ollama (el fetch se corto antes de esa clase) — pendiente para
  ADK-01.
- **HITL / aprobacion humana, confirmado nativo:** `FunctionTool(fn,
  require_confirmation=True)` (bool o predicado async) pausa la ejecucion de una tool
  hasta confirmacion; `ToolContext.requestConfirmation(hint=..., payload=...)` para el
  flujo mas rico (pausa/resume via UI o API REST). Esto es un candidato real para envolver
  (no reemplazar) el gate de `ai_editor.repository.promote_to_workspace()` — ver seccion 4.
- No verificado en esta pasada (marcar como pendiente, no asumir): version exacta en la
  que Sequential/Parallel/Loop se eliminan de verdad (el docstring dice "a future version",
  sin numero); si siguen funcionando hoy o solo emiten warning (la redaccion sugiere que
  si funcionan, con warning).

## 1. Inventario real de Sintel — 5 sistemas, confirmados existentes y separados

Coincide con la separacion que propone el usuario (seccion 1/3 de su mensaje) — **confirmado
correcto**, con los paths reales (no `apps/tenant/ai_knowledge/` ni `apps/services/ai/`,
que no existen en este repo):

| Sistema | Path real | Responsabilidad | Corre como |
|---|---|---|---|
| AI Engine | `ecommerce_sintel/ai_engine/` | Chatbot de soporte al cliente: routing de intents, agentes, tools, RAG-consumer | Microservicio FastAPI propio, contenedor `sintel_ai` |
| AI Provider | `ecommerce_sintel/ai_provider/` | Config de que proveedor/modelo LLM (chat) y de embeddings usar, runtime, editable desde panel | App Django |
| AI Knowledge | `ecommerce_sintel/ai_knowledge/` | RAG semantico: `AIKnowledgeDocument`/`AIKnowledgeChunk`, `EmbeddingService`, `RetrievalService` sobre pgvector (construido hoy mismo, ver `AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md`) | App Django |
| AI Editor | `ecommerce_sintel/ai_editor/` | Propuestas de cambio de codigo seguras (intent→resolver→planner→sandbox→validacion→aprobacion→promocion→rollback) | **Sin Dockerfile, sin entrypoint CLI, sin servicio en docker-compose** — no corre hoy como proceso persistente, se invoca via tests/management (confirmar mecanismo real exacto en ADK-01/02, es un hueco de este audit) |
| Project Knowledge Graph (EKG) | `ecommerce_sintel/project_knowledge_graph/` | Conocimiento estructural del codigo: scanner, Project Map, Knowledge Graph, Dependency Graph, deteccion incremental, `graph_sdk`, CLI | Libreria Python pura, sin servicio propio, consumida por `ai_editor` via `graph_client` y por su propio `cli/` |

**Correccion importante al plan del usuario:** `ai_editor` NO tiene Dockerfile ni esta
declarado en `docker-compose.yml`/`docker-compose.prod.yml` (verificado, cero
coincidencias). Cualquier diseno de "donde vive el ADK Runner de ai_editor" (ADK-11) debe
partir de que hoy no hay un proceso persistente al que atarlo — es un hallazgo nuevo, no
mencionado en el plan original, y cambia el orden de riesgo: ai_editor no tiene trafico de
produccion que proteger de una migracion a medias, a diferencia de `ai_engine`.

## 2. AI Engine — estado real HOY (post-simplificacion de hoy mismo)

El plan del usuario cita "29 capabilities y 9 agent profiles" y "31 endpoints internos" —
**verificado en el codigo real, actualizado a la fecha de este documento:**

- Agent profiles: **9** (`ai_engine/agents/profiles/*.yaml`) — coincide.
- Capabilities registradas: **30** (`capabilities/registry.py`) — cercano, no exacto (30 no 29;
  diferencia menor, no material).
- Endpoints internos `/api/v1/internal/ai/*`: **36** (`ecommerce/internal_ai_urls.py`,
  contados hoy) — el plan dice 31; la cifra crecio con trabajo de esta misma sesion (Meta
  Business, `ai_knowledge/retrieve/`). Usar 36 como cifra vigente, no 31.
- `action_graph.py` (923 lineas) sigue siendo el unico orquestador real de `/chat` —
  confirmado que hace routing de intent, seleccion de agente, ejecucion de tools, policy
  layer (limite diario de turnos, rate limit), y generacion de respuesta. Esto SI es
  candidato directo a reemplazo por `Workflow`/`Runner` de ADK (coincide con el analisis
  del usuario, seccion 3).
- **Importante, y NO mencionado en el plan: `ai_engine` ya fue objeto de una limpieza
  arquitectonica completa HOY MISMO** (sesion previa, mismo dia, commits `cf50009` →
  `f3c8638` en esta misma branch `fix/audit-p0-remediation`): se elimino por completo el
  pipeline de generacion de codigo que antes vivia dentro de `ai_engine` (`/generate`,
  `/plan`, `/impact`, etc. — 6 modulos, ~1900 lineas) y ChromaDB (5 modulos mas, servicio
  Docker, dependencias). `ai_engine` hoy expone **exactamente 2 rutas propias**: `POST
  /chat` y `GET /health`, mas el AI Gateway (`/api/v1/ai/*`, MCP de Meta Ads, sin tocar).
  Cualquier documentacion o ejemplo que mencione `/generate`/`/plan`/ChromaDB/embeddings
  locales en `ai_engine` describe el estado **anterior a hoy**, no el actual.

## 3. Correcciones a supuestos del plan que no coinciden con el codigo real

| Supuesto del plan | Estado real verificado | Accion recomendada |
|---|---|---|
| `AIEmbeddingProvider` (seccion 12: "Mantener EmbeddingService, AIEmbeddingProvider, AIKnowledgeDocument, AIKnowledgeChunk") | **No existe y NUNCA se construyo a proposito** — se reutilizo `ai_provider.AIChannelConfig` con un canal nuevo `CHANNEL_EMBEDDINGS` en vez de duplicar `AIProvider`/`AIModel` en un modelo paralelo (decision explicita de esta misma sesion, documentada en el commit `aa3dd41`, exactamente para cumplir la regla de "no duplicar" que el propio plan pide en su seccion 5) | No crear `AIEmbeddingProvider` en ninguna fase futura. Seguir usando `AIChannelConfig.CHANNEL_EMBEDDINGS` |
| `AIContext` (seccion 10 y 14 del plan: SSoT de contexto operacional usuario/tenant/sede/area/permisos) | **No existe en absoluto** — cero coincidencias en todo el repo. Es una propuesta de disenar-desde-cero, no algo a "mantener" | Si se decide construirlo (ADK-08), es trabajo NUEVO, no una migracion de algo existente. Antes de crearlo, mapear que de "tenant/sede/area" aplica de verdad (ver fila siguiente) |
| Multi-tenancy / tenant isolation / tenant scope (mencionado repetidamente en secciones 3, 11, 15, 16, 22, 26 del plan) | **No existe ningun concepto de tenant en `ai_editor`/`project_knowledge_graph`, y el proyecto completo es deliberadamente single-tenant** (decision registrada 2026-08-14 en `AUDITORIA/WHITE_LABEL/WHITE_LABEL_DECISION_RECORD.md`, reconfirmada explicitamente por el usuario en vivo el 2026-09-14: "no apliques multitenant a este proyecto") | **Eliminar toda mencion a tenant/multi-tenant del prompt de ejecucion** — no es un guardrail a preservar, es una feature que no existe y no se va a construir. Cualquier "tenant isolation test" de la seccion 22 del plan no tiene contra que probar |
| `apps/tenant/ai_knowledge/`, `apps/services/ai/` (seccion 6 del plan, rutas a auditar) | No existen — este proyecto no usa un prefijo `apps/`. Los paths reales ya estan en la tabla de la seccion 1 de este documento | Corregir la lista de paths en cualquier prompt de ejecucion futuro |
| `resolve_change()`, `calculate_change_impact()`, `build_graph_context_packet()` como API publica de `graph_sdk` (seccion 13 del plan) | Los tres existen como implementacion real en `project_knowledge_graph/knowledge_graph/query.py`, PERO la superficie publica de `graph_sdk`/`ai_editor.graph_client` (el unico punto de entrada permitido, por regla arquitectonica ya existente) expone `resolve_change()` igual, mas `calculate_impact()` (no `calculate_change_impact`) y `build_context_packet()` (no `build_graph_context_packet`) | Usar los nombres publicos reales: `calculate_impact()`, `build_context_packet()`. `graph_client` expone 16 operaciones en total (ver seccion 4) |
| Pipeline de `ai_editor` como 11 pasos lineales incluyendo `graph_client` como etapa propia (secciones 5, 19 del plan) | El pipeline real (`ai_editor/.AGENT/CHANGE_FLOW.md`) es mas granular (12 pasos) y `graph_client` **no es una etapa independiente** — es una dependencia interna de `resolver.resolve_change_context()`. Ademas hay una etapa explicita de `repository.create_sandbox()` que el plan omite de su lista aunque la menciona sueltamente en otras secciones | Usar el pipeline real (seccion 4 de este documento) al disenar el ADK Workflow de ADK-11, no la version simplificada del plan |
| IMPLEMENTATION_SUMMARY.md describe la arquitectura vigente | El propio usuario ya lo identifico correctamente en su mensaje: ese documento describe el estado anterior a la migracion de hoy (ChromaDB). Documentos afectados por la migracion de hoy (`ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`, `GUIA_USO.md`) ya quedaron marcados explicitamente como HISTORICOS en el commit `ae45755` | Tratar `IMPLEMENTATION_SUMMARY.md` con la misma cautela — no esta corregido todavia, queda pendiente si se decide seguir con esta mision |

## 4. `ai_editor` + `project_knowledge_graph` — pipeline y API reales (para ADK-06/07/11)

**`graph_client`** (`ai_editor/graph_client/__init__.py`) es, confirmado, el UNICO punto de
entrada permitido hacia `project_knowledge_graph` (re-exporta `graph_sdk` por identidad de
objeto; ningun otro submodulo de `ai_editor` puede importar
`project_knowledge_graph.knowledge_graph.*`/`.internal.*` directo — regla ya verificada por
AST en los tests existentes, mismo patron que la regla "AI Engine nunca importa Postgres
directo"). 16 operaciones publicas: `resolve_change`, `find_symbol`, `find_file`,
`find_endpoint`, `find_consumers`, `trace_data_flow`, `trace_execution`, `find_tests`,
`find_docs`, `calculate_impact`, `build_change_plan`, `build_context_packet`,
`find_configuration`, `find_node`, `get_app_summary`, `get_graph_status`.

**Pipeline real de `ai_editor`** (`ai_editor/.AGENT/CHANGE_FLOW.md`), 12 pasos:

```
intent.interpret_request
  -> resolver.resolve_change_context()          [usa graph_client.resolve_change internamente]
  -> planner.build_change_plan() + validate_plan()
  -> repository.create_sandbox()                 [etapa explicita de sandbox, copia aislada]
  -> patch.apply_operation()
  -> validation.run_validation() + build_test_validation_report()
  -> approval.build_change_summary() + record_decision()   [gate humano]
  -> repository.promote_to_workspace() (+ rollback_promotion() si falla)
  -> audit.audit_pipeline_run()
```

**`promote_to_workspace()`** (`ai_editor/repository/promote.py:83`) — confirmado, 4 gates
independientes, cualquiera bloquea: (a) `approval.decision == APPROVE`; (b) `confirm=True`
explicito, separado de la aprobacion; (c) si viene `validation_report`, exige
`level_1_passed` (sintaxis); (d) chequeo de fingerprint por archivo contra el workspace real
antes de escribir (todo o nada). `rollback_promotion()` existe en paralelo
(`ai_editor/repository/rollback.py`).

**Modulo real de `ai_editor`** (66 archivos .py): `agent/`, `approval/`, `audit/`, `data/`,
`generation/`, `graph_client/`, `intent/`, `llm/`, `patch/`, `planner/`, `repository/`,
`resolver/`, `validation/`, mas `workspace.py`. 28 docs bajo `.AGENT/`.

**Modulo real de `project_knowledge_graph`** (93 archivos .py): `audit/`, `cli/`, `data/`,
`dependency_graph/`, `graph_sdk/`, `incremental/`, `knowledge_graph/` (+`enrichers/`),
`project_map/`, `scanner/`, `snapshots/`, `tests/` (49 archivos — la suite real de
`ai_editor` vive AQUI, no dentro de `ai_editor/`, salvo 1 archivo inline). Ultima medicion
documentada: 9.575 nodos / 20.335 aristas (cifra del plan del usuario, no re-verificada en
esta pasada — pendiente confirmar via `graph_client.get_graph_status()` en ADK-01).

**Sandbox real, confirmado:** `ai_editor/repository/sandbox.py` (`create_sandbox`) — copia
aislada de archivos, el workspace real nunca se toca hasta `promote_to_workspace`.
Documentado en `ai_editor/.AGENT/FASE61_12_SANDBOX.md`.

## 5. Riesgos identificados para las fases siguientes

1. **`Workflow` no puede ser sub-agente de un `LlmAgent` todavia** (seccion 0) — el diseno
   Root Agent → Support/Sales/Operations/Engineering Agent (seccion 6/4 del plan) asume
   composicion anidada fluida; hay que validar en ADK-01 si esto se resuelve con
   `LlmAgent.sub_agents` normal (sin pasar por `Workflow` en cada nivel) o si requiere un
   patron distinto al propuesto.
2. **`ai_editor` no corre como servicio hoy** — antes de ADK-11 (orquestacion de AI Editor)
   hace falta decidir DONDE corre el ADK Runner que lo invoque (nuevo proceso? dentro de
   `sintel_ai`? management command de Django?). No es una decision tecnica que corresponda
   tomar en este documento.
3. **Mezcla de Python 3.12 (`ai_engine`) y 3.13 (Django)** — ADK exige 3.10+, ambos
   cumplen, pero si se decide correr ADK del lado Django (para acceso directo a
   Commands/Selectors sin cruzar el bridge HTTP) es una decision de imagen/dependencias
   nueva, no trivial.
4. **El propio plan reconoce (seccion 26) "ADK nunca debe convertirse en autoridad de
   negocio"** — esto ya es consistente con la arquitectura actual (AI Engine llama a
   Django via HTTP interno, nunca al reves) y no requiere cambio de diseno, solo
   preservarlo explicitamente en cada fase.
5. **`LiteLlm` (integracion Ollama/LM Studio) no se verifico a nivel de firma/uso real** —
   pendiente confirmar antes de escribir cualquier codigo de ADK-01 que dependa de esto,
   dado que el stack de Sintel es 100% Ollama/LM Studio, nunca Gemini.

## 6. ADK-01 — POC aislado (completado)

Codigo en `adk_poc/` (repo root, fuera de `ecommerce_sintel/`, sin Dockerfile, sin entrada
en `docker-compose*.yml`, venv propio no versionado) — ver `adk_poc/README.md` para el
detalle completo. **5/5 tests pasando, contra un Ollama real (`llama3.1:8b`), sin mocks.**

**Hallazgo real mas importante, no anticipado en la seccion 0 de este documento:** ADK
2.9.0 trae activada por default una feature experimental (`JSON_SCHEMA_FOR_FUNC_DECL`) que
**rompe el tool-calling nativo** cuando el modelo es `LiteLlm(model="ollama_chat/...")` — el
LLM nunca dispara una llamada de funcion real, solo ecoa la declaracion de la tool como
texto plano. Aislado (con una llamada `litellm.completion()` cruda) a la capa de ADK, no a
Ollama ni a litellm. Fix confirmado: `override_feature_enabled(FeatureName.
JSON_SCHEMA_FOR_FUNC_DECL, False)`, ejecutado ANTES de importar `google.adk.agents`/
`google.adk.tools`/`google.adk.models.lite_llm` (verificado que llamarlo despues, aunque
sea antes de construir el `Agent`, no tiene efecto). **Impacto: cualquier agente de Sintel
que use `LiteLlm`+Ollama para tool-calling nativo necesita este override global al
arrancar el proceso, o las tools nunca se invocan de verdad.** Esto es exactamente lo que
ADK-01 existe para descubrir antes de comprometerse a la migracion — sin este POC, este bug
se habria descubierto recien en ADK-10 (dual-run) o peor, en produccion.

Otros hallazgos de API real: `FunctionTool` no tiene atributo publico `require_confirmation`
(usar `_require_confirmation`/`check_require_confirmation()`); `InMemoryRunner` exige crear
la sesion explicitamente (`await runner.session_service.create_session(...)`) antes de
`run_async()`; `SequentialAgent`/`ParallelAgent`/`LoopAgent` confirmados funcionales HOY
(solo warning), no eliminados todavia — refuerza el guardrail de la seccion 0, no lo cambia.

**Pendiente, fuera de alcance de ADK-01:** el mismo fix no se probo contra LM Studio
(proveedor real de produccion); la limitacion "Workflow no puede ser sub-agente de un
LlmAgent" sigue sin probarse en la practica; el flujo completo de
`ToolContext.requestConfirmation()` (pausa+resume real) no se ejecuto, solo se confirmo que
la API existe.

## 7. ADK-02 — SINTEL Tool Adapter (completado)

`adk_poc/sintel_adapter.py::adapt_sintel_tool()` — toma una `RegisteredTool` REAL de
`ai_engine.tools.registry` (importada via `sys.path`, sin copiar ni un archivo) y produce
una `FunctionTool` de ADK real. Mapeo directo `ToolMetadata.requires_confirmation` ->
`FunctionTool(require_confirmation=...)`.

**Verificado end-to-end con dos Tools reales de `ai_engine`, sin duplicar logica:**

- `OrderStatusTool` (lectura): Ollama decide llamar la tool -> adapter -> funcion real
  `order_status_tool()` -> `django_internal_get()` (unico punto mockeado) -> respuesta
  final coherente con el dato real devuelto. Confirmado explicitamente que la funcion
  invocada es `is` la funcion original (no una copia), y que el token de la sesion de ADK
  llega intacto hasta la llamada HTTP.
- `RequestKycUpgradeTool` (escritura real, `side_effects=True`,
  `requires_confirmation=True`): confirmado que el gate **efectivamente pausa** la
  ejecucion — ADK emite `requested_tool_confirmations` y `django_internal_post` **nunca se
  ejecuta** sin confirmacion. Mismo principio estructural que
  `ai_editor.repository.promote_to_workspace()` ya exige del lado Sintel — ADK puede
  sostener ese gate tambien para tools normales de `ai_engine`.

**Riesgo nuevo encontrado:** el mecanismo de confirmacion (`FeatureName.TOOL_CONFIRMATION`)
tambien esta marcado EXPERIMENTAL en ADK 2.9.0 (mismo estado que
`JSON_SCHEMA_FOR_FUNC_DECL` de ADK-01) — no asumir estabilidad de API entre versiones de
ADK para HITL.

**Pendiente para ADK-03 (no resuelto aqui, fuera de alcance de ADK-02):** resolucion de
identidad real (aqui se sembro el token a mano en `create_session(state=...)`); el flujo de
RESUME tras confirmacion real (solo se probo la mitad "pausa"); generalizar el adapter a
tools con `**kwargs` reales (ej. `CreateRentalRequestTool`); fix de `JSON_SCHEMA_FOR_FUNC_DECL`
sin probar contra LM Studio (proveedor real de produccion).

## 8bis. ADK-03 — Root Workflow (completado)

**Hallazgo central: la limitacion "`Workflow` no puede usarse aun como sub-agente de
`LlmAgent`" (ADK-00, ADK-01) NO aplica al patron Root -> Support/Sales/Operations del plan
de migracion.** Ese patron no necesita `Workflow` en absoluto — usa
`BaseAgent.sub_agents: list[BaseAgent]` + `LlmAgent.disallow_transfer_to_parent/
disallow_transfer_to_peers`, un mecanismo de delegacion LLM-driven (`transfer_to_agent`)
propio de `LlmAgent`, real y NO deprecado, distinto y mas simple que el motor de grafo
`Workflow` (candidato, sin decidir todavia, para el pipeline mas rigido de `ai_editor` en
fases posteriores, no para el routing de negocio).

**Verificado en vivo (`adk_poc/test_root_workflow.py`, 2/2, contra Ollama real, sin mocks
de LLM):** un Root Agent con `sub_agents=[support_agent, sales_agent]` delega la pregunta
de pedidos a `support_agent` y la pregunta de catalogo a `sales_agent`, sin cruces —
routing real decidido por el LLM segun la instruccion del Root, no hardcodeado por regex/
intent-matching propio.

**Hallazgo arquitectonico no anticipado: el sistema "AIContext" que el plan de migracion
proponia crear como pieza NUEVA ya existe, con otro nombre.** `ai_engine/auth.py` ya
resuelve identidad completa en dos pasos reales: `decode_django_jwt()` (verifica firma
HS256 + expiracion localmente, misma `SIGNING_KEY` de SimpleJWT) y `fetch_user_context()`
(reenvia el token al endpoint interno de Django `/internal/ai-context/`, que es la unica
autoridad real de perfil — `ProfileResolver` vive solo ahi). ADK-03 reutiliza este boundary
tal cual (`adk_poc/sintel_root_workflow.py::resolve_identity()`), sin duplicarlo. No se
necesita construir un "AIContext" nuevo — falta, como mucho, decidir si se le pone ese
nombre al que ya existe.

**Sesion:** el patron real de `action_graph.run_action_chat` (`thread_id =
f"{user_id}:{conversation_id}"`, namespaced por usuario para que nadie retome la
conversacion de otro adivinando el conversation_id) se replico 1:1 como `session_id` de
ADK (`build_session_id()`). Verificado que un segundo turno con el mismo
`conversation_id` reusa la misma sesion de ADK (no se recrea, no se pierde estado) via el
guard `get_session()` antes de `create_session()`.

**`adk_poc/sintel_root_workflow.py` — alcance deliberado:** solo se construyo UN agente de
dominio real, `support_agent`, envolviendo las 2 tools ya probadas en ADK-02
(`OrderStatusTool`, `KycStatusTool`). El registro real de `ai_engine` tiene ~28 tools
repartidas en 10 dominios (core, inventory, kyc, marketing, orders, payment, quotes,
renting, services, support) — migrarlas y separar Sales/Operations/Engineering como
sub-agentes reales es explicitamente trabajo de ADK-04 (Support Agents) y ADK-05
(migracion de tools 1 a 1), no de ADK-03, para no inventar logica de dominio antes de
tener las tools reales migradas (regla de cambio minimo, seccion 2 del plan).

**Verificado end-to-end (`adk_poc/test_sintel_root_workflow.py`, 3/3):** JWT real firmado
con PyJWT (no mockeado) -> `decode_django_jwt` real lo valida -> `fetch_user_context`
(mockeado, unico punto de red) resuelve contexto -> Root Agent enruta a `support_agent` ->
`OrderStatusTool` real ejecuta (`django_internal_get` mockeado) -> respuesta final
coherente. Incluye un test negativo: JWT firmado con la clave incorrecta falla cerrado
(`IdentityResolutionError`), nunca degrada a turno anonimo.

**Pendiente para ADK-04+ (no resuelto aqui, fuera de alcance de ADK-03):** el resto del
contrato de `ChatResponse` (`intent`, `tool_calls`, `needs_confirmation`, `metrics`) — este
runtime solo cubre identidad/sesion/routing/eventos, no reemplaza `/chat` todavia; eso se
decide en ADK-10 (dual run) comparando ambos runtimes antes de exponer nada. Tambien sigue
pendiente: flujo de RESUME tras confirmacion real, generalizar el adapter a tools
`**kwargs`, y verificar el fix de `JSON_SCHEMA_FOR_FUNC_DECL` contra LM Studio (heredado de
ADK-01/02, todavia sin probar).

## 8ter. ADK-04 — Support Agents (completado)

**Hallazgo previo a escribir codigo, reportado al usuario antes de continuar (checkpoint
de "ambiguedad de migracion"):** el routing real de `ai_engine` NO es una decision del LLM
— es 100% deterministico. `ai_engine/agents/` (`AgentRegistry`, cargado desde
`agents/profiles/*.yaml`) declara **9 perfiles reales**: `AccountAgent`, `AdminAgent`,
`MarketingAgent`, `OrderAgent`, `PaymentAgent`, `RentalAgent`, `SalesAgent`, `ServiceAgent`,
`SupportAgent` (coincide con "9 agent profiles" de la seccion 2). Cada uno declara sus
tools, permisos, intents y `reglas_escalamiento` (regex de seguridad — ej. una queja SIEMPRE
escala a `SupportAgent`; un cambio de fecha de alquiler SIEMPRE es no-self-service, decision
del usuario 2026-07-16 "gap #1"). `action_graph.py` lo declara como regla dura: *"Ninguna
regla de negocio vive en el prompt: las Tools/Selectors deciden."*

Esto entra en tension directa con el mecanismo `sub_agents`/transfer validado en ADK-03 (LLM
decide a quien transferir). Usar ese mecanismo como router de produccion violaria "ADK
ORQUESTA. SINTEL EJECUTA Y CONTROLA" — dejaria decisiones de seguridad de negocio (ej.
escalar una queja a un humano) al juicio de un LLM en vez de una regex ya probada en
produccion. **Se pregunto al usuario explicitamente y decidio: el router deterministico de
Sintel decide, ADK solo ejecuta al agente ya elegido.** El mecanismo `sub_agents` queda
confirmado como una capacidad real y funcional de ADK 2.9.0 (ver `test_root_workflow.py`,
conservado con docstring actualizado aclarando que no se usa para routing de produccion),
sin uso en el runtime real.

**`sintel_root_workflow.py` (reescrito):**
- `resolve_turn_agent(message)` reutiliza tal cual `action_graph.detect_business_intents` +
  `agents.AgentRegistry.route/apply_escalation` (mismas funciones reales, no una copia) —
  replica exactamente la logica de `action_graph.py::node_detect_intent`.
- `get_domain_agent(profile_name)` construye un `LlmAgent` real por cada uno de los 9
  perfiles YAML — mismas tools (adaptadas con `sintel_adapter.adapt_sintel_tool`, ADK-02),
  mismo objetivo/personalidad/tono como instruccion (texto real, no inventado).
- Cambio de `InMemoryRunner` a `Runner` explicito con un `InMemorySessionService`
  compartido a nivel de modulo — **hallazgo real, verificado leyendo el codigo fuente**:
  `InMemoryRunner.__init__` crea su PROPIO `InMemorySessionService` aislado por instancia:
  si el agente activo cambia de un turno a otro (routing real, no hipotetico) y se creara
  un `InMemoryRunner` por turno, la sesion se perderia. `Runner` acepta `session_service`
  como argumento explicito — se comparte uno solo entre turnos.

**Bug real encontrado construyendo los 9 agentes (no sintetico, con las tools reales):**
`sintel_adapter.py::adapt_sintel_tool` no soportaba tools con `**kwargs` real — 5 tools
reales (`CoreBannerUpdateTool`, `CoreBannerCreateTool`, `CoreNavbarLinkUpdateTool`,
`CoreNavbarLinkCreateTool`, `CoreBrandSliderUpdateTool`, todas de `AdminAgent`) fallaban con
`ValueError: wrong parameter order` al construir la firma del wrapper (un
`KEYWORD_ONLY` despues de `VAR_KEYWORD` es invalido en Python). Arreglado ese error de
orden, quedaba un bug de correctness mas serio y silencioso: un `**kwargs` puro no expone
NINGUN campo opcional al LLM (subtitle, link_url, link_label, display_order...) aunque la
tool real si los acepta. **Fix:** cuando la funcion real tiene `VAR_KEYWORD`, el adapter
sintetiza parametros keyword-only adicionales leyendo `ToolMetadata.args_schema.properties`
— la fuente REAL que ya declara esos campos (`core_tools.py`), no una inferencia inventada.
Verificado con `test_sintel_adapter_kwargs.py` (2/2): el LLM ve todos los campos reales, y
el wrapper filtra `None` antes de reenviar al `real_func`, mismo criterio que la tool
original.

**Verificado:** los 9 perfiles reales construyen sus `LlmAgent` correctamente (33
instancias de tool adaptadas en total, contando reuso entre perfiles — ej. `OrderStatusTool`
aparece en `OrderAgent`/`ServiceAgent`/`SupportAgent`). 16/16 tests pasando en `adk_poc/`
salvo un flake ya documentado y confirmado pre-existente (`test_agent_runner_tool_session_event_async_e2e`
de ADK-01 — reproducido 3/3 en aislado tras el fallo, es variabilidad de muestreo de
`llama3.1:8b` local, no una regresion de ADK-04).

**Pendiente para ADK-05+:** el resto del contrato de `ChatResponse` (`tool_calls`,
`needs_confirmation`, `metrics`) sigue sin replicarse (ADK-10). El flujo de RESUME tras
confirmacion real sigue sin probarse (heredado de ADK-02). El fix de
`JSON_SCHEMA_FOR_FUNC_DECL` sigue sin verificarse contra LM Studio (heredado de ADK-01) —
dado el flake de arriba, verificar tambien si LM Studio (proveedor real de produccion) es
mas o menos confiable que Ollama para tool-calling con este modelo/tamano.

## 8quater. ADK-05 — migracion de tools 1 a 1 (completado)

Alcance real verificado: ADK-04 ya habia adaptado las 33 instancias de tool de los 9
perfiles sin excepciones de construccion, pero eso solo probaba que `adapt_sintel_tool` NO
truena — no que la superficie expuesta al LLM sea exactamente la correcta. ADK-05 audito el
**registro completo real (29 tools, confirmado en vivo con `tools.list_tools()`)** cruzando,
para cada una, la firma expuesta por el wrapper contra `ToolMetadata.args_schema.properties`.

**Bug de seguridad real encontrado (no hipotetico) auditando `OpenSupportTicketTool`:** su
funcion real (`ai_engine/tools/support_tools.py::open_support_ticket_tool`) tiene un
parametro real `history: list | None = None` que **deliberadamente NO esta en
`args_schema`** — el comentario del propio codigo dice *"el LLM jamas lo controla"*: lo
inyecta el grafo desde su propio estado (Human Handoff, Fase 7), nunca el usuario/LLM. El
adapter de ADK-02/04 construia la superficie expuesta al LLM leyendo `inspect.signature`
directo (menos `ctx`), sin cruzarla contra `args_schema` para los parametros NO-`**kwargs`
— eso habria expuesto `history` como un campo rellenable por el LLM en la migracion real,
violando un boundary de seguridad ya deliberado del sistema actual.

**Fix (`sintel_adapter.py`, rediseño):** `ToolMetadata.args_schema.properties` pasa a ser la
**unica fuente autoritativa** de que expone el wrapper al LLM — nunca `inspect.signature`
cruda. Un parametro real ausente del schema no se expone ni se reenvia; `real_func` usa su
propio default cuando el wrapper no se lo pasa. Los parametros `**kwargs` siguen
sintetizandose desde `args_schema` igual que en ADK-04.

**Verificado exhaustivamente, no solo con casos puntuales:**
`test_adk05_tool_registry_audit.py` (31/31) recorre las **29 tools reales** una por una y
confirma que la firma expuesta == `args_schema.properties` exacto, sin excepciones ni casos
ocultos adicionales mas alla de `history`. `test_sintel_adapter_hidden_param.py` prueba
end-to-end con Ollama real: el LLM abre un ticket de soporte real (con una queja real como
input) y `history` nunca llega al body HTTP real, aunque la tool si tiene ese parametro en
Python.

**Conclusion de alcance:** con este fix, las 29 tools reales del registro quedan
adaptadas correcta y exhaustivamente — no queda trabajo pendiente de "migrar tools 1 a 1"
mas alla de lo ya cubierto por ADK-04+ADK-05 combinados. 48/48 tests pasando en `adk_poc/`.

**Pendiente heredado (sin cambios):** el resto del contrato de `ChatResponse` (`tool_calls`,
`needs_confirmation`, `metrics`) sigue sin replicarse (ADK-10). El flujo de RESUME tras
confirmacion real sigue sin probarse (ADK-02). El fix de `JSON_SCHEMA_FOR_FUNC_DECL` sigue
sin verificarse contra LM Studio (ADK-01).

## 8quinquies. ADK-06 — RAG adapter (completado)

Regla dura del plan (seccion 6): reusar `RetrievalService`/pgvector via `ai_knowledge`,
nunca reintroducir ChromaDB/FAISS/un segundo vector store. Verificado: `sintel_rag_adapter.py`
no habla con pgvector ni con Django directo — reutiliza tal cual
`ai_engine/retrievers.py::retrieve_knowledge_for_chat`, la MISMA funcion real que ya usa
`action_graph.py::node_retrieve_knowledge` desde la migracion ChromaDB->pgvector (mision
anterior, ver `project_chromadb_to_pgvector_migration` en memoria). Cero logica de retrieval
nueva.

**Decision de arquitectura consistente con ADK-04 (mismo principio, no una decision nueva):**
en el sistema real, retrieval NO es una Tool que el LLM decide invocar — es una rama
determinista del grafo (`node_route_after_context`, activa SOLO si `intent == "knowledge"`,
clasificado por regex). El Root Workflow decide SI hace retrieval (reusando
`resolve_turn_agent()`, ya determinista desde ADK-04) y le INYECTA el resultado al agente —
nunca se expone como FunctionTool. Routing real: `AgentRegistry` asigna el intent
`"knowledge"` a **SalesAgent** (`sales_agent.yaml`: `intents: [promos, quote, knowledge]`,
`memoria: conversacion + cliente + empresarial (RAG)`) — verificado en vivo con
`resolve_turn_agent("Cual es la politica de garantia de ustedes?")` -> `("knowledge",
"SalesAgent", None)`.

**Hallazgo real de gobernanza que este adapter debia replicar (Fase 17, ya documentado en el
codigo real):** `node_retrieve_knowledge` inyecta un marcador EXPLICITO ("NINGUNO -- no se
encontro informacion verificada sobre este tema.") cuando no hay chunks — el comentario real
documenta el incidente que lo motivo: sin el, el LLM alucino una respuesta (horario de
atencion) rellenando el hueco con un chunk irrelevante (mismo incidente que
`project_support_agent_separation_plan` en memoria del agente). `build_knowledge_context()`
replica ese marcador BIT a BIT.

**Mecanismo de inyeccion (hallazgo de API real de ADK):** `LlmAgent.instruction` acepta un
CALLABLE `(ReadonlyContext) -> str`, evaluado por turno (no solo un string fijo) —
confirmado via `LlmAgent.model_fields['instruction'].annotation`. `get_domain_agent()` ahora
construye la instruccion asi, leyendo `SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY` del state de la
sesion. Ese state se setea por turno via `Runner.run_async(state_delta=...)` (parametro real
de `Runner`, confirmado por introspeccion) — en turnos con `intent != "knowledge"` se limpia
explicitamente a `""`, replicando que `optimized_context` se reconstruye desde cero cada
turno en el sistema real (sin este cuidado, el conocimiento de una pregunta de FAQ se
filtraria a un turno posterior no relacionado de otro agente, dentro de la misma sesion).

**Verificado:** `test_sintel_rag_adapter.py` (3/3, sin Ollama): union/truncado real de
chunks, marcador de gobernanza exacto cuando no hay resultados, degradacion con gracia si
Django no responde. `test_sintel_root_workflow.py` (+3 tests): el contexto recuperado
(mockeado en el unico punto de red real) queda sembrado en el state de la sesion de ADK; con
**Ollama real**, la respuesta del LLM queda basada en el hecho inyectado (horario 7:00am-
4:30pm), regresion directa del incidente real de Fase 17; y el contexto NO sobrevive a un
turno posterior de otro intent en la misma sesion (verificado leyendo el state despues).
54/54 tests pasando en `adk_poc/`.

**Gotcha real de mocking encontrado (no un bug del adapter):** mockear
`retrievers.httpx.AsyncClient` rompe cualquier test que en el MISMO turno tambien haga una
llamada real a Ollama — `retrievers.py` hace `import httpx` (no `from httpx import
AsyncClient`), asi que `retrievers.httpx` ES el modulo `httpx` compartido globalmente;
parchear `AsyncClient` ahi lo parcha para TODO el proceso, incluyendo el `httpx.AsyncClient`
interno de litellm, y el turno explota al hablar con Ollama. Fix: mockear
`retrievers.retrieve_knowledge_for_chat` directo (la funcion real, no su transporte) en
cualquier test que combine RAG + un LLM real en el mismo turno.

**Pendiente heredado (sin cambios):** el resto del contrato de `ChatResponse` (`tool_calls`,
`needs_confirmation`, `metrics`) sigue sin replicarse (ADK-10). El flujo de RESUME tras
confirmacion real sigue sin probarse (ADK-02). El fix de `JSON_SCHEMA_FOR_FUNC_DECL` sigue
sin verificarse contra LM Studio (ADK-01).

## 8sexies. ADK-07 — Knowledge Graph adapter (completado)

Regla dura del plan (seccion 7): reusar `graph_sdk` via `ai_editor.graph_client` — UNICA
frontera oficial hacia `project_knowledge_graph` (regla ya existente, verificada por AST en
los tests reales de `ai_editor`), nunca serializar el grafo completo al LLM. Confirmado en
vivo: las 16 operaciones reales de `graph_client` ya devuelven dicts/lists ACOTADOS (un
nodo, un vecindario, un resumen de una sola app) — ninguna serializa los 9575 nodos/20335
aristas reales del grafo completo (`get_graph_status()` real, contra el grafo YA construido
y poblado del repo).

**HALLAZGO REAL IMPORTANTE — cambia el alcance de ADK-09/10/11, no solo de ADK-07:**
`ai_editor.agent.run_autonomous_change_loop(request, policy=None, intent=None)` **ya existe**
como orquestador real, completo, end-to-end (FASE 51-53, plan "AI Change Proposal Engine",
2026-08-11) — compone `intent/interpret_request()` -> `resolver/resolve_change_context()` ->
`planner/build_change_plan()`+`validate_plan()` -> `generation/generate_with_retry()` ->
`generation/run_sandbox_validation_loop()` -> checks de calidad/arquitectura/dependencias/
contratos/tests/documentacion -> `APPROVAL_REQUIRED`. La regla de seguridad esta garantizada
**estructuralmente, por ausencia de import**: `ai_editor.agent` NUNCA importa
`generation.promotion` ni `repository.promote` — promover exige una llamada SEPARADA,
humana, `generation.promotion.review_and_promote()`, fuera de este paquete.

Esto contradice la lectura inicial de ADK-00 (que `intent/`/`resolver/`/`planner/` seguian
siendo "stubs documentales" — literal del docstring de `graph_client/__init__.py`, escrito
en una fase anterior a FASE 51 y nunca actualizado). **Implicacion real para ADK-09/10/11:
el rol de ADK para `ai_editor` NO deberia ser reimplementar el pipeline como Tools ADK
sueltas que llamen a `graph_client` una por una para planificar un cambio — deberia ser un
wrapper delgado alrededor de `run_autonomous_change_loop()` ya existente** (sesion/eventos/
streaming hacia un chat, HITL real sobre el resultado `APPROVAL_REQUIRED`), para no duplicar
una orquestacion ya construida y con su propia regla de seguridad estructural. Revisar este
hallazgo ANTES de escribir codigo de ADK-09.

**Alcance real ejecutado en ADK-07:** un adapter (`sintel_graph_adapter.py`) para un caso de
uso MAS LIGERO y distinto — preguntas de ingenieria ad-hoc ("que modelos tiene la app X",
"que impacto tiene cambiar Y"), pensado para un futuro `EngineeringAgent` (mencionado en la
arquitectura propuesta por el usuario, seccion 3 del plan; NO es un perfil real hoy, a
diferencia de los 9 Support Agent profiles de ADK-04/05). Subconjunto deliberado de 9
operaciones de solo lectura (`find_symbol`, `find_file`, `find_endpoint`, `find_consumers`,
`trace_data_flow`, `find_tests`, `calculate_impact`, `get_app_summary`, `get_graph_status`) —
excluye a proposito `resolve_change`/`build_change_plan` (pipeline de PROPUESTA de cambio, ya
cubierto por `run_autonomous_change_loop`).

**Bug de naming real encontrado (no un problema de logica):** el `__name__` propio de la
funcion real de `graph_sdk` no siempre coincide con el alias que `graph_client` exporta —
`calculate_impact.__name__ == "calculate_change_impact"`,
`get_graph_status.__name__ == "latest_snapshot"` (alias de import, Python no renombra
`__name__`). Sin normalizar esto, el LLM veria nombres de tool distintos a los documentados
en este audit. Fix: wrapper delgado que fija `__name__`/`__doc__`/`__signature__` al nombre
canonico de `graph_client`, sin mutar la funcion real (evita parchear `ai_editor` desde el
POC) y sin cambiar comportamiento (delega sin logica nueva).

**Verificado, todo contra el grafo REAL (sin mocks — solo lectura, cero riesgo de
escritura):** `test_sintel_graph_adapter.py` (5/5) — nombres normalizados correctos;
`resolve_change`/`build_change_plan` rechazados por el subconjunto de solo lectura;
`calculate_impact("Order")` resuelve el modelo real `orders/models.py`; `get_graph_status()`
confirma en vivo que ninguna respuesta serializa el grafo completo; y, con **Ollama real**,
un `EngineeringAgent` de prueba responde "que modelos tiene la app orders" citando
correctamente los 11 modelos reales (`ShippingAddress`, `Coupon`, `Order`, etc.) sin
alucinar. 58/59 tests pasando en `adk_poc/` (el unico fallo es el flake pre-existente de
ADK-01, no relacionado).

`ai_editor`/`project_knowledge_graph` importan limpio en el venv aislado de `adk_poc/` sin
Django instalado ni configurado — confirma que el grafo es un sistema file-based,
desacoplado del ORM (consistente con su naturaleza de conocimiento ESTRUCTURAL, no runtime).

**Pendiente heredado (sin cambios):** el resto del contrato de `ChatResponse` sigue sin
replicarse (ADK-10). El flujo de RESUME tras confirmacion real sigue sin probarse (ADK-02).
El fix de `JSON_SCHEMA_FOR_FUNC_DECL` sigue sin verificarse contra LM Studio (ADK-01).

## 9. Estado de este documento

ADK-00 + ADK-01 + ADK-02 + ADK-03 + ADK-04 + ADK-05 + ADK-06 + ADK-07 completos. Todo el
codigo sigue aislado en `adk_poc/`, sin tocar `ai_engine`/`ai_editor`/Django/Docker — ningun
cambio de este documento modifico produccion. Usuario autorizo continuar sin pausa entre
fases ("continua hasta terminar la instruccion anterior", 2026-09-14) — siguiente: ADK-08
(Session/state — mapear estado persistente vs efimero antes de decidir que va donde).
