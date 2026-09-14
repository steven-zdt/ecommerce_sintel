# Auditoría ai_engine — Support Agent vs Code Engineering

> Fase 2 del `PLAN_DE_EJECUCION_SUPPORT_AGENT`. Clasifica cada componente real de
> `ecommerce_sintel/ai_engine/` (no la lista de ejemplo del plan — se verificó contra el
> código: imports trazados, endpoints leídos) como `SUPPORT_KEEP`, `SUPPORT_MOVE`,
> `SUPPORT_REFACTOR`, `ENGINEERING_SEPARATE`, `DEPRECATE` o `DELETE`. No se elimina ni
> mueve nada en esta fase — solo se clasifica y se documenta evidencia.

Método: para cada módulo se leyeron sus imports (`grep "^import\|^from"`) y, cuando hacía
falta, quién lo importa a él, para confirmar si está realmente en el camino de ejecución
de `/chat` (`action_graph.py` y lo que éste importa transitivamente) o del camino de
generación de código (`/generate`, `/plan`, `/impact`, `/breakage`, `/refresh`, `auditor.py`).

---

## 1. Hallazgo principal: la separación de código YA es casi total

`action_graph.py` (el grafo que sirve `/chat`) importa: `config`, `redis_checkpointer`,
`tools`, `agents`, `auth`, `capabilities`, `observability`, `retrievers`. **No** importa
`chains.py`, `chains_frontend.py`, `graph.py`, `guardrails*.py`, `planner.py`,
`auditor.py`, `project_map.py`, `knowledge_graph.py`, ni `dependency_graph.py`. La regla
de dependencia de `AI_SUPPORT_SCOPE.md` seccion 4 **ya se cumple hoy en el código**, no es
solo una aspiración. El acoplamiento real está en:

- **`retrievers.py`** — importado tanto por `action_graph.py` (RAG de `/chat`) como por
  `chains.py`/`chains_frontend.py` (RAG de generación de código). Mismo módulo, mismo
  `Chroma` vectorstore, misma colección (`CHROMA_COLLECTION_NAME`).
- **`bootstrap.py`** — la ingesta que llena esa colección sigue indexando **ambos**
  `DOCS_SPECS_PATH` (specs/docs) y `CODEBASE_PATH` (código fuente completo) juntos, en el
  mismo store — eso es correcto, `chains.py` necesita ver código real para generar código
  consistente. **[Corregido 2026-08-08]** Lo que sí incumplía la regla de Fase 6 era la
  *consulta* del lado `/chat`: `node_retrieve_knowledge` usaba `retrieve_context_for_task`
  sin filtrar, devolviendo código fuente y un bloque fijo de "reglas globales de
  arquitectura backend" en cada respuesta a un cliente. Se agregó
  `retrieve_knowledge_for_chat` (`retrievers.py`), que filtra por
  `metadata.language == "markdown"` (excluye python/vue/javascript) y no inyecta el
  bloque de reglas internas; `node_retrieve_knowledge` ahora la usa en vez de
  `retrieve_context_for_task`, que queda intacta para `chains.py`/`chains_frontend.py`.
  No se tocó `bootstrap.py`/`loaders.py`/`splitters.py` — el filtro correcto vive en la
  consulta, no en la ingesta, porque la misma colección sirve legítimamente a dos
  consumidores con necesidades distintas.
- **Infra compartida de proceso**: `main.py` (un solo FastAPI, puerto 8100),
  `config.py`, `embeddings_factory.py`, `vectorstore_factory.py`, `llm_factory.py`,
  `requirements.txt`, `Dockerfile` — todos sirven a ambos mundos porque hoy es un solo
  deployable.

Estos son los puntos que Fase 17 (separación física) tiene que resolver realmente; todo
lo demás ya está separado a nivel de imports.

---

## 2. Camino de ejecución de `/chat` (verificado por imports transitivos)

```text
main.py -> action_graph.run_action_chat
              -> config, redis_checkpointer, auth
              -> tools (registry + metadata + http_bridge + *_tools.py)
              -> agents (AgentRegistry -> profiles/*.yaml)
              -> capabilities (CapabilityRegistry)
              -> observability (TurnMetrics)
              -> retrievers (retrieve_context_for_task)   <- unico punto compartido con code-gen
gateway/router.py -> tools, auth, capabilities, config     (mismo Tool/Capability Registry)
```

## 3. Camino de ejecución de generación de código (verificado)

```text
main.py -> graph.run_code_generation, chains.py, chains_frontend.py
              -> retrievers (mismo modulo que /chat)
planner.py -> project_map, dependency_graph, memory_builder
auditor.py -> (construye PROJECT_MAP.json; en el proceso importa dinamicamente
               graph_validator, graph_visualizer)
knowledge_graph.py -> (importa dinamicamente documentation_graph, docker_graph, agent_graph)
main.py endpoints /search,/indices -> specialized_retrieval.py
main.py endpoints /memory,/manifest,/refresh,/ingest -> memory_builder, ai_manifest,
                                                          incremental_updater
```

Ninguno de estos módulos es importado, directa ni indirectamente, por `action_graph.py`,
`tools/`, `capabilities/`, `agents/` o `gateway/`. Confirmado por grep exhaustivo.

---

## 4. Tabla de clasificación

> **[CORREGIDO, Fase 20 "Limpieza Documental", 2026-08-10]** Esta tabla es un snapshot de
> clasificación de 2026-08-08 ("dónde vive cada modulo hoy y a qué mundo pertenece
> conceptualmente"). Desde entonces, la Fase 0 del rediseno "Site Knowledge Graph / AI Editor
> Runtime" (2026-08-10) **eliminó físicamente** 9 de los archivos clasificados abajo como
> `ENGINEERING_SEPARATE` (`project_map.py`, `knowledge_graph.py`, `dependency_graph.py`,
> `auditor.py`, `agent_graph.py`, `docker_graph.py`, `documentation_graph.py`,
> `graph_validator.py`, `graph_visualizer.py`) — ya no existen en `ai_engine/` en absoluto, no
> solo "separados conceptualmente". Y la fila de `tools/graph_tools.py` de abajo (marcada
> "SUPPORT_KEEP, excepción documentada") también fue eliminada por completo, cerrando esa
> excepción (ver `AI_SUPPORT_SCOPE.md` sección 4bis, ya corregida). Se deja la tabla original sin
> reescribir por valor histórico (documenta correctamente el estado de esa fecha), pero para el
> estado ACTUAL de qué existe en `ai_engine/` ver `FLIJO_COMPLETO_IA_ENGINE.md` sección 2 y
> `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`.

| Componente | Clasificación | Evidencia |
|---|---|---|
| `main.py` | **SHARED_PROCESS** (no es SUPPORT ni ENGINEERING puro — monta ambos routers) | Único FastAPI; a separar en Fase 17 |
| `config.py` | SUPPORT_KEEP | Config compartida, ambos mundos la necesitan; no acoplamiento de lógica |
| `auth.py` | SUPPORT_KEEP | Solo lo importa `action_graph.py` y `gateway/router.py` |
| `action_graph.py` | SUPPORT_KEEP | Es el grafo de `/chat` |
| `agents/` (Agent Registry + `profiles/*.yaml`) | SUPPORT_KEEP | Solo lo importa `action_graph.py` |
| `capabilities/` | SUPPORT_KEEP | Solo lo importan `action_graph.py` y `gateway/router.py` |
| `tools/` (registry, metadata, http_bridge) y todos los `*_tools.py` **excepto `graph_tools.py`** | SUPPORT_KEEP | Solo lo importan `action_graph.py` y `gateway/router.py` |
| `tools/graph_tools.py` | **SUPPORT_KEEP (excepción documentada)** | Importa `dependency_graph.build_impact_analysis_text/what_breaks_if_i_change` y `knowledge_graph.find_node_context` directamente — único import de módulos `ENGINEERING_SEPARATE` dentro de todo `tools/`. Registrado como capability `analizar_impacto_arquitectura` -> `GraphImpactAnalysisTool`, ruteado por el intent `architecture_impact` al `AdminAgent` (`agents/profiles/admin_agent.yaml`, agregado 2026-08-04 per `AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`). Solo lectura, `IsAdminUser`. **Decisión del usuario 2026-08-08**: aceptado como única excepción deliberada — ver `AI_SUPPORT_SCOPE.md` seccion 4bis. No usar como precedente para nuevas dependencias de código-gen en `/chat`. |
| `gateway/` | SUPPORT_KEEP | AI Gateway, `/api/v1/ai/*` |
| `observability.py` | SUPPORT_KEEP | Solo lo importa `action_graph.py` |
| `redis_checkpointer.py` | SUPPORT_KEEP | Solo lo importa `action_graph.py` |
| `retrievers.py` | SUPPORT_KEEP (compartido a propósito) | Compartido con `chains.py`/`chains_frontend.py`; `/chat` usa `retrieve_knowledge_for_chat` (filtrada), code-gen usa `retrieve_context_for_task` (sin filtrar) — mismo módulo, dos funciones separadas. **Corregido 2026-08-08**, ver Hallazgo 1 |
| `llm_factory.py` | SUPPORT_REFACTOR | Ya marcado así en el plan original — pasar de "LLM_PROVIDER" a concepto "Inference Gateway" (Fase 12) sin romper `LOCAL_MODEL_CHAIN` |
| `embeddings_factory.py` | SUPPORT_KEEP (compartido, sin lógica de negocio propia) | Usado por `bootstrap.py` y por el vectorstore que ambos mundos consultan |
| `vectorstore_factory.py` | SUPPORT_KEEP (compartido, sin lógica de negocio propia) | Idem |
| `bootstrap.py` | SUPPORT_KEEP (compartido a propósito) | Sigue ingestando código fuente (`CODEBASE_PATH`) junto con docs — correcto, `chains.py` lo necesita; el filtro para `/chat` se resolvió en la consulta (`retrievers.py`), no en la ingesta |
| `loaders.py` | SUPPORT_KEEP (compartido a propósito) | Etiqueta cada doc con `metadata.language` (markdown/python/vue/javascript) — esa etiqueta es justamente lo que permite filtrar en la consulta |
| `splitters.py` | SUPPORT_KEEP (compartido a propósito) | Sin cambios, no participaba del hallazgo |
| `chains.py` | ENGINEERING_SEPARATE | Genera código backend; no lo importa nada del camino `/chat` |
| `chains_frontend.py` | ENGINEERING_SEPARATE | Genera código Vue; idem |
| `graph.py` | ENGINEERING_SEPARATE | `run_code_generation`, workflow de `/generate` |
| `guardrails.py` | ENGINEERING_SEPARATE | Reglas arquitectura backend para código generado |
| `guardrails_frontend.py` | ENGINEERING_SEPARATE | Idem frontend |
| `planner.py` | ENGINEERING_SEPARATE | Importa `project_map`, `dependency_graph`, `memory_builder` |
| `auditor.py` | ENGINEERING_SEPARATE | Genera `PROJECT_MAP.json`; importa dinámicamente `graph_validator`/`graph_visualizer` |
| `project_map.py` | ENGINEERING_SEPARATE | Solo lo usan `main.py` (endpoints `/impact`,`/plan`) y `planner.py` |
| `knowledge_graph.py` | ENGINEERING_SEPARATE | Importa dinámicamente `documentation_graph`/`docker_graph`/`agent_graph` |
| `dependency_graph.py` | ENGINEERING_SEPARATE | Blast-radius de código, usado por `/breakage`,`/impact`,`planner.py` |
| `agent_graph.py` (Graphify) | ENGINEERING_SEPARATE | Solo lo importa `knowledge_graph.py`; **no confundir con `agents/`** (Agent Registry del Support Agent) — nombre ambiguo, ver seccion 5 |
| `docker_graph.py` | ENGINEERING_SEPARATE | Solo lo importa `knowledge_graph.py` |
| `documentation_graph.py` | ENGINEERING_SEPARATE | Solo lo importan `knowledge_graph.py` y `main.py` (`/refresh`) |
| `graph_validator.py` | ENGINEERING_SEPARATE | Solo lo importan `auditor.py` y `main.py` (`/refresh`, gobernanza) |
| `graph_visualizer.py` | ENGINEERING_SEPARATE | Solo lo importa `auditor.py` |
| `incremental_updater.py` | ENGINEERING_SEPARATE | Solo lo importa `main.py` (`/refresh`, `/refresh/detect`) |
| `ai_manifest.py` | ENGINEERING_SEPARATE | Solo lo importan `main.py` (`/manifest`) y `auditor.py` |
| `memory_builder.py` | ENGINEERING_SEPARATE | Solo lo importan `planner.py` y `main.py` (`/memory`) — **no** `action_graph.py` |
| `specialized_retrieval.py` | ENGINEERING_SEPARATE | Solo lo importa `main.py` (`/search`,`/indices`) |
| `PROJECT_MAP.json`, `KNOWLEDGE_GRAPH.json`, `DEPENDENCY_GRAPH.json`, `GLOBAL_MEMORY.json`, `MASTER_MANIFEST.json`, `AI_MANIFESTS/*`, `APP_MEMORY/*`, `GRAPH_VALIDATION_REPORT.json`, `GRAPH_VIEW.html`, `.file_hashes.json` | ENGINEERING_SEPARATE | Todos generados por el pipeline de `auditor.py` |
| `Dockerfile` | SHARED_PROCESS (a resolver en Fase 17) | Hornea todo `ai_engine/` en una sola imagen |
| `requirements.txt` | SHARED_PROCESS (a resolver en Fase 17) | Un solo set de dependencias para ambos mundos |
| `e2e_http/e2e_support_ai_chat_test.ps1` | SUPPORT_KEEP | Prueba `/health` + `/chat` real |
| `e2e_http/e2e_accounts_users_test.ps1` | **FUERA DE ALCANCE ai_engine** | Prueba Django accounts directo por HTTP, no toca `ai_engine` en absoluto — parqueado aquí por convención de carpeta, no por dependencia real |
| `e2e_http/e2e_home_config_test.ps1` | FUERA DE ALCANCE ai_engine | Idem, prueba `core` home config |
| `e2e_http/e2e_rental_http_test.ps1` | FUERA DE ALCANCE ai_engine | Idem, prueba `renting`/`operations` |
| `e2e_ui/` (Playwright) | FUERA DE ALCANCE ai_engine | Prueba UI de `home_config`, no invoca `ai_engine` |
| `.AGENT/` (docs) | SUPPORT_KEEP + ENGINEERING_SEPARATE (mixto por diseño) | Documenta ambos mundos hoy; a partir de Fase 3 los docs nuevos de soporte van aquí, ver `AI_SUPPORT_SCOPE.md` |

## 5. Riesgo de nombres ambiguos

`agent_graph.py` (Graphify, `ENGINEERING_SEPARATE`, estructura arquitectura como grafo) y
`agents/` (Agent Registry, `SUPPORT_KEEP`, carga `profiles/*.yaml` de dominio) tienen
nombres casi idénticos pero pertenecen a mundos opuestos. Cualquier refactor de Fase 17
debe renombrar uno de los dos primero (sugerido: `agent_graph.py` -> algo como
`architecture_agent_graph.py`) para que un import accidental sea imposible de pasar
desapercibido en code review.

## 6. [2026-08-08] Hallazgo mayor: `action_graph.py` no es un Support Agent, es una plataforma de 9 agentes

Al auditar Intent Detection y Agent Registry para el Bloque 3 se descubrió que
`AgentRegistry` (`agents/__init__.py`) enruta hoy entre **9 Agent Profiles**, no uno:

| Agent Profile | Intents que atiende |
|---|---|
| `SupportAgent` | `support`, `rental_change`, `unknown` |
| `AccountAgent` | `kyc`, `kyc_upgrade` |
| `AdminAgent` | `core_content`, `maintenance_check`, `architecture_impact` |
| `MarketingAgent` | `marketing_admin`, `personal_recommendation` |
| `OrderAgent` | `order_status` |
| `PaymentAgent` | `payment` |
| `RentalAgent` | `rental_status`, `renting_search`, `rental_cancel`, `stock` |
| `SalesAgent` | `promos`, `quote`, `knowledge` |
| `ServiceAgent` | `service_status` |

Esto contradice la premisa de `AI_SUPPORT_SCOPE.md` seccion 1 ("el AI Agent tendrá, por
ahora, una única responsabilidad: Support Agent") y la seccion final del plan general
("REGLA ARQUITECTÓNICA FINAL", que proyecta Sales/Marketing/Admin Agent como trabajo
**futuro**, posterior a certificar solo Support Agent). En el código, ese futuro ya pasó:
`AdminAgent` y `MarketingAgent` ya están implementados, registrados y ruteando tráfico
real de `/chat` hoy.

Consecuencia directa: el hallazgo de la seccion anterior (`tools/graph_tools.py`
importando `dependency_graph.py`/`knowledge_graph.py`) no es un descuido aislado — es
`AdminAgent` exponiendo deliberadamente una capability de analisis de arquitectura
(`analizar_impacto_arquitectura`) a usuarios `IsAdminUser` vía el mismo `/chat` que sirve
a clientes. Fue una decision consciente tomada el 2026-08-04 (antes de que existiera este
plan de scope-freeze), documentada en
`AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`.

**Esto no se resuelve solo con documentación — es una decisión de producto/arquitectura
que le corresponde al usuario, no a esta auditoría.** Las opciones son, en resumen:

1. Redefinir el alcance: lo que este plan llama "Support Agent" es en realidad la
   plataforma completa de 9 Agent Profiles (Support + Sales + Rental + Account + Payment +
   Order + Service + Admin + Marketing), y `AI_SUPPORT_SCOPE.md` seccion 1 debe reescribirse
   para reflejarlo — en cuyo caso `architecture_impact`/`AdminAgent` sigue siendo una
   excepción a documentar (single capability de solo lectura hacia el Knowledge Graph),
   pero el resto de los 8 agentes quedan `SUPPORT_KEEP` sin cambios.
2. Mantener el alcance literal de la Fase 0 (solo `SupportAgent`) y sacar los otros 8
   agent profiles + sus intents + sus tools de este proceso, tratándolos como productos
   separados ya adelantados (Sales Agent, Rental Agent, etc.) que deben auditarse aparte.
3. Mantener los 9 agentes como "Support Agent" en sentido amplio, pero remover
   específicamente `architecture_impact`/`AdminAgent`/`graph_tools.py` del camino de
   `/chat` y moverlo a un endpoint HTTP interno separado (p.ej. bajo `/generate`'s mundo),
   ya que es la única capability que de verdad toca el motor de generación de código.

**Decisión del usuario (2026-08-08): opción 1.** Se amplía el alcance formal de
`AI_SUPPORT_SCOPE.md` seccion 1 para reconocer los 9 Agent Profiles como el
`SINTEL SUPPORT AI AGENT`. `architecture_impact`/`AdminAgent`/`graph_tools.py` queda
como única excepción documentada a la regla de dependencia (seccion 4bis del scope), sin
sentar precedente para nuevas dependencias de código-gen en `/chat`. El resto de los 8
Agent Profiles pasan a `SUPPORT_KEEP` sin cambios adicionales. Bloque 3 continúa desde
aquí con esta base.

## 8. Depuración final (Fase 37, PLAN_MAESTRO_SINTEL_AI_SUPPORT, 2026-08-08)

Auditoría de duplicados/no-usados sobre el lado Support del AI Engine:

- **Tools duplicadas**: imposible por construcción — `tools/registry.py::register_tool`
  levanta `ValueError` si el nombre ya existe. Verificado: 0 duplicados.
- **Capabilities duplicadas** (`capability_id` repetido en `capabilities/registry.py`):
  **0 encontrados**.
- **Tools huérfanas** (declaradas en `tools/*.py` pero nunca referenciadas por ninguna
  `Capability.tool_name`): comparé las 30 Tools declaradas contra las 30 referenciadas
  por capabilities — **coinciden exactamente, 0 huérfanas**.
- **Agent Profiles sin uso**: los 9 (`agents/profiles/*.yaml`) están todos registrados
  en `_INTENT_TO_AGENT` y alcanzables desde al menos un intent real — **0 sin uso**.
- **Variables de entorno**: `JWT_SECRET_KEY`, `LLM_MODEL`, `EMBEDDING_PROVIDER`, etc. no
  aparecen en el bloque `environment:` de `docker-compose.yml` para `sintel_ai` — esto
  **no es un hallazgo real**, viven en `.env` (`env_file: .env`), archivo aparte no
  versionado que no se audita por texto plano.

**Resultado: no se encontró nada que depurar.** El lado Support del AI Engine ya está
limpio — ni Tools ni Capabilities ni Agents sin uso. Esto es consistente con el hallazgo
de la seccion 1 (la separación de código entre Support y Engineering ya estaba hecha
antes de empezar esta auditoría) — no había deuda acumulada de este tipo en el lado
Support.

## 7. Qué queda pendiente de Fase 2

- ~~Decidir el tratamiento de `retrievers.py` + `bootstrap.py`~~ — **resuelto 2026-08-08**,
  ver Hallazgo 1 (`retrieve_knowledge_for_chat`).
- Confirmar con el usuario si los 3 scripts E2E "fuera de alcance" se relocalizan en la
  Fase 18 (limpieza) o se dejan donde están.
- Pendiente de verificación manual (no se puede probar en esta sesión sin levantar
  Ollama/ChromaDB/Redis): correr `e2e_http/e2e_support_ai_chat_test.ps1` contra el fix de
  `retrieve_knowledge_for_chat` para confirmar en vivo que `/chat` sigue respondiendo bien
  preguntas de conocimiento (`knowledge` intent) con la colección real, no solo que el
  código compila.
- Este documento reemplaza la tabla de ejemplo del plan original — usar esta tabla, no la
  del plan, como fuente de verdad para Bloque 3+.
