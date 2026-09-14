# Auditoría Enterprise — Knowledge Graph como Single Source of Truth

## Addendum 2 — Respuesta al meta-análisis del prompt de auditoría (2026-08-04, cuarta pasada)

El usuario compartió un meta-análisis (una auditoría del *prompt/brief* usado para esta auditoría,
no del sistema) que puntúa el brief 97/100 como diseño de auditoría y concluye correctamente que
**no se puede validar la afirmación central sin evidencia del sistema en ejecución**, y lista 6
"hallazgos de mejora" que el brief podría cubrir mejor. Esa evidencia de sistema en ejecución es
exactamente lo que ya se ejecutó en los 3 addendums anteriores (lectura de código real, JSON
regenerados y comparados, 9 endpoints probados en vivo, `/chat` probado extremo a extremo con
JWTs reales de un usuario staff y uno no-staff). Repaso punto por punto de los 6 hallazgos,
siendo honesto sobre qué ya tiene evidencia real y qué sigue siendo un hueco genuino:

| # | Hallazgo del meta-análisis | Estado real en esta auditoría |
|---|---|---|
| 1 | Ciclo de actualización (quién/cuándo/trigger/reindexación/invalidación de embeddings) | **Cubierto y corregido** — grafo↔RAG desacoplados (H11), acumulación real medida (5299 vs 4131) y **corregida** (limpieza + reindexado, verificado en vivo) |
| 2 | Calidad semántica (densidad, nodos aislados, centralidad, comunidades, ciclos) | **Cubierto** — densidad 0.001026, 221 nodos aislados (12.1%), componente gigante 82.4%, centralidad por grado, 233 componentes conexas — ver H13. Corrigió además un hallazgo previo impreciso sobre Tools/Agents |
| 3 | Validar consultas reales (API, módulo, función, error, regla de negocio + precisión/tiempo) | **Cubierto, con evidencia** — ver H12. Precisión buena a nivel de clase/entidad, mala a nivel de función individual |
| 4 | Memoria temporal (conversación/proyecto/persistente/episódica/semántica) | **Cubierto en profundidad** — ver H14: conversación (TTL 7 días en Redis, no RAM), semántica (hardcodeada, sin validador de drift), proyecto (dinámica, fresca) |
| 5 | Calidad del Prompt Builder (duplicado/contradictorio/obsoleto/exceso de tokens) | **Cubierto donde es medible** — ver H15: dedup real confirmada en código (con matices), tamaño de contexto medido (7446 caracteres en un caso real), obsolescencia corregida junto con H11. Contradicción adversarial **no evaluada** (requeriría un caso de prueba diseñado a propósito) |
| 6 | ROI del grafo (tiempo, tokens, reutilización, duplicidad documental, precisión) | **Datos reales recopilados, sin línea base comparativa** — ver sección ROI al final. No existe una corrida "sin grafo" del mismo flujo para comparar; se reportan tiempos/tokens reales medidos hoy, marcados explícitamente como no comparativos |

### H11 — El grafo estructural y el RAG vectorial nunca se sincronizan entre sí, y los embeddings se acumulan sin límite

**Evidencia, no interpretación:**
- `main.py::lifespan()` (arranque del contenedor) hace `load_all_documents → split_all` (carga
  chunks en RAM) pero **nunca llama a `vectorstore.add_documents()`** — el arranque nunca
  reingesta a ChromaDB.
- `POST /refresh` (`main.py:411-454`) llama a `update_changed_apps()` (actualiza
  `PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`DEPENDENCY_GRAPH.json`/memoria) y corre
  `graph_validator.py` — **cero líneas tocan `vectorstore`/ChromaDB**.
- `POST /ingest` (`main.py:464-480`) hace `load_all_documents → split_all → vs.add_documents()`
  — **cero líneas tocan `PROJECT_MAP.json`/el grafo**, y `add_documents()` se llama sin borrar ni
  hacer upsert contra lo ya indexado.
- **Medido en vivo ahora mismo:** `/health` reporta `chunks_indexed: 4131` (lo cargado en RAM en
  el arranque actual, la fuente de verdad real), pero el conteo real de la colección de ChromaDB
  en disco es **5299** — 1168 vectores de más, acumulados de ejecuciones anteriores de `/ingest`
  que nunca se limpiaron. Esto no lo causaron los rebuilds de esta sesión (confirmado: el arranque
  no reingesta) — es acumulación histórica preexistente, ahora cuantificada por primera vez.

**Consecuencia real:** cada búsqueda RAG probablemente recupera contenido duplicado y/o obsoleto
mezclado con el actual, degradando precisión y gastando tokens de contexto en repeticiones. Dos
sistemas que deberían ser una sola fuente de verdad (grafo + RAG) tienen ciclos de actualización
completamente independientes, cada uno con su propio "ahora" distinto.

**Corregido (2026-08-04, con confirmación explícita del usuario antes de ejecutar la operación
destructiva):**
1. `client.delete_collection("sintel_kb")` + `client.create_collection("sintel_kb")` — colección
   vaciada, confirmado `count()==0`.
2. **Lección operacional real encontrada al ejecutar esto:** `POST /ingest` falló con 500
   inmediatamente después (`Collection ... does not exist`) — el objeto `Chroma`/cliente vive en
   `_STATE["vectorstore"]` desde el arranque del proceso y cachea el `collection_id` resuelto en
   ese momento; recrear la colección por fuera sin reiniciar el proceso lo deja apuntando a un ID
   que ya no existe. Solución: `docker restart ecommerce_sintel_ai` (reconecta y resuelve el
   nombre a su nuevo ID) — no hace falta rebuild, el código no cambió.
3. `POST /ingest` tras el restart, monitoreado directo contra el conteo de la colección
   (`/api/v2/.../collections/{id}/count`) cada 30s hasta estabilizar.
4. **Resultado medido:** la colección pasó de **5299 → 4131** vectores — **exactamente igual** al
   `chunks_indexed` que reporta `/health`, cero duplicados residuales. `POST /search` reprobado
   después (`"regla de negocio soft delete"` → `BusinessRulesIndex`, 5 resultados) — el RAG sigue
   funcionando correctamente sobre la colección limpia.

### H12 — Búsquedas a nivel de función individual tienen precisión baja (probado en vivo)

Se ejecutaron 4 consultas reales contra `POST /search`: "endpoint de productos shop" (→
`ViewSetIndex`, ~520ms, relevante), "regla de negocio soft delete" (→ `BusinessRulesIndex`,
~485ms, relevante), "funcion calculate_variant_price" y "error IntegrityError carrito" (ambas
enrutadas a `DocumentationIndex`+`ViewSetIndex`+`ModelIndex`, ~490ms, **resultados no
relevantes** — devolvió ViewSets de `accounts`/`users`/`technical_services` sin relación real con
la función buscada). Causa raíz: los 9 índices especializados operan a nivel de clase/entidad
(Model, Serializer, ViewSet, Command, Selector, Service...), no existe un índice a nivel de
función/método individual — una limitación de diseño real, no un bug puntual. Además, aunque
`routed_to` incluyó `DocumentationIndex` en 2 de las 4 consultas, ningún resultado real devuelto
pertenecía a ese índice — coherente con el hallazgo H8 ya reportado (`/indices` no lo cuenta entre
los 9 poblados).

**Recomendación (no aplicada, requiere decisión de diseño):** si se necesita precisión a nivel de
función, haría falta un índice nuevo (`FunctionIndex`/`MethodIndex`) — trabajo de la misma familia
que los 9 existentes, no una corrección de bug.

### H13 — Métricas de densidad/calidad semántica calculadas sobre `KNOWLEDGE_GRAPH.json` real (punto #2 del meta-análisis)

Cálculo directo sobre el grafo actual (1823 nodos, 3407 aristas):

- **Densidad** (dirigida): 0.001026 — esperable para un grafo de dependencias de código real (no
  debería ser denso; un grafo denso aquí significaría acoplamiento excesivo, no calidad).
- **Nodos aislados** (grado 0): 221 de 1823 (**12.1%**), concentrados en `Route` (89 — la mayoría
  de las rutas legítimamente no tienen aristas entrantes/salientes más allá de su propio nodo, no
  es necesariamente un problema), `Documentation` (49), `PiniaStore` (26), `FrontendView` (23),
  `Composable` (22).
- **Componente gigante:** 1503 de 1823 nodos (82.4%) están conectados entre sí — el grafo técnico
  central (Models/Serializers/ViewSets/Endpoints/Apps) es un solo bloque conexo, coherente con el
  hallazgo de acoplamiento fuerte entre apps ya reportado (H5, 19 apps mutuamente acopladas).
- **"Centralidad" por grado** (proxy simple, no eigenvector/betweenness formal): los nodos `App`
  dominan como es esperable (`app:renting` grado=198, `app:dashboard`/`app:technical_services`
  grado=164) — confirma que `renting` y `dashboard` son los puntos de mayor impacto estructural
  del proyecto, dato accionable real para priorizar revisión de riesgo.
- **"Comunidades"** (componentes conexas fuera de la gigante, proxy de comunidades reales sin
  correr Louvain/Leiden): 233 componentes totales. Las más grandes después de la gigante son
  islas coherentes por diseño — `app:frontend` (29 nodos: el App sintético + sus 28 docs, aislado
  porque `frontend` no tiene FKs estructurales hacia las apps Django), `app:ai_engine` (14 nodos),
  y **dos-tres islas de `Tool`+`Agent`** (13, 12 y 9 nodos).

**Corrección a un hallazgo de la auditoría original (H9/Fase 8):** el informe inicial afirmó "sin
arquitectura de agentes/tools/capabilities modelada en el grafo". Es impreciso — **sí existen 30
nodos `Tool` y 9 nodos `Agent`** en `KNOWLEDGE_GRAPH.json`. Lo correcto es: existen como nodos,
pero **aislados en 3 componentes pequeñas separadas del grafo técnico principal** — ninguna arista
conecta "esta Tool consulta este Endpoint/Model real" al resto del grafo. Es un matiz distinto:
no es ausencia de modelado, es modelado sin integrar (Etapa 2 conectó el *flujo de ejecución*
`/chat`→Tool→grafo para `GraphImpactAnalysisTool` específicamente, pero eso no crea una arista
nueva en `KNOWLEDGE_GRAPH.json` — son dos preguntas distintas: "¿la Tool puede consultar el grafo
en runtime?" ahora sí para esa Tool; "¿el grafo sabe que esa Tool existe y qué consulta?" sigue
siendo una isla).

### H14 — Memoria temporal, auditada en profundidad (punto #4 del meta-análisis)

Evidencia real leída directamente del código, no del doc (que estaba desactualizado en un punto
concreto, ver abajo):

| Tipo de memoria | Implementación real | Retención | Hallazgo |
|---|---|---|---|
| **Conversación** (episódica) | `state["history"]`, acumulado por turno (`operator.add` en el `TypedDict` del grafo) | Vive mientras el `thread_id` (`user_id:conversation_id`) no expire | `optimize_context` inyecta solo los últimos `MAX_HISTORY_TURNS=3` turnos al prompt del LLM en cada turno; `node_execute_write` usa `history[-6:]` específicamente al abrir un ticket de soporte con handoff humano (Fase 7) — **no es una inconsistencia**, es intencional: un operador humano recibiendo el handoff necesita más contexto de una vez que el LLM turno a turno |
| **Persistente** (checkpoint) | `RedisCheckpointSaver` (`redis_checkpointer.py`), backend Redis del propio proyecto | **TTL de 7 días** (`CHECKPOINT_TTL_SECONDS`), `expire()` aplicado en cada escritura — conversaciones abandonadas expiran solas | **Documentación desactualizada, corregida (2026-08-04):** `FLIJO_COMPLETO_IA_ENGINE.md` describía el checkpointer como `MemorySaver` (RAM, se perdía en cada reinicio) en sus 2 menciones (líneas 182 y 208) — el código ya lo había migrado a Redis desde el 2026-08-01 (`action_graph.py:712-714`), pero el `.md` de referencia no se había actualizado. Corregido: ambas menciones ahora dicen `RedisCheckpointSaver` + TTL 7 días, con nota explicando el porqué. `PLAN_DE_ACCION_AI_CORE.md` (líneas 663-664, 828) **no se tocó** — ese documento describe legítimamente el estado de una fase histórica anterior a la migración a Redis, no el estado actual |
| **Semántica** (reglas/decisiones de negocio) | `memory_builder.py::GLOBAL_RULES`/`APP_STATIC_KNOWLEDGE` — **diccionarios Python hardcodeados**, "destilados manualmente" de `CLAUDE.md`/`.AGENT.md` en algún momento pasado | No expira, pero tampoco se regenera solo — es texto estático que alguien escribió a mano | Verificado 1 regla al azar (`NO_ROLE_FIELD`) contra el estado real del proyecto — sigue siendo precisa hoy. Pero **no hay ningún validador** (a diferencia de `graph_validator.py` para la documentación de nivel 2) que contraste `GLOBAL_RULES` contra `CLAUDE.md`/`.AGENT.md` reales — mismo riesgo de drift silencioso que el resto de la documentación, sin la red de seguridad que sí existe para los `.md` |
| **De proyecto** (dinámica) | `PROJECT_MAP.json` → `APP_MEMORY/{app}.json`/`GLOBAL_MEMORY.json`, regenerados por `auditor.py` | Tan fresca como la última corrida del auditor (ver H2 original) | Confirmado en vivo: `GLOBAL_MEMORY.json` con `generated_at: 2026-08-04T20:05:25Z` — se regeneró correctamente en las corridas de esta sesión |

### H15 — Calidad del Prompt Builder (punto #5 del meta-análisis)

- **Deduplicación real, confirmada en código** (`retrievers.py:153,213`): `hash(doc.page_content[:200])`
  antes de aplicar `MAX_RETRIEVER_CHUNKS`. Es una heurística barata con dos modos de falla teóricos
  no probados en producción: falso positivo (dos chunks que empiezan igual pero difieren después
  de los primeros 200 caracteres se tratarían como duplicados, descartando contenido único) y falso
  negativo (mismo contenido real con un prefijo distinto en los primeros 200 caracteres no se
  detecta). No se encontró evidencia de que esto haya causado un problema real — es un matiz de
  diseño, no un bug confirmado.
- **Medición real de tamaño de contexto:** `POST /plan` con una tarea real de 3 apps
  ("Agregar descuentos dinamicos al checkout" → `shop`, `orders`, `marketing`) produjo un
  `enriched_context` de 7446 caracteres (~1860 tokens estimados a 4 car./token) — no es excesivo
  para el alcance de la tarea, sin `warnings` reportados por el propio sistema.
- **Contexto contradictorio:** no medido con un caso adversarial diseñado a propósito (requeriría
  construir una tarea donde dos fuentes indexadas digan cosas opuestas y observar si el LLM lo
  nota o elige una sin más) — queda como gap genuino, no evaluado.
- **Contexto obsoleto mezclado con vigente:** este era exactamente el mecanismo que producía H11
  (vectores duplicados/viejos en ChromaDB sin invalidar) — **ya corregido** en este mismo addendum;
  la medición de `/plan` de arriba se hizo *después* de la limpieza, sobre la colección ya sana.

### ROI del grafo — medido donde hay datos reales, marcado como estimación donde no (punto #6 del meta-análisis)

No existe una línea base real "con grafo vs. sin grafo" en este proyecto (nunca se corrió el
mismo flujo dos veces, una vez sin consultar el grafo). Cualquier cifra de "% de mejora" sería
inventada. Lo que sí hay son mediciones reales de esta misma sesión, presentadas como lo que son
— tiempos/tokens reales de tareas reales, no un ROI comparativo:

| Consulta real ejecutada hoy | Tiempo medido | Tokens medidos | Alcance real de la respuesta |
|---|---|---|---|
| `/chat`: "que se rompe si cambio el modelo Product de shop?" | 21111 ms | 1685 in / 237 out | 20 ViewSets, ~50 Serializers, ~50 Models afectados, con archivos reales |
| `/chat`: "quien usa el modelo Equipment de renting?" | ~9-10 s (no registrado exacto) | — | Mismo tipo de análisis para `renting.Equipment` |
| `/chat`: "tienen camaras disponibles?" (intent normal, sin grafo) | 9435 ms | 986 in / 68 out | Búsqueda de catálogo, sin tocar el grafo |
| `/plan`: tarea real de checkout con descuentos | no cronometrado por separado | contexto de 7446 caracteres | Plan de 14 pasos, 3 apps identificadas automáticamente |

**Lo único defendible con esta evidencia:** trazar manualmente "qué ViewSets/Serializers/Models
se ven afectados por cambiar `shop.Product`" revisando 21 apps a mano tomaría, de forma
conservadora, varios minutos de un desarrollador con `grep`/lectura de código — el grafo lo
devuelve en ~9-21 segundos con una lista concreta y verificable (archivos reales, no una
suposición del LLM). Esto **no es una cifra de ROI validada** (no hay medición del proceso manual
equivalente), es una comparación cualitativa razonable a partir de datos reales. Reducción de
tokens, reutilización de conocimiento y duplicidad documental **no se midieron** — quedan como
gap honesto.

---

## Addendum — Correcciones aplicadas (2026-08-04, mismo día)

Tras entregar este informe, se aplicó la Fase 13 (Plan de Corrección) hasta donde era seguro
hacerlo sin decisiones de producto/infraestructura pendientes. Todo lo de abajo está verificado
en vivo, no solo editado — se regeneró el grafo repetidamente tras cada fix, se comparó contra
casos de prueba reales (componentes que se sabía con certeza que estaban vivos o muertos por
verificación directa en navegador de esta misma sesión), y se reconstruyó + redesplegó el
contenedor `ecommerce_sintel_ai` para que el motor en vivo sirva el grafo corregido, no solo el
JSON en disco.

### Etapa 1 (frescura) — hecho
- `python ai_engine/auditor.py` corrido desde el host: los 4 JSON pasaron de 2026-07-31 a
  2026-08-04, reflejando ya todo el trabajo de esta sesión (186 modelos, 151 ViewSets, 135
  endpoints, 518 archivos frontend — vs. 166/131/118/385 del snapshot anterior).
- **Bug real encontrado y corregido en el camino:** `incremental_updater.py::_resolve_base_dir()`
  tenía una copia desactualizada del fix de rutas de `auditor.py` (1 `.parent` en vez de 3),
  resolviendo a un directorio inexistente — por eso `.file_hashes.json` quedaba `{}` en cada
  corrida pese al mensaje "Hash DB initialized". Corregido; ahora trackea 1107 archivos reales.
- `docker compose build sintel_ai && docker compose up -d sintel_ai`: contenedor reconstruido y
  redesplegado (servicio 100% local de desarrollo, sin equivalente en `docker-compose.prod.yml`
  — no toca producción). Verificado en vivo: `/health` → `chunks_indexed: 4131`, `/indices`
  refleja los conteos nuevos.
- **No aplicado (requiere decisión de infraestructura, no de código):** un hook de CI que corra
  el auditor automáticamente en cada cambio, y automatizar el rebuild+redeploy. Hoy no existe
  ningún pipeline de CI en el proyecto al que engancharse — crear uno de cero es una decisión de
  infraestructura que excede "aplicar correcciones de un informe", se deja pendiente y explícito.

### Etapa 3 (hueco de modelo de datos `frontend`) — hecho
- `knowledge_graph.py::_add_apps()` ahora agrega nodos `App` sintéticos para `frontend` y
  `ai_engine` (los dos módulos no-Django que `documentation_graph.py` ya etiquetaba como `app`
  válido en sus docs, pero que nunca tenían nodo `App` real para recibir la arista
  `DOCUMENTED_BY`). **Resultado medido: `orphaned_app_docs` 31 → 0.**

### Etapa 4 (detector de código muerto) — hecho, con hallazgos adicionales en el camino
El hallazgo original (H3) apuntaba a un solo síntoma (`RentalDetailView.vue` no detectado,
`CartOffcanvas.vue` falso positivo). Arreglarlo de verdad requirió encontrar y corregir **6
causas raíz distintas**, todas confirmadas con evidencia antes/después:

1. **Alias de ruta resuelto por nombre crudo, no por archivo real** (`auditor.py`) — dos alias en
   archivos de rutas distintos pueden llamarse igual y apuntar a `.vue` diferentes. Se agregó
   `extract_router_component_aliases()` para resolver cada alias a su archivo real antes de
   comparar.
2. **Archivos de layout nunca escaneados para aristas `USES_COMPONENT`** (`knowledge_graph.py`) —
   `CustomerLayout.vue`/`AppShell.vue` etc. tienen su propia categoría (`Layout`), excluida del
   escaneo; cualquier componente usado *solo* dentro de un layout (`CartOffcanvas.vue`) salía
   como "muerto" pese a estar en producción.
3. **El detector solo escaneaba `FrontendComponent`, nunca `FrontendView`** — una "página" nunca
   podía aparecer como código muerto aunque lo fuera de verdad; esto es lo que ocultaba
   `RentalDetailView.vue`. Extendido a ambos tipos, con `comp_by_name` también indexando Views
   como targets válidos (algunas Views se reusan como sub-componente de otra, ej.
   `RentingDetailContent.vue` dentro de `PublicDetailView.vue`).
4. **El clasificador de "archivo de router" solo reconocía la palabra "router" en el nombre**
   (`auditor.py::VUE_ROLE_PATTERNS`) — las 12 definiciones reales de rutas del proyecto viven en
   `frontend/src/apps/admin/routes/*.routes.js` ("routes", no "router"), así que nunca se
   auditaban como tales y `extract_router_routes()` nunca corría sobre ellas.
5. **El regex de extracción de `name`/`component` por ruta estaba estructuralmente roto** — un
   cuantificador perezoso seguido de grupos opcionales en modo DOTALL resuelve casi siempre a
   "grupo vacío", así que `component` salía `None` para prácticamente cualquier ruta real de
   varias líneas. Reescrito con ventanas de texto acotadas por cada `path:` encontrado.
   Efecto lateral encontrado en el camino: el regex de `path:` con `+` (uno-o-más) tampoco
   matcheaba rutas índice con `path: ''` (string vacío, ej. la ruta "home") — cambiado a `*`.
6. **Los nodos `Route` colisionaban entre árboles de rutas distintos** (`knowledge_graph.py`) —
   el id era solo `frontend:Route:{path}`, y dos routers separados (admin vs público) pueden
   reusar el mismo segmento (`servicios` en `/panel/servicios` y en `/servicios`), pisando
   silenciosamente la resolución correcta. Namespaced por archivo de origen.

**Resultado medido, verificado contra 9 casos de prueba reales (componentes/vistas confirmadas
vivas o muertas por verificación directa en navegador en esta misma sesión):**

| Caso | Antes | Después |
|---|---|---|
| `dead_frontend_components` (total) | 56 | **26** |
| `CartOffcanvas.vue` (vivo, verificado en vivo hoy) | falso positivo (muerto) | correcto (vivo) |
| `RentalDetailView.vue` (muerto, confirmado en vivo hoy) | falso negativo (no detectado) | correcto (muerto) |
| `HomeView.vue`, `ServicesCatalogView.vue`, `PublicDetailView.vue`, `RentingDetailContent.vue`, `ShopDetailContent.vue`, `ServiceDetailContent.vue`, `LoginView.vue`, `DashboardView.vue` (todos vivos) | habrían sido falsos positivos tras extender el escaneo a Views, de no corregirse las 6 causas raíz | correctos (vivos) |

**Hallazgo nuevo, no anticipado en el informe original:** `views/customer/shop/ProductDetailView.vue`
y `views/customer/services/ServiceDetailView.vue` ahora aparecen como código muerto real — el
mismo patrón exacto que `RentalDetailView.vue` (su alias de ruta resuelve en realidad a
`PublicDetailView.vue`, no a sí mismos). Tres archivos duplicados/obsoletos del mismo rediseño de
PDP, no uno solo. No se borraron los archivos — el objetivo de esta pasada fue arreglar el
*detector*, no ejecutar la limpieza (eso es una decisión de producto/scope aparte).

### Etapa 2 (integrar Action Graph con el grafo) — aplicado (2026-08-04, tercera pasada, a pedido explícito del usuario)
El plan original decía "no integrar por integrar" porque era una decisión de arquitectura, no un
bug — el usuario dio esa decisión explícitamente ("aplica etapa 2"). Al investigar para
implementarla se encontraron dos cosas que cambiaron el plan original:

**1. La integración ya existía a medias, y estaba deliberadamente incompleta por una razón
correcta.** `tools/graph_tools.py::GraphImpactAnalysisTool` ya envolvía
`dependency_graph.py`/`knowledge_graph.py`, ya estaba registrada en `capabilities/registry.py`
(`analizar_impacto_arquitectura`) y ya estaba en el scope de `AdminAgent`
(`agents/profiles/admin_agent.yaml`) desde una fase anterior (Fase 9,
`AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md` -- no localizable hoy, ver hallazgo H4, pero su rastro
sí quedó en el código). Un comentario ya explicaba por qué faltaba la única pieza real: nadie
había agregado un patrón de intent en `BUSINESS_INTENT_PATTERNS`/`INTENT_CAPABILITIES`
(`action_graph.py`) — exactamente el mismo argumento de "no tocar el router regex en vivo sin
poder probar contra tráfico real" que ya había razonado esta misma auditoría. Es decir: la
arquitectura recomendada por Etapa 2 ("exponerlo como una Tool más del ToolRegistry, no una
integración ad-hoc") ya estaba construida; solo faltaba conectar el último cable.

**2. Al ir a conectar ese cable, apareció un hallazgo de seguridad real, no anticipado, que había
que corregir primero.** `node_select_and_execute_tools` (el ejecutor de lecturas del flujo normal
de `/chat`) **nunca validaba `metadata.permissions`** — solo lo hacía la rama de escrituras
(`node_evaluate_policy`) y el endpoint de debug (`gateway/router.py`, con un comentario propio que
explica que esa asimetría "no era explotable porque los endpoints internos de Django re-validan
permisos... y son la autoridad final"). Ese razonamiento es correcto para la mayoría de las Tools
(proxean a Django vía `tools/http_bridge.py`) pero **no aplica a `GraphImpactAnalysisTool`**, que
consulta el grafo directo en memoria del proceso, sin HTTP, sin JWT, sin ningún endpoint de Django
detrás que pudiera re-validar nada. Conectar el intent sin corregir esto primero habría hecho
explotable, por primera vez en el proyecto, un permiso `IsAdminUser` declarado pero no aplicado.

**Lo que se hizo, en orden:**
1. `action_graph.py::node_select_and_execute_tools` -- se agregó el mismo chequeo que ya existía
   en `node_evaluate_policy`/`gateway/router.py` (`"IsAdminUser" in metadata.permissions and not
   ctx.user.get("is_staff")` -> rechazo 403), ahora también en la rama de lectura.
2. `action_graph.py::BUSINESS_INTENT_PATTERNS` -- nuevo intent `architecture_impact`, patrón
   deliberadamente angosto (lenguaje de "qué se rompe"/"qué afecta"/"quién usa" sobre una entidad
   de código), probado offline contra frases objetivo y frases de cliente reales antes de
   desplegar (ver tabla de pruebas abajo).
3. `action_graph.py::INTENT_CAPABILITIES["architecture_impact"] = ["analizar_impacto_arquitectura"]`.
   Deliberadamente NO se agregó a `INTENT_FALLBACK_CAPABILITY` (esa capability exige el argumento
   `entidad`; el fallback determinístico del proyecto es solo para lecturas sin argumentos).
4. `agents/profiles/admin_agent.yaml` -- `architecture_impact` agregado a `intents:`, comentario
   actualizado explicando por qué ahora sí es seguro conectarlo.
5. `sintel_ai` reconstruido y redesplegado; los 9 Agent Profiles cargaron sin error de validación
   (`_load_profiles()` valida contra `CapabilityRegistry`/`ToolRegistry` al arrancar).

**Verificado en vivo, extremo a extremo, con JWTs reales de un usuario staff y uno no-staff
(ambos limpiados después, ninguno quedó con estado nuevo en BD -- todo fue de solo lectura):**

| Prueba | Resultado |
|---|---|
| `POST /chat` (usuario **staff**), mensaje "que se rompe si cambio el modelo Product de shop?" | `intent=architecture_impact`, `agent=AdminAgent`, el LLM invocó `analizar_impacto_arquitectura` con `entidad=Product` por su cuenta (function-calling), devolvió el análisis real del grafo (ViewSets/Serializers/Models afectados) y una respuesta en lenguaje natural correcta |
| Mismo mensaje, usuario **no-staff** | `intent=architecture_impact`, `agent=AdminAgent` (el router SÍ lo enruta igual -- el punto es que la Tool en sí se protege), pero `tool_calls: []` y `result: {"error": "Esta accion es solo para administradores.", "status_code": 403}` -- **cero datos del grafo llegaron a un usuario no autorizado** |
| `POST /api/v1/ai/tools/debug` directo (staff) | Funciona, devuelve el mismo análisis real |
| `POST /api/v1/ai/tools/debug` directo (no-staff) | 403 (comportamiento preexistente del endpoint de debug, confirmado que sigue intacto) |

**Riesgo residual, documentado, no oculto:** el patrón regex de `architecture_impact` no se probó
contra tráfico real de clientes (no existe forma de hacerlo sin desplegar a producción) -- se
optó por un patrón angosto y ampliarlo después con evidencia real, en vez de al revés. Si
apareciera un falso positivo real (un cliente cuyo mensaje dispara este intent por accidente), el
peor caso ya está cubierto por el fix de permisos: se le rechaza con un 403 explícito, nunca se le
filtran datos.

### Etapa 5 (referencias de gobernanza rotas) — aplicado parcialmente (2026-08-04, segunda pasada)
Se confirmó que **ni `docs/` ni `AUDITORIA/` existen como directorios en este checkout** (no es
solo que falten 2 archivos puntuales). Sin inventar contenido de reemplazo ni borrar las citas
(para no destruir la pista de qué se perdió), se anotaron las 3 referencias con más peso —
las que un lector (humano o IA) tomaría como verificación real de una afirmación, no solo como
procedencia histórica:
- `CLAUDE.md` (tabla raíz, línea 46) — fila marcada `[ROTO 2026-08-04]` con nota explícita.
- `.AGENT.md` (tabla de servicios externos, líneas 139-140) — mismo tratamiento, sincronizado con
  `CLAUDE.md` como exige su propia regla de consistencia.
- `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` — las 2 citas a `AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md`
  que respaldaban "verificado corriendo"/"verificado con un check de CI" ahora indican
  explícitamente que el archivo no se encontró y la cita no es verificable con el estado actual
  del repo (esto NO afirma que la funcionalidad subyacente sea falsa — solo que esa cita puntual
  no se puede confirmar hoy).

**No tocado deliberadamente:** las citas a `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md` dentro de
comentarios/docstrings de `auditor.py`, `documentation_graph.py` y `graph_validator.py` — ahí
funcionan como procedencia histórica del diseño, no como evidencia de una afirmación puntual;
anotarlas aporta mucho menos valor que las 3 de arriba y no se quiso generar ruido de diff sin
necesidad real.

**Pendiente de decisión humana, sin cambios:** si `AUDITORIA/14_*.md` y `AUDITORIA/16_*.md` deben
recrearse (si alguien tiene el contenido original en otro lugar) o si las citas deben eliminarse
por completo en una pasada posterior.

---

**Fecha:** 2026-08-04
**Alcance:** `ai_engine/` (motor de generación de código + AI Core / Action Graph) y su
integración real con el resto del proyecto (backend Django, frontend Vue, documentación).
**Método:** lectura directa de código fuente (`ai_engine/*.py`), inspección de los JSON
auto-generados (`PROJECT_MAP.json`, `KNOWLEDGE_GRAPH.json`, `DEPENDENCY_GRAPH.json`,
`GRAPH_VALIDATION_REPORT.json`), llamadas en vivo a los endpoints (`/health`, `/indices`) del
contenedor `ecommerce_sintel_ai` (activo, saludable), y búsqueda exhaustiva en disco de los
componentes nombrados en el brief. Todos los hallazgos citan archivo y evidencia verificable.

**Nota metodológica importante:** el brief original pide auditar módulos (BCVOR, VIP, Browser
Engine, OCR, Tracking, Detección, Temporal Memory) que **no existen en este proyecto** — se
buscó exhaustivamente en `ai_engine/` (código, YAML de agentes, JSON generados) y no hay una
sola coincidencia. Este informe los marca explícitamente como **N/A — módulo inexistente** en
vez de inventar hallazgos sobre componentes que no están en el codebase. Inventar contenido
ahí sería precisamente el tipo de "contexto huérfano" que la Fase 4 pide detectar.

---

## Resumen ejecutivo (adelanto — detalle completo en Fase 14)

El proyecto **sí tiene** un Knowledge Graph real, no solo documentado: `ai_engine/knowledge_graph.py`
construye `KNOWLEDGE_GRAPH.json` (1.39 MB, grafo tipado de entidades) a partir de `PROJECT_MAP.json`
(1.26 MB, auto-generado por `auditor.py` auditando 166 modelos / 131 ViewSets / 118 endpoints / 385
archivos frontend). Es funcional, consultable en vivo (`/graph/node/{entity}`, `/graph/impact/{entity}`,
`/manifest/{app}`) y alimenta el nodo `analyze_impact` del flujo de **generación de código**
(`/generate`, `/plan`, `/impact`).

Pero **no es la fuente única de verdad del ecosistema** en el sentido que pide el brief. Evidencia
directa, no interpretación:

1. **El flujo de negocio real (`/chat`, `action_graph.py` — lo que atiende a clientes por soporte
   web y WhatsApp) tiene cero referencias a `knowledge_graph`, `dependency_graph`, `PROJECT_MAP` o
   `KNOWLEDGE_GRAPH`** (grep exhaustivo, 0 resultados). Ese flujo usa RAG (ChromaDB) + Tools/
   Capabilities + un CRM Context Builder aparte — nunca consulta el grafo.
2. **Los 4 JSON del grafo no se han regenerado desde 2026-07-31** (`stat` de los 4 archivos:
   idéntico timestamp `17:22`). Hoy es 2026-08-04. El propio tracker incremental
   (`.file_hashes.json`) está vacío (`{}`), y el cambio masivo de esta misma sesión (nuevo
   `MediaImage.vue`, `utils/media.js`, refactor de 8+ componentes, cambios de backend en `cart/`,
   default de vista grid en 3 catálogos) **no existe todavía en el grafo**.
3. El propio motor genera un reporte de auto-validación (`GRAPH_VALIDATION_REPORT.json`, también
   de 2026-07-31) que documenta **31 docs huérfanos, 13 documentos obsoletos, 56 componentes
   frontend marcados "muertos" y 18 conteos contradictorios entre documentación y grafo** — y ese
   detector tiene tanto falsos positivos (`CartOffcanvas.vue`, activamente usado y verificado en
   vivo hoy mismo, aparece en la lista de "muertos") como falsos negativos (`RentalDetailView.vue`,
   que **sí** es código muerto real descubierto en esta misma sesión, no aparece en la lista).
4. Ni un solo módulo de negocio (`shop`, `renting`, `cart`, `quotes`, `support`...) **escribe** en
   el grafo. Es una fotografía unidireccional (código → análisis estático → JSON), regenerada
   manualmente, nunca al revés.
5. Documentos citados como evidencia por el propio `ai_engine` (`AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md`,
   `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`) **no existen en este checkout**, igual que dos
   archivos referenciados por el `CLAUDE.md` raíz del proyecto (`docs/.AGENT/GUIA_AI_ENGINE.md`,
   `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md`).

**Conclusión en una frase:** el grafo es una herramienta de **impact analysis para generación de
código** (real, funcional, útil dentro de ese alcance) — no un mecanismo de gobierno de contexto
consultado antes de cada respuesta de IA en todo el ecosistema. Convertirlo en eso es un proyecto
de ingeniería identificable y acotado (Fase 13), no un ajuste menor.

---

## FASE 1 — Auditoría de Existencia del Grafo

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| ¿Existe realmente? | **Sí** | `ai_engine/knowledge_graph.py` (código real, no stub) + `KNOWLEDGE_GRAPH.json` (1.39 MB) |
| ¿Está implementado? | **Sí, parcialmente** | Construido desde `PROJECT_MAP.json`; expone `GET /graph/node/{entity}`, `GET /graph/impact/{entity}` |
| ¿Es funcional? | **Sí, dentro de un alcance acotado** | `/health` responde `200` en vivo hoy (`chunks_indexed: 4132`); `analyze_impact` es el nodo 1 real del LangGraph de generación de código (`graph.py`) |
| ¿Es parcial? | **Sí** | Cubre entidades de código (Model/Serializer/ViewSet/endpoint/Vue file) vía `documentation_graph.py`, agrega nodos `Documentation` — pero **no** cubre decisiones de negocio, incidentes, memoria conversacional ni el flujo `/chat` |
| ¿Es solo documentación? | **No** | Es JSON real, generado por AST/regex sobre el código, no prosa |
| ¿Está siendo utilizado? | **Sí, por un subconjunto de flujos** | Usado por `/generate`, `/plan`, `/impact`, `/breakage` (generación de código) y por `documentation_graph.py`. **No** usado por `/chat` (acción de negocio real) |

**Modelo de datos:** `App` (nodo), `Model`/`Serializer`/`ViewSet`/`Endpoint`/`FrontendFile`/`Store`
(nodos), `Documentation` (nodo, agregado en una fase posterior — ver `documentation_graph.py:1-11`,
que cita explícitamente su propio origen como "Fase 2 de `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`").
Aristas: `endpoint_to_viewset`, `model_to_viewset`, `frontend_to_endpoint`, `store_to_endpoint`,
`DOCUMENTED_BY` (App → Documentation).

**Versionado / trazabilidad:** ninguno formal. No hay historial de versiones del grafo, no hay
diff entre generaciones, no hay changelog — cada `python ai_engine/auditor.py` sobreescribe el
JSON anterior sin backup. La única "trazabilidad" es el timestamp del archivo en disco.

**Consistencia:** ver Fase 7 — el propio motor detecta 18 conteos contradictorios entre lo que
documentan los `.AGENT/docs/*.md` y lo que el grafo cuenta realmente (ejemplo real:
`renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` afirma "11 modelos", el grafo cuenta 35).

---

## FASE 2 — Auditoría de Integración por Módulo

| Módulo | Consume el grafo | Escribe información | Actualiza relaciones | Consulta entidades | Reutiliza contexto | Sincronización |
|---|---|---|---|---|---|---|
| **Frontend (Vue)** | No directamente — es *objeto* del grafo (`FrontendFile`/`Store` nodos), no *consumidor* en runtime | No | No | No | No | Regenerado solo cuando corre `auditor.py` desde el host |
| **Backend (Django, todas las apps)** | No en runtime — son *objeto* de análisis estático | No | No | No | No | Idem |
| **AI Engine — generación de código** (`/generate`,`/plan`,`/impact`,`/breakage`) | **Sí** | No (solo lee) | No | **Sí**, vía `project_map.py`/`dependency_graph.py` | **Sí**, `impact_context` se inyecta al prompt | Manual (`python ai_engine/auditor.py` + rebuild de imagen) |
| **RAG (ChromaDB + retrievers.py)** | No — es un índice vectorial independiente sobre chunks de texto (código+docs), no consulta el grafo tipado | No | No | No | Parcialmente — comparte las mismas fuentes de documentos, pero por indexación de texto, no por relaciones de grafo | `POST /ingest` manual |
| **BCVOR** | **N/A — módulo inexistente** (0 coincidencias en todo `ai_engine/`) | — | — | — | — | — |
| **VIP** | **N/A — módulo inexistente** | — | — | — | — | — |
| **Browser Engine** | **N/A — módulo inexistente** (existe un *browser preview* de la herramienta de desarrollo, no un módulo del proyecto) | — | — | — | — | — |
| **OCR** | **N/A — módulo inexistente** | — | — | — | — | — |
| **Tracking** | Existe `shipmenttrackingevent`/`TrackingEvent` en `users` (rastreo de envíos, dominio de negocio) — no tiene relación con el Knowledge Graph | No | No | No | No | N/A |
| **Detección** | **N/A como módulo propio** — "detección" solo aparece como `detect_task_type`/`detect_apps_from_text` (heurísticas de keywords en `retrievers.py`, no un módulo de visión/IA) | — | — | — | — | — |
| **Agents** (`ai_engine/agents/`, 9 Agent Profiles YAML) | **No consultan el grafo** — su scope viene de `capabilities/registry.py`, no de `KNOWLEDGE_GRAPH.json` | No | No | No | Su "contexto" es el prompt de personalidad del YAML + Capabilities visibles, no el grafo | Se validan al arranque, no versionados aparte |
| **LLM** (Ollama / OpenAI / Anthropic, vía `llm_factory.py`) | Solo indirectamente, cuando `impact_context` se le inyecta en `/generate` | No | No | No | No | N/A |
| **VLM** | **N/A — módulo inexistente** | — | — | — | — | — |
| **Temporal Memory** | Existe `MemorySaver` (checkpointer de LangGraph, últimos 3 turnos de `/chat`) — es memoria conversacional efímera por `thread_id`, **no** el grafo | No | No | No | Solo dentro de la misma conversación | N/A |
| **Notifications** | No | No | No | No | No | N/A |
| **Ecommerce / Shop / Renting / Quotes / Support / Payments / Accounts / Inventario / Servicios Técnicos** | No en runtime — son *objeto* de análisis (sus modelos/serializers/endpoints aparecen como nodos), nunca *consumidores* del grafo en su propia lógica de negocio | No | No | No | No | Se actualizan solo si alguien corre `auditor.py` tras cambiar esas apps |
| **CRM** | No hay app `crm` en el proyecto; existe el "CRM Context Builder" del Action Graph (`optimize_context`, trae marketing profile + direcciones desde `GET /api/v1/internal/ai/customer-context/`, cacheado en Redis TTL 300s) — **usa datos vivos de Postgres/Redis, explícitamente nunca indexados al RAG ni al grafo** (`FLIJO_COMPLETO_IA_ENGINE.md:206`, "Datos vivos jamás se indexan al RAG") | — | — | — | — | — |

**Conclusión Fase 2:** de los ~25 módulos listados en el brief, **8 simplemente no existen en este
proyecto** (BCVOR, VIP, Browser Engine, OCR, Detección como módulo, VLM). De los que sí existen,
**ninguno escribe al grafo** y solo el subsistema de generación de código lo **lee** en runtime. El
resto de "integración" reportable es indirecta: ser objeto de análisis estático, no ser cliente del
grafo.

---

## FASE 3 — Auditoría del Flujo de Prompts

El brief asume un único flujo `Usuario → Prompt → Normalización → Grafo → RAG → LLM → Respuesta`.
**En este proyecto existen DOS flujos de prompt independientes, y solo uno pasa por el grafo:**

### Flujo A — Generación/validación de código (`/generate`, `/plan`, `/impact`)
```
Request → detect_task_type() → node_analyze_impact (CONSULTA EL GRAFO: project_map.py +
  PROJECT_MAP.json) → node_generate_code (retrieve_context_for_task: RAG BM25+MMR) → LLM →
  node_validate_code (guardrails) → [retry con feedback | emit_result | escalate]
```
Aquí sí se cumple el flujo que pide el brief — el grafo se consulta **antes** que el RAG y **antes**
del LLM (`graph.py:528-532`, nodo `analyze_impact` es el primer nodo del `StateGraph`).

### Flujo B — Acción de negocio / chat con clientes (`/chat`, `action_graph.py`) — el que
realmente atiende Support Web y WhatsApp, es decir, el tráfico real de usuarios finales
```
Request → resolve_customer_context → detect_intent → optimize_context (RAG conocimiento +
  CRM Context desde Postgres/Redis — NUNCA el grafo) → select_and_execute_tools |
  retrieve_knowledge → generate_response
```
**Cero pasos de este flujo consultan `knowledge_graph.py`, `dependency_graph.py`,
`PROJECT_MAP.json` ni `KNOWLEDGE_GRAPH.json`** — verificado por grep directo sobre
`action_graph.py` completo (0 coincidencias). El "contexto" de este flujo viene de: (a) RAG
vectorial sobre chunks de documentación/código, (b) Tools que llaman endpoints internos read-only
de Django, (c) el CRM Context Builder (datos vivos, no indexados).

**Respuesta a la pregunta del brief:** sí, hay una etapa que omite el grafo — y es la que importa
para el usuario final. El grafo solo gobierna el flujo interno de generación de código para
desarrollo, no las respuestas que reciben los clientes reales.

---

## FASE 4 — Auditoría del Contexto

| Elemento | ¿Proviene del grafo? | Evidencia |
|---|---|---|
| Documentos (`.AGENT/docs/*.md`) | Indexados al RAG (ChromaDB) directamente, **y también** como nodos `Documentation` en el grafo (doble vía, ver Fase 7 duplicación) | `loaders.py` (RAG) + `documentation_graph.py` (grafo) — dos pipelines paralelos sobre la misma fuente |
| Especificaciones / arquitectura | RAG, vía `ai_skills/frontend/*.md`, `frontend/.AGENT/doc/*.md` | `loaders.py:415-426` |
| Dependencias | **Sí**, del grafo (`DEPENDENCY_GRAPH.json`, blast-radius) | Solo consumido por `/breakage`, `/graph/impact/{entity}` |
| Reglas/configuraciones | **No** del grafo — están hardcodeadas como listas Python en `guardrails.py`/`chains.py` (14 reglas backend, 15 frontend) | `chains.py:565-579` |
| Historial/decisiones | Parcial — `AI_MANIFESTS/*.json` tiene campos `decisions`/`known_issues`/`TODO`/`BUG` extraídos por regex de comentarios en código, no un log real | `.AGENT/FLIJO_COMPLETO_IA_ENGINE.md:391` |
| Incidencias | No hay integración con `security.SecurityEvent` ni con ningún sistema de tickets en el grafo | — |
| Memoria temporal | `MemorySaver` de LangGraph — conversacional, por `thread_id`, no persiste al grafo | `FLIJO_COMPLETO_IA_ENGINE.md:180` |
| Memoria permanente | `GLOBAL_MEMORY.json`/`APP_MEMORY/*.json` — derivados de `PROJECT_MAP.json`, mismo problema de staleness que el grafo (generados en el mismo batch 2026-07-31) | `ls -la` (ver Fase 5) |

**Contexto duplicado detectado:** la documentación se indexa **dos veces** por dos pipelines
independientes que no se coordinan entre sí — RAG (`loaders.py`) y grafo (`documentation_graph.py`)
— cada uno con su propio chunking/metadata, sin una fuente única intermedia.

**Contexto perdido:** `documentation_graph.py:33-40` documenta explícitamente que, cuando corre
**dentro del contenedor** `sintel_ai`, las fuentes cross-app (`AUDITORIA/`, `Documentacion/`,
`docs/.AGENT/`, `ai_engine/.AGENT/`) **no están disponibles** porque no hay volumen que las monte
— solo se ven si el proceso corre desde el host. Esto es una pérdida de contexto silenciosa y
autodocumentada por el propio código, no una inferencia de esta auditoría.

**Contexto huérfano:** 31 documentos declarados en `GRAPH_VALIDATION_REPORT.json` como
`orphaned_app_docs`, con la razón `app_no_existe_como_nodo_App` — **los 31 son de
`frontend/.AGENT/doc/*.md`**. Causa raíz real: el modelo de datos del grafo modela `App` como
"Django app", y `frontend` no es una Django app — es un directorio con su propio árbol de
documentación que el grafo no sabe representar como nodo. No es un problema de documentación
faltante, es un hueco en el modelo de datos (ver Fase 1 y Fase 8).

**Contexto obsoleto:** 13 documentos flagged por el propio `GRAPH_VALIDATION_REPORT.json` como
`stale_documentation` (ejemplo: `shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md` declara fecha
2026-06-11, último commit real del código 2026-07-29 — 48 días de desfase). Ese reporte es
además, él mismo, del 31-07 — desactualizado 4 días adicionales respecto a hoy.

---

## FASE 5 — Auditoría de Sincronización

El flujo ideal que pide el brief (`Documentación → Embeddings → KG → RAG → Motor IA → Prompts →
Respuestas`, con sincronización automática) **no existe como automatización**. Evidencia directa:

```
$ ls -la ai_engine/*.json
PROJECT_MAP.json        2026-07-31 17:22:06
KNOWLEDGE_GRAPH.json    2026-07-31 17:22:07
DEPENDENCY_GRAPH.json   2026-07-31 17:22:07
GLOBAL_MEMORY.json      2026-07-31 17:22:07
GRAPH_VALIDATION_REPORT.json  2026-07-31 17:22 (mismo batch)

$ cat ai_engine/.file_hashes.json
{}
```

- Los 4 artefactos del grafo se regeneraron **una sola vez**, el 2026-07-31, y no desde entonces.
  Hoy es 2026-08-04: **4 días de cambios reales del proyecto no están reflejados**, incluyendo
  todo el trabajo de esta misma sesión (redisño de PDP, `MediaImage.vue`, `utils/media.js`, el fix
  del bug real en `ProductHorizontalCard.vue`, los cambios de backend en `cart/`, el default de
  vista grid en los 3 catálogos).
- `.file_hashes.json` (el tracker que decide qué apps re-auditar incrementalmente) está **vacío**
  — no tiene baseline. Sin baseline, `incremental_updater.py::detect_changed_apps()` no tiene con
  qué comparar de forma confiable.
- **No existe ningún hook, señal post-commit, ni trigger automático** que dispare `/refresh` o
  `python auditor.py` cuando cambia un archivo — la única vía es ejecución manual, y el propio doc
  del motor lo advierte explícitamente: *"No hay ninguna validación de 'frescura' en el startup —
  es responsabilidad de quien despliega correr el auditor antes de reconstruir la imagen"*
  (`FLIJO_COMPLETO_IA_ENGINE.md:141-149`).
- Además, el `Dockerfile` de `sintel_ai` hornea los JSON con `COPY . .` — no son un volumen live.
  Regenerar en el host **no alcanza**; hace falta rebuild + redeploy del contenedor para que el
  motor sirva el grafo actualizado.

**Elemento crítico de gobernanza:** el propio `FLIJO_COMPLETO_IA_ENGINE.md` (que este mismo
`CLAUDE.md` designa como la arquitectura de referencia obligatoria de `ai_engine/`) cita como
evidencia de que "el AI Core ya está en el codebase y verificado corriendo" un archivo
(`AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md`) que **no existe en este checkout** (búsqueda
exhaustiva `find -iname` sobre todo el repo, 0 resultados). Lo mismo aplica a
`AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`, citado como el diseño origen de
`documentation_graph.py`. No se puede verificar esa afirmación con el estado actual del
repositorio — puede ser un artefacto no versionado, o una referencia rota.

---

## FASE 6 — Auditoría del RAG

Estado en vivo (verificado ahora mismo contra el contenedor real, no solo lectura de código):

```
GET /health   → {"status":"ok","chunks_indexed":4132,"vectorstore":"chromadb"}
GET /indices  → {"CommandIndex":91,"SelectorIndex":58,"ServiceIndex":12,"ModelIndex":175,
                  "SerializerIndex":382,"ViewSetIndex":138,"FrontendIndex":450,
                  "DependencyIndex":501,"BusinessRulesIndex":19}
```

- El motor está sano y sirviendo tráfico (RAG operativo, no solo documentado).
- **Discrepancia menor doc-vs-runtime:** `FLIJO_COMPLETO_IA_ENGINE.md:376-381` documenta **10**
  índices especializados, incluyendo `DocumentationIndex`. El endpoint real `/indices` solo
  devuelve **9** — `DocumentationIndex` está ausente de la respuesta en vivo.
- **Recuperación semántica:** ensemble BM25 (35%, k=6, filtrado por app) + ChromaDB MMR (65%,
  k=8, fetch_k=25, λ=0.6), con dedup por hash de los primeros 200 caracteres y límite de 50
  chunks. Diseño razonable y estándar de la industria — no hay forma de medir precisión/recall
  reales sin un dataset de evaluación, que **no existe** en el proyecto (no hay ningún
  `eval_dataset` ni métricas de retrieval registradas).
- **¿El grafo mejora la recuperación del RAG?** No directamente. Son dos sistemas paralelos que
  comparten fuente (los mismos `.md`/`.py`) pero no se retroalimentan: el RAG no usa las
  relaciones del grafo para expandir o re-rankear resultados, y el grafo no usa embeddings para
  nada. La única intersección real es `impact_context` (texto plano generado desde
  `PROJECT_MAP.json`), que se concatena al final de la tarea antes de pasar por el RAG — un
  puente unidireccional simple, no una fusión de sistemas.

---

## FASE 7 — Auditoría de Relaciones

Evidencia tomada directamente de `GRAPH_VALIDATION_REPORT.json` (auto-generado por el propio
motor, 2026-07-31) — el motor **ya audita esto de sí mismo**, esta fase confirma y contextualiza
sus propios hallazgos:

| Categoría | Cantidad | Ejemplo real |
|---|---|---|
| `orphaned_app_docs` (documentación desconectada) | 31 | Los 31 son 100% de `frontend/.AGENT/doc/*.md` — razón: `app_no_existe_como_nodo_App` |
| `stale_documentation` (conocimiento redundante/obsoleto) | 13 | `shop/.AGENT/docs/ARQUITECTURA_COMPLETA_SHOP.md`: declarado 2026-06-11, código real 2026-07-29 |
| `service_layer_violations` | 2 | `cart/services/selectors.py::get_for_user` usa `.get_or_create(` dentro de un Selector (debería ser solo lectura) |
| `import_cycles` | 1 grupo de **19 apps mutuamente acopladas** | `app:cart → app:shop`, `app:shop → app:cart` y así en cascada — prácticamente todo el backend forma un único componente fuertemente conectado |
| `dead_frontend_components` | 56 | Incluye **falsos positivos confirmados hoy**: `CartOffcanvas.vue` (editado y verificado en vivo en esta misma sesión, definitivamente no está muerto) |
| `contradictory_counts` | 18 | `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` afirma "11 modelos", el grafo cuenta 35 |

**Hallazgo adicional de esta auditoría (no capturado por el propio validador):**
`frontend/src/views/customer/renting/RentalDetailView.vue` es código muerto real — no está
importado por ningún router ni componente (verificado por grep exhaustivo y confirmado en vivo en
el navegador durante el trabajo de esta sesión: el router usa un alias con el mismo nombre que en
realidad apunta a `PublicDetailView.vue`). **No aparece en `dead_frontend_components`** — el
detector tiene falsos negativos además de los falsos positivos ya confirmados. Esto degrada la
confiabilidad de esa lista como fuente de verdad para decisiones automatizadas de limpieza.

**Módulos aislados:** el ciclo de 19 apps mutuamente acopladas (tabla arriba) significa que, en la
práctica, casi no hay aislamiento real entre apps de dominio — lo opuesto al problema que el
brief pregunta ("módulos aislados"), pero igual de relevante: un grafo de dependencias donde casi
todo depende de casi todo tiene poco valor para blast-radius preciso (todo bloque de código
"afecta potencialmente" a 18 apps más).

---

## FASE 8 — Auditoría de Arquitectura

| Tipo de arquitectura | ¿La representa el grafo? |
|---|---|
| Empresarial / de negocio | No — no hay nodos de "proceso de negocio", "KPI" ni "objetivo" |
| Técnica (modelos, serializers, viewsets, endpoints) | **Sí**, es su fuerte — 166 modelos / 131 ViewSets / 118 endpoints mapeados |
| Lógica (relaciones FK, flujos) | Parcial — FKs sí (`fk_relations`), flujos de negocio no |
| Física (infraestructura, contenedores) | No — el grafo no sabe qué corre en qué contenedor Docker, esa info vive solo en `docker-compose*.yml` |
| Funcional | Parcial, vía `service_contracts`/`business_rules` en los manifests, pero extraídos por regex, no modelados |
| de IA (Agents/Tools/Capabilities) | **No** — ni una arista del grafo conecta `agents/profiles/*.yaml`, `tools/*.py` o `capabilities/registry.py` con `KNOWLEDGE_GRAPH.json`. Son sistemas de registro totalmente separados |
| Documental | Parcial — `documentation_graph.py` cubre nivel2 (`{app}/.AGENT/docs/`) pero excluye `frontend` por el hueco de modelo de datos ya descrito (Fase 4) |
| de Procesos | No | 
| de Datos | Sí, a nivel de modelos/campos | 
| de Eventos | No — Celery tasks, Django signals y WebSocket events no están modelados como nodos |
| de Servicios | Parcial — `services`/`selectors` aparecen listados por app, sin relación explícita entre ellos |
| de APIs | Sí, es su segunda fuerza — `endpoints`, `url_patterns`, `cross_refs.endpoint_to_viewset` |
| de Agentes | **No** (ver "de IA" arriba) |

**Conclusión:** el grafo modela bien la arquitectura de código (Django+DRF+Vue), pero no modela
en absoluto la arquitectura del propio motor de IA (Agents/Tools/Capabilities) que corre sobre él
— una brecha irónica dado que el brief pide auditar justo eso.

---

## FASE 9 — Auditoría del Motor IA

| ¿La IA usa el grafo para...? | Respuesta |
|---|---|
| Comprender dependencias | **Sí**, en el flujo de generación de código (`analyze_impact`, `/breakage`, `/graph/impact/`) |
| Resolver preguntas de negocio a clientes | **No** — `/chat` no lo toca (Fase 3) |
| Encontrar documentación | Sí, indirectamente vía `DocumentationIndex`/nodos `Documentation` — pero solo en el flujo de generación de código |
| Entender relaciones | Sí, dentro del alcance técnico (Fase 8) |
| Resolver ambigüedades | Parcial — `find_affected_apps` combina keywords + structural pass, es heurístico, no garantiza resolución correcta |
| Buscar componentes / APIs / archivos | Sí, vía `project_map.py` |
| Entender arquitectura / flujos | Solo arquitectura técnica, no flujos de negocio |
| Reutilizar decisiones anteriores | Débil — `decisions` en los manifests son extracciones regex de comentarios, no un mecanismo de recuperación de decisiones pasadas |
| Evitar respuestas inconsistentes | Parcial — los guardrails (`guardrails.py`/`guardrails_frontend.py`) previenen código que viole reglas arquitectónicas, pero eso es validación de reglas estáticas, no consistencia semántica derivada del grafo |

---

## FASE 10 — Auditoría de Rendimiento

No existe instrumentación dedicada a medir el propio grafo (no hay métricas de "tiempo de
búsqueda en el grafo" separadas de RAG). Lo verificable:

- `PROJECT_MAP.json` se carga con `@lru_cache(maxsize=1)` — sin I/O repetido por request
  (`FLIJO_COMPLETO_IA_ENGINE.md:792`). Bien diseñado para lo que hace.
- `observability.py` registra tokens/latencia/handoff por turno de `/chat` — pero como ese flujo
  no toca el grafo, esas métricas no dicen nada sobre el rendimiento del grafo en sí.
- No hay dataset ni proceso de medición de precisión/recall del RAG ni del grafo (mismo hallazgo
  que Fase 6).
- Reducción de tokens/redundancia: el diseño de `impact_context` (texto compacto inyectado una
  vez) es eficiente para lo que cubre, pero cubre solo generación de código.
- Escalabilidad: `KNOWLEDGE_GRAPH.json` de 1.39 MB cargado completo en memoria por request es
  aceptable hoy (166 modelos); el patrón "regenerar todo el JSON y recargarlo entero" no escala
  linealmente si el proyecto crece 5-10x sin migrar a una base de grafo real (Neo4j u otra) — hoy
  no hay ningún indicio de motor de grafo real, es JSON plano parseado en Python.

---

## FASE 11 — Auditoría de Gobernanza

| Aspecto | Estado |
|---|---|
| Versionado del grafo | **No existe** — cada regeneración sobreescribe sin historial |
| Historial / linaje de datos | Solo el timestamp de archivo; sin changelog, sin commits dedicados al grafo |
| Control de cambios | Manual, sin proceso — "correr el auditor" es una convención documental, no un gate de CI |
| Trazabilidad | Débil — no se puede saber, mirando el JSON, qué versión del código lo generó más allá del timestamp |
| Integridad | El propio `GRAPH_VALIDATION_REPORT.json` prueba que hay huecos de integridad conocidos y no corregidos desde hace ≥4 días |
| Consistencia | 18 conteos contradictorios documentados (Fase 7) |
| Políticas / estándares | No hay una política escrita de "cuándo regenerar el grafo es obligatorio" más allá de comentarios sueltos en el código |
| **Referencias rotas en documentos de gobernanza** | `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` y `ai_engine/documentation_graph.py` citan `AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md` y `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md` — **ninguno de los dos existe en este checkout**. El `CLAUDE.md` raíz del proyecto (el primer documento que cualquier sesión de IA debe leer, según su propia regla) también referencia dos archivos inexistentes: `docs/.AGENT/GUIA_AI_ENGINE.md` y `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md` |

---

## FASE 12 — Hallazgos

### 🔴 Crítico

**H1 — El flujo de negocio real (`/chat`) no consulta el grafo en absoluto.**
- **Causa:** `action_graph.py` se diseñó como un pipeline independiente de RAG+Tools+CRM Context,
  sin integración con `knowledge_graph.py`/`dependency_graph.py`.
- **Impacto:** el grafo no puede ser "fuente única de verdad del ecosistema" mientras el tráfico
  real de usuarios (soporte web, WhatsApp) lo ignore por completo.
- **Evidencia:** grep de `knowledge_graph|dependency_graph|PROJECT_MAP|KNOWLEDGE_GRAPH` sobre
  `action_graph.py` → 0 resultados.
- **Módulos afectados:** Support, WhatsApp, todo el AI Core orientado a cliente.
- **Prioridad:** máxima si el objetivo es el enunciado del brief (SSOT real).
- **Solución recomendada:** ver Fase 13, Etapa 2.

**H2 — El grafo está desactualizado 4+ días, incluyendo cambios estructurales de esta misma sesión.**
- **Causa:** no hay automatización de regeneración; `.file_hashes.json` vacío rompe además la
  detección incremental.
- **Impacto:** cualquier respuesta de IA que dependiera del grafo hoy estaría razonando sobre un
  estado del proyecto de hace 4 días.
- **Evidencia:** timestamps idénticos `2026-07-31 17:22` en los 4 JSON; `.file_hashes.json = {}`.
- **Módulos afectados:** todos los cubiertos por el grafo (shop, renting, cart, technical_services,
  frontend...).
- **Prioridad:** máxima.
- **Solución recomendada:** Fase 13, Etapa 1.

### 🟠 Alto

**H3 — El detector de código muerto del propio grafo tiene falsos positivos y falsos negativos confirmados.**
- **Causa:** heurística de "componente sin referencias" insuficiente — no resuelve alias de router
  (`RentalDetailView` importando en realidad `PublicDetailView.vue`), y marca como muerto código
  activamente usado.
- **Impacto:** decisiones automatizadas de limpieza basadas en esta lista borrarían código vivo
  (`CartOffcanvas.vue`) y dejarían pasar código muerto real (`RentalDetailView.vue`).
- **Evidencia:** `GRAPH_VALIDATION_REPORT.json::dead_frontend_components` — verificado línea por
  línea contra el estado real del router en esta sesión.
- **Módulos afectados:** frontend, cualquier automatización futura de limpieza de código.
- **Prioridad:** alta.

**H4 — Referencias a documentos de gobernanza inexistentes, incluyendo en el `CLAUDE.md` raíz.**
- **Causa:** desconocida — posible pérdida de archivos no versionados o refactor incompleto.
- **Impacto:** las afirmaciones de "verificado en runtime" en la documentación de arquitectura no
  son verificables con el estado actual del repositorio; rompe la cadena de confianza documental
  que el propio proyecto exige (Fase 11).
- **Evidencia:** búsqueda exhaustiva `find -iname` sobre todo el repo — 4 archivos citados, 0
  encontrados.
- **Módulos afectados:** gobernanza documental de todo el proyecto.
- **Prioridad:** alta.

**H5 — Ciclo de 19 apps backend mutuamente acopladas.**
- **Causa:** arquitectura orgánica sin capas de aislamiento estrictas entre dominios.
- **Impacto:** el blast-radius calculado por el grafo pierde precisión — casi cualquier cambio
  "afecta" a casi todas las apps, lo que reduce el valor práctico de `/breakage`/`/impact` para
  priorizar revisión de riesgo real.
- **Evidencia:** `GRAPH_VALIDATION_REPORT.json::import_cycles[0]`, 19 apps, ~140 aristas internas.
- **Módulos afectados:** todo el backend.
- **Prioridad:** alta (arquitectónico, no se resuelve solo tocando el grafo).

### 🟡 Medio

**H6 — Documentación indexada dos veces por dos pipelines no coordinados (RAG vs grafo).**
- **Causa:** `loaders.py` (RAG) y `documentation_graph.py` (grafo) leen las mismas fuentes de
  forma independiente, sin una capa de ingesta compartida.
- **Impacto:** mantenimiento duplicado, riesgo de que ambos índices diverjan silenciosamente.
- **Evidencia:** comparación directa de fuentes en ambos archivos.
- **Prioridad:** media.

**H7 — 31 documentos de `frontend/.AGENT/doc/` huérfanos del grafo por hueco de modelo de datos.**
- **Causa:** el nodo `App` del grafo asume "Django app"; `frontend` no encaja en ese modelo.
- **Impacto:** toda la documentación de arquitectura frontend (la app con más archivos, 385) está
  fuera del grafo de documentación.
- **Evidencia:** `GRAPH_VALIDATION_REPORT.json::orphaned_app_docs`, 31/31 son de `frontend`.
- **Prioridad:** media-alta (afecta al módulo más grande del proyecto).

**H8 — Discrepancia doc-vs-runtime: 10 índices RAG documentados, 9 servidos en vivo.**
- **Causa:** `DocumentationIndex` documentado en `FLIJO_COMPLETO_IA_ENGINE.md` pero ausente de
  `GET /indices` en producción hoy.
- **Impacto:** menor — funcional, pero la documentación no refleja el estado real.
- **Evidencia:** comparación directa `FLIJO_COMPLETO_IA_ENGINE.md:376-381` vs respuesta HTTP en
  vivo capturada en esta auditoría.
- **Prioridad:** media.

### 🟢 Bajo

**H9 — Sin arquitectura de agentes/tools/capabilities modelada en el grafo.**
- **Impacto:** bajo en lo inmediato (el sistema de Agents funciona con su propio registro), pero
  bloquea cualquier consulta futura tipo "¿qué Tool usa qué endpoint?" vía grafo.
- **Prioridad:** baja, mejora de completitud.

**H10 — Módulos del brief no aplicables al proyecto (BCVOR, VIP, Browser Engine, OCR, VLM).**
- **Impacto:** ninguno real — se documenta para que quede constancia de que se buscó y no se
  encontró, no para tratarlo como un gap a corregir.
- **Prioridad:** informativa, no accionable.

---

## FASE 13 — Plan de Corrección

### Etapa 1 — Frescura y automatización (prerrequisito de todo lo demás)
- **Objetivo:** que el grafo nunca tenga más de X horas de desfase con el código real.
- **Actividades:** (a) reparar `.file_hashes.json` corriendo `auditor.py` completo una vez para
  poblar el baseline; (b) agregar un hook de CI/pre-deploy que corra `python ai_engine/auditor.py`
  y falle el build si el grafo generado difiere del commiteado sin regenerar; (c) automatizar
  rebuild+redeploy de `sintel_ai` tras cada regeneración (hoy es 100% manual, ver Fase 5).
- **Archivos afectados:** `ai_engine/auditor.py`, `ai_engine/incremental_updater.py`,
  pipeline de CI/CD (no existe hoy uno dedicado a esto), `Dockerfile` de `sintel_ai`.
- **Dependencias:** ninguna — puede empezar de inmediato.
- **Riesgos:** el auditor tarda (genera JSON de >1 MB); correrlo en cada commit puede ser lento —
  considerar el modo incremental una vez el baseline esté sano.
- **Criterio de aceptación:** `.file_hashes.json` no vacío; los 4 JSON con timestamp posterior al
  último commit relevante; `/refresh/detect` reportando 0 apps pendientes tras un ciclo completo.

### Etapa 2 — Integrar el Action Graph (`/chat`) con el grafo

> **[APLICADA 2026-08-04]** Esta sección describe el plan tal como se pensó originalmente (nodo
> nuevo desde cero). En la práctica ya existía una Tool real (`GraphImpactAnalysisTool`)
> construida y registrada, solo sin conectar a un intent; conectarla reveló un hallazgo de
> seguridad real que se corrigió primero. Ver el addendum al inicio del documento para el detalle
> completo y la evidencia de verificación en vivo.

- **Objetivo:** que las respuestas de negocio a clientes también puedan consultar relaciones
  estructurales cuando la intención lo amerite (ej. "¿por qué mi cotización no incluye X?" podría
  beneficiarse de `dependency_graph.py`).
- **Actividades:** diseñar un nodo `consult_graph` opcional en `action_graph.py`, gateado por
  intención (no todas las intenciones lo necesitan — evitar sobre-ingeniería); exponerlo como una
  Tool más del `ToolRegistry` en vez de una integración ad-hoc, consistente con el patrón existente.
- **Archivos afectados:** `ai_engine/action_graph.py`, `ai_engine/tools/` (nueva tool), 
  `ai_engine/capabilities/registry.py`.
- **Dependencias:** Etapa 1 (no tiene sentido consultar un grafo desactualizado desde el flujo de
  clientes).
- **Riesgos:** el grafo actual es "código", no "negocio" — puede no aportar valor real a la
  mayoría de intenciones de `/chat`; validar con casos de uso concretos antes de invertir en
  integración completa, no integrar por integrar.
- **Criterio de aceptación:** al menos una intención real de `/chat` demuestra una respuesta mejor
  gracias al grafo, medible A/B.

### Etapa 3 — Cerrar el hueco `frontend` en el modelo de datos
- **Objetivo:** eliminar los 31 huérfanos reales agregando `frontend` como nodo `App` válido.
- **Actividades:** extender el nodo `App` en `knowledge_graph.py` para incluir módulos no-Django
  (`frontend`, y potencialmente `ai_engine` mismo).
- **Archivos afectados:** `ai_engine/knowledge_graph.py`, `ai_engine/documentation_graph.py`.
- **Dependencias:** ninguna, independiente de las otras etapas.
- **Riesgos:** bajo.
- **Criterio de aceptación:** `orphaned_app_docs` baja de 31 a 0 para `frontend` en el próximo
  `GRAPH_VALIDATION_REPORT.json`.

### Etapa 4 — Arreglar el detector de código muerto
- **Objetivo:** eliminar falsos positivos/negativos confirmados (H3).
- **Actividades:** resolver alias de router antes de marcar un componente como sin referencias
  (seguir la cadena `router.js` → import real, no solo el nombre de la variable); agregar
  `RentalDetailView.vue` como caso de prueba de regresión del validador.
- **Archivos afectados:** el script de `GRAPH_VALIDATION_REPORT.json` (no identificado por nombre
  exacto en esta auditoría — probablemente en `auditor.py` o `graph_validator.py`, requiere
  lectura adicional antes de implementar).
- **Dependencias:** ninguna.
- **Riesgos:** bajo.
- **Criterio de aceptación:** `CartOffcanvas.vue` deja de aparecer como muerto;
  `RentalDetailView.vue` empieza a aparecer.

### Etapa 5 — Reparar referencias de gobernanza rotas
- **Objetivo:** que toda cita a un documento en `CLAUDE.md`/`FLIJO_COMPLETO_IA_ENGINE.md` apunte
  a un archivo real.
- **Actividades:** localizar o recrear `docs/.AGENT/GUIA_AI_ENGINE.md`,
  `docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md`, y decidir conscientemente si
  `AUDITORIA/14_*`/`AUDITORIA/16_*` deben recrearse o si las citas deben eliminarse.
- **Archivos afectados:** `CLAUDE.md`, `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`,
  `ai_engine/documentation_graph.py` (comentario que cita la fuente).
- **Dependencias:** requiere decisión humana (no es una corrección de código, es una decisión de
  gobernanza: ¿esos archivos se perdieron o nunca se debieron citar?).
- **Riesgos:** ninguno técnico.
- **Criterio de aceptación:** 0 referencias rotas detectadas por un grep de verificación.

---

## FASE 14 — Resultado Final (Informe Ejecutivo)

1. **Estado actual del Knowledge Graph:** existe, es real, es funcional — pero dentro de un
   alcance acotado (generación de código, no gobierno de todo el ecosistema).
2. **Nivel real de implementación:** ~40%. Fuerte en modelado técnico de código (modelos,
   endpoints, ViewSets); ausente en modelado de negocio, IA/Agents, e integración con el flujo de
   cliente real.
3. **Porcentaje de cobertura del proyecto:** cobertura estructural alta para backend Django
   (166 modelos / 131 ViewSets / 118 endpoints auditados) y buena para frontend (385 archivos),
   pero con 0% de cobertura de los subsistemas de IA (Agents/Tools/Capabilities) y 0% de
   integración con el flujo de negocio real (`/chat`).
4. **Nivel de sincronización con la documentación:** bajo. 13 documentos obsoletos y 18 conteos
   contradictorios detectados por el propio motor, sin regenerar desde hace 4+ días, sin
   automatización que lo corrija.
5. **Nivel de integración con el RAG:** paralelo, no fusionado. Comparten fuente, no comparten
   mecanismo — el grafo no mejora el ranking del RAG ni viceversa.
6. **Nivel de integración con el motor de IA:** parcial y asimétrico — total en generación de
   código, nulo en el chat de negocio (el tráfico real de usuarios).
7. **Calidad de las relaciones entre entidades:** técnicamente sólida donde existe (FK, endpoint→
   viewset), pero con un ciclo de acoplamiento de 19 apps que limita la utilidad práctica del
   blast-radius, y un detector de relaciones "vivo/muerto" con errores confirmados en ambas
   direcciones.
8. **Riesgos detectados:** desactualización silenciosa (sin alarma cuando el grafo envejece),
   decisiones automatizadas de limpieza que borrarían código vivo si se confiaran ciegamente en
   `dead_frontend_components`, y una cadena de documentación de gobernanza con referencias rotas
   que erosiona la confianza en las afirmaciones "verificado en runtime" del propio proyecto.
9. **Oportunidades de optimización:** unificar el pipeline de ingesta de documentación (RAG +
   grafo comparten fuente, podrían compartir loader); resolver el hueco de modelo de datos de
   `frontend`; automatizar completamente la Etapa 1 antes de invertir en cualquier integración
   nueva.
10. **Recomendaciones priorizadas:** (1) automatizar la frescura del grafo — sin esto nada más
    importa; (2) decidir explícitamente si el Action Graph de negocio debe consultar el grafo, y
    si sí, con qué alcance, en vez de asumirlo; (3) reparar el detector de código muerto antes de
    usarlo para cualquier limpieza automatizada; (4) cerrar las referencias de gobernanza rotas
    como una tarea de higiene documental de bajo esfuerzo y alto valor de confianza.
11. **Roadmap técnico hacia SSOT real:** las 5 etapas de la Fase 13, en ese orden — la Etapa 1
    (frescura automática) es la única que bloquea a todas las demás; las Etapas 2-5 son
    paralelizables entre sí una vez resuelta. Convertir el grafo en el mecanismo por el que
    "todas las instrucciones, prompts, consultas y decisiones de la IA recuperen primero el
    contexto desde el grafo" (como pide el brief) es realista **solo** para el flujo de
    generación de código sin trabajo adicional; para el flujo de negocio real requiere la Etapa 2
    completa, que hoy no existe ni en diseño más allá de esta auditoría.
