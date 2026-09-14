# ADK_CUTOVER_PLAN.md — ADK-11 (Plan, NO ejecutado)

Complementa `AUDITORIA/ADK_MIGRATION_AUDIT.md` (ADK-00 a ADK-10, todo completo y aislado en
`adk_poc/`, cero cambios a produccion). Este documento es el **plan** de ADK-11 (Cutover),
pedido explicitamente por el usuario como "disena el plan, sin ejecutarlo" — ningun paso de
aqui se ejecuta sin una autorizacion posterior, explicita, por item.

## 0. Requisito duro agregado por el usuario (2026-09-14, durante esta misma fase)

> "quiero que dejes google adk como unico orquestador RAG para atencion al cliente y
> gestion de chat de soporte y servicio al cliente"

**Alcance confirmado por el propio usuario: esto aplica al chat de atencion al
cliente/soporte (`ai_engine` /chat, los 9 Support Agent profiles de ADK-04/05) — no a
`ai_editor`/EKG (ADK-07/09, sistema separado, sin deploy hoy, sin decision de cutover
propia todavia).**

**Estado real de esto DESPUES de ADK-00 a ADK-10 (ya construido, verificado, solo falta
activar):**
- El Root Workflow de ADK (`sintel_root_workflow.py`) es quien decide SI se hace retrieval
  (via el router determinista de ADK-04, `intent == "knowledge"`) y quien invoca
  `sintel_rag_adapter.build_knowledge_context()` -- ADK-06.
- `action_graph.py::node_retrieve_knowledge` es el UNICO otro punto del sistema real que
  hoy hace retrieval de RAG (llama a la MISMA funcion real,
  `retrievers.retrieve_knowledge_for_chat`, sin duplicar logica).
- **Para que ADK quede como UNICO orquestador de RAG (no "el principal", UNICO), el
  cutover debe RETIRAR `action_graph.py::node_retrieve_knowledge` (y el propio
  `action_graph.py` completo, dado que es un solo grafo, no solo el nodo de RAG) en el
  MISMO cutover que activa el Root Workflow de ADK — no coexistir "por un tiempo" con
  ambos caminos de RAG activos.** Esto es mas fuerte que un blue-green tibio: exige que,
  al terminar el cutover, el proceso `sintel_ai` YA NO tenga ningun codigo capaz de
  ejecutar `node_retrieve_knowledge` en produccion (ver seccion 3, Opcion A, que ya
  cumple esto por diseno -- OLD se apaga, no solo se deja de enrutarle trafico).

## 1. Alcance de ADK-11 (este plan)

**Dentro de alcance:** cutover del chat de soporte/atencion al cliente (`ai_engine` /chat,
consumido por `support/services/ai_bridge.py::ask_ai()`/`ask_ai_async()` desde
`SupportChatConsumer` y el webhook de WhatsApp).

**Fuera de alcance de este plan (decision separada, futura):** `ai_editor` (ADK-07/09) --
no esta desplegado como servicio hoy (sin Dockerfile, sin entrada en
`docker-compose*.yml`), asi que no tiene un "cutover" que ejecutar todavia. El adapter de
ADK-09 queda listo en `adk_poc/` para cuando esa decision se tome, sin bloquear esto.

## 2. Hallazgo que dirige la decision de arquitectura (ADK-10, ya confirmado)

`langchain-openai==0.2.14` (necesario para el `LOCAL_MODEL_CHAIN` real, que encadena LM
Studio como fallback) exige `openai<2.0.0`; `litellm` (dependencia de ADK, usado por
`LiteLlm`) exige `openai>=2.20.0` — **rangos que no se solapan.** Mientras el codigo de
`action_graph.py` (LangChain/LangGraph) siga importado en el MISMO proceso Python que el
codigo ADK (LiteLLM), no hay una sola version de `openai` que sirva a ambos. Esto elimina
de raiz cualquier diseño que intente que un solo proceso `sintel_ai` importe ambos stacks
"por un tiempo" durante la transicion.

## 3. Opciones de arquitectura de despliegue evaluadas

### Opcion A — Blue-green por servicio separado, swap de `AI_ENGINE_URL` (RECOMENDADA)

Django ya tiene un UNICO punto de integracion real con `ai_engine`:
`settings.AI_ENGINE_URL` (`ecommerce/settings/base.py:342`, default
`http://sintel_ai:8100`), consumido solo por `ai_bridge.py::ask_ai()`/`ask_ai_async()`
(`POST {AI_ENGINE_URL}/chat`). Ni `SupportChatConsumer` ni el webhook de WhatsApp llaman a
`ai_engine` por ningun otro camino.

**Pasos (alto nivel, cada uno con su propia autorizacion antes de ejecutarse):**
1. Construir un servicio NUEVO (`sintel_ai_adk`, contenedor propio, su propio
   `requirements.txt`/venv -- SOLO paquetes ADK/LiteLLM, sin `langchain-core`/
   `langchain-ollama`/`langchain-openai`/`langgraph` -- resuelve el conflicto de
   dependencias por construccion, no por parcheo) que expone el MISMO contrato HTTP real
   que `ai_bridge.py` ya consume: `POST /chat` (mismo `ChatRequest`: `message`,
   `conversation_id`, `confirm`; mismo `ChatResponse` minimo: `conversation_id`,
   `response` -- ver seccion 4 para el resto de campos, pendiente) y `GET /health`.
   Internamente, este servicio es una envoltura fina de `sintel_root_workflow.
   run_sintel_turn()` (ya construido y probado en ADK-03 a ADK-10) sobre FastAPI, mismo
   framework que el servicio real hoy.
2. Agregar `sintel_ai_adk` a `docker-compose.yml`/`docker-compose.prod.yml` (nuevo
   servicio, puerto propio, ej. 8101) -- SIN tocar el servicio `sintel_ai` (OLD) existente.
   Ambos corren simultaneamente, en contenedores/venvs separados -- el conflicto de
   dependencias de la seccion 2 no aplica (procesos distintos).
3. **Validacion en produccion sin riesgo para el usuario final**: correr el dual run de
   ADK-10 (ya construido) contra ESTE servicio nuevo (no `adk_poc/` aislado) durante un
   periodo, comparando respuestas reales lado a lado sin que `sintel_ai_adk` reciba
   trafico real de clientes todavia.
4. **Cutover real**: cambiar `AI_ENGINE_URL` (una sola variable de entorno de Django) de
   `http://sintel_ai:8100` a `http://sintel_ai_adk:8101`. Reiniciar Django (o recargar
   settings, segun el mecanismo real del proyecto). Este es el UNICO paso que afecta
   trafico real de clientes.
5. **Apagar `sintel_ai` (OLD)** -- requisito duro de la seccion 0: no basta con dejar de
   enrutarle trafico, el requisito del usuario es que ADK quede como UNICO orquestador.
   Detener y remover el contenedor/servicio OLD de `docker-compose.yml` (no solo dejarlo
   corriendo sin trafico) es parte de este mismo cutover, no un paso futuro opcional.

**Rollback**: revertir `AI_ENGINE_URL` a `http://sintel_ai:8100` + reiniciar `sintel_ai`
(si ya se detuvo en el paso 5, un `docker compose up sintel_ai` lo revive desde la misma
imagen -- no hace falta rebuild). Tiempo de rollback: minutos, un cambio de config + un
restart de contenedor, sin redeploy de codigo. Esto SI satisface el requisito del plan
original ("cutover con capacidad de rollback inmediato").

**Costo real**: durante la ventana de transicion (pasos 1-4), el proyecto corre 2
contenedores de `ai_engine` (mas RAM/CPU temporal) -- aceptable dado que es una ventana
corta y deliberada, no un estado permanente (termina en el paso 5).

### Opcion B — Proxy de canary/rollout gradual

Variante de A con un componente extra (proxy/gateway) que reenvia cada `/chat` a OLD o
NEW segun una regla (hash de `conversation_id`, % de trafico, feature flag por sala).
Permite validar con trafico REAL de clientes de forma gradual antes del 100%.

**Descartada como recomendacion principal** (no como imposible): agrega un componente
nuevo a operar (el proxy mismo), y el proyecto es single-tenant de escala moderada (ver
memoria: sin necesidad de infraestructura de canary compleja ya existente) -- el costo de
construir y operar el proxy no parece proporcional al beneficio sobre la Opcion A, dado
que ADK-10 ya genero confianza fuerte con dual-run estructurado contra infraestructura
real. Si el usuario prefiere de todos modos una validacion gradual con trafico real antes
del 100%, esta opcion queda disponible -- requiere una decision explicita aparte.

### Opcion C — Cutover atomico dentro del MISMO proceso `sintel_ai`

Reemplazar `action_graph.py` por el Root Workflow de ADK dentro del mismo contenedor,
resolviendo el conflicto de dependencias eliminando `langchain-core`/`langchain-ollama`/
`langchain-openai`/`langgraph` del `requirements.txt` de `ai_engine` EN EL MISMO commit
que agrega ADK (esto efectivamente ejecuta ADK-12, eliminacion del runtime viejo, de forma
simultanea a ADK-11, no despues).

**Descartada como recomendacion principal**: sin ventana de coexistencia, no hay forma de
comparar OLD vs NEW con trafico real antes de comprometerse (ADK-10 ya lo hizo, pero de
forma aislada/sintetica, no con trafico real de clientes). El rollback exige un redeploy
completo de la imagen anterior (mas lento que un swap de config) -- no cumple tan bien el
requisito de "rollback inmediato" del plan original. Se deja documentada como alternativa
mas simple operacionalmente a LARGO plazo (un solo proceso, sin par de contenedores) --
podria ser el estado FINAL deseado, alcanzado despues de validar con la Opcion A y
completar ADK-12 formalmente, no el mecanismo del cutover en si.

## 4. Trabajo tecnico real pendiente antes de poder ejecutar la Opcion A (no de este plan,
   de una fase de CONSTRUCCION futura, con su propia autorizacion)

- **Contrato HTTP completo**: `sintel_root_workflow.run_sintel_turn()` hoy devuelve
  `{conversation_id, session_id, intent, agent, handoff, response, events}` -- el
  `ChatResponse` real que `ai_bridge.py`/`_process_chat_response()` consume tambien
  necesita (o degrada con gracia sin) `tool_calls`, `tool_results`, `needs_confirmation`,
  `confirmation`, `metrics` (pendiente ya identificado desde ADK-03, nunca cerrado --
  ver ADK-10). `ai_response_opened_ticket()` (ai_bridge.py) en particular depende de
  poder inferir si se ejecuto `abrir_ticket_soporte` desde la respuesta -- verificar que
  campo del nuevo contrato cubre eso antes de construir el servicio nuevo.
- **HITL real para escrituras del chat** (ej. `RequestKycUpgradeTool`,
  `CreateRentalRequestTool`): ADK-02 probo que `require_confirmation` pausa la ejecucion,
  pero el flujo de RESUME (el usuario responde "si" y la escritura real se dispara) nunca
  se probo end-to-end (pendiente heredado desde ADK-02, sigue abierto). El sistema OLD
  real ya tiene esto resuelto via `pending_write`/`policy_decision` en
  `SintelActionState` + el parametro `confirm` de `ChatRequest` -- el servicio nuevo debe
  replicar ese comportamiento observable, no inventar uno distinto.
- **Backend de sesion persistente real** (ADK-08 dejo la clasificacion hecha, la eleccion
  de backend pendiente): Redis (reusa infraestructura ya operada, mismo Redis DB 2 del
  checkpointer viejo se podria dedicar a esto) vs `DatabaseSessionService` de ADK sobre
  Postgres. Recomendacion preliminar: Redis, por el mismo motivo que ya goberno
  `RedisCheckpointSaver` (reusar infra existente) -- pero verificar que el
  `SessionService` de ADK realmente soporta un backend Redis (revisar si existe uno
  oficial o si hay que escribir uno, como se escribio `RedisCheckpointSaver` a mano para
  LangGraph por falta de soporte oficial con las capacidades del Redis real del
  proyecto).
- **Cost control real** (`cost_control.check_and_increment_daily_turns`, limite diario de
  turnos por usuario) y **rate limiting real** (`AI_CHAT_RATE_LIMIT`/
  `AI_CHAT_RATE_WINDOW_SECONDS` en `ai_bridge.py`, y cualquier throttle propio de
  `ai_engine`) -- confirmar que el servicio nuevo los preserva; son protecciones de costo/
  abuso reales, no cosmeticas.
- **Continuidad de conversaciones en curso al momento del corte**: una conversacion con
  historial en el checkpointer de Redis del sistema OLD no sera visible para el sistema
  NEW (backend de sesion distinto, sin importar cual se elija en el punto anterior). El
  historial LEGIBLE por humanos (`ChatRoom`/`ChatMessage` en Django) no se pierde -- solo
  el contexto de corto plazo que el LLM tenia cargado se reinicia para esa sala en su
  siguiente turno. Decidir si esto es aceptable tal cual (razonable: son conversaciones de
  soporte, tipicamente cortas) o si vale la pena migrar el estado activo -- probablemente
  no vale la complejidad, pero es una decision explicita pendiente, no un accidente.
- **Imagen/Dockerfile propio para `sintel_ai_adk`**: basado en el `requirements.txt` real
  ya construido y probado en `adk_poc/` (85+ paquetes, incluye `google-adk`, `litellm`,
  FastAPI, PyJWT, httpx -- YA verificado que corre limpio sin Django/Postgres) mas lo que
  falte para servir HTTP real (uvicorn, ya viene con FastAPI en el proyecto real).

## 4bis. Ejecucion real (2026-09-14, autorizada explicitamente: "ajecuta el plan y sicroniza con produccion de forma general")

Pasos 1-3 de la Opcion A EJECUTADOS y verificados contra infraestructura real (no un
simulacro):

1. **Extraccion de `routing.py`/`model_chain.py`** desde `action_graph.py`/`llm_factory.py`
   (commits `64b340e`, `e564d25`) -- logica pura, cero cambio de comportamiento, verificado
   contra la imagen REAL del contenedor `sintel_ai` (disposable, sin afectar produccion):
   162/162 tests reales de `ai_engine/tests/` sin regresiones.
2. **Flujo de RESUME de confirmaciones descubierto y probado** (`adk_poc/
   test_sintel_hitl_resume.py`, commit `6d159ea`) -- gap abierto desde ADK-02, ahora
   cerrado: ADK emite un evento sintetico (`adk_request_confirmation`) cuyo id (no el de
   la llamada original) es el que hay que usar para resumir.
3. **Servicio `sintel_ai_adk` construido y desplegado** (commit `19ba5d5`), agregado a
   `docker-compose.yml` de forma ADITIVA -- `sintel_ai` (OLD) confirmado sin interrupcion
   durante todo el proceso. Contrato HTTP completo (`tool_calls`/`needs_confirmation`/
   `confirmation`/RESUME) cerrado, pendiente desde ADK-03.

**2 conflictos de dependencias reales adicionales encontrados durante el build** (mas alla
del de `openai` ya documentado en ADK-10): `google-adk==2.9.0` exige `fastapi>=0.133` y
`uvicorn>=0.34`, incompatibles con los pines del sistema OLD -- resuelto dejando que pip
resuelva esas versiones a partir de lo que `google-adk` exige.

**Verificado end-to-end contra la infraestructura real:** `/health` responde; `/chat` sin
token rechaza con 401; `/chat` con un JWT firmado con un secreto DE PRUEBA (nunca el real de
produccion, nunca extraido) es rechazado correctamente por el Django real -- confirma la
cadena de identidad completa (validacion local + Django real) sin exponer ningun secreto de
produccion.

**NO ejecutado, deliberadamente, gate final que sigue vigente:** el swap de `AI_ENGINE_URL`
y el apagado de `sintel_ai` (paso 4-5 de la Opcion A) -- el unico paso que afectaria trafico
real de clientes. Tampoco se ejecuto un smoke test de `/chat` con una identidad REAL (exige
una credencial de prueba real, no la extraccion del secreto de produccion -- fuera de
alcance sin que el usuario provea una) ni el dual-run de ADK-10 contra el servicio ya
desplegado. Este es exactamente el punto donde el "gate final" de la seccion 5 sigue
aplicando -- "ejecuta el plan" se interpreto como autorizacion para CONSTRUIR y DESPLEGAR
junto a produccion (reversible: `docker compose stop sintel_ai_adk` sin afectar nada mas),
no como autorizacion para el corte de trafico real en si, dado su blast radius distinto
(afecta clientes reales) y que el propio plan (seccion 5) declara ese paso sujeto a
confirmacion explicita item por item.

## 5. Gate final antes de ejecutar cualquier paso de este plan

Ningun paso de la seccion 3 (Opcion A) se ejecuta sin autorizacion explicita, item por
item -- consistente con el criterio ya aplicado en esta mision para acciones dificiles de
revertir o que afectan sistemas compartidos. El checkpoint obligatorio de la mision
(seccion 24 del plan original) sigue vigente: cualquier regresion de seguridad, perdida de
datos, ruptura de contrato, test fallido o ambiguedad de migracion detiene el avance para
reportar antes de continuar.
