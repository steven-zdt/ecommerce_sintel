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

## 4ter. Swap de trafico y apagado de OLD -- EJECUTADO (2026-09-14, autorizado explicitamente: "continua el swap de trafico y apaga sintel_ai")

**Hallazgo real encontrado justo antes del swap, no bloqueante pero importante:**
`LOCAL_MODEL_CHAIN` real de produccion (verificado con `printenv`, dato no sensible -- URL/
nombre de modelo, no un secreto) es `lmstudio|openai-compatible|http://host.docker.internal:
1234/v1|qwen/qwen3.5-9b` -- **LM Studio, no Ollama**, y SIN entrada de fallback (una sola
entrada en la cadena). El fix de `JSON_SCHEMA_FOR_FUNC_DECL=False` (ADK-01) solo se habia
verificado contra Ollama en TODA la mision hasta este punto -- riesgo real, nunca resuelto
silenciosamente. Se intento verificar tool-calling real contra LM Studio antes del swap:
**LM Studio no esta corriendo en este momento** (`ConnectError: Connection refused`,
confirmado igual desde el contenedor OLD y el NEW -- no es un problema de red de este
servicio, LM Studio simplemente no esta activo ahora mismo en el host). Esto significa que,
en este momento, NINGUNO de los dos sistemas (OLD ni NEW) puede servir un turno de chat real
con datos de un LLM -- el swap no empeora esa situacion preexistente, pero el riesgo real
(`JSON_SCHEMA_FOR_FUNC_DECL` sin verificar contra LM Studio) sigue sin resolverse y se hara
visible en cuanto LM Studio vuelva a estar disponible. **Accion pendiente real:** verificar
tool-calling real contra LM Studio en cuanto este disponible, antes de confiar en ese
proveedor para trafico real de escritura (ver seccion 4, ya lo listaba como pendiente).

**Pasos ejecutados:**
1. `AI_ENGINE_URL` cambiado en `.env` (`http://sintel_ai:8100` -> `http://sintel_ai_adk:
   8101`).
2. `docker compose restart django celery_worker celery_beat` **NO fue suficiente** --
   `restart` reutiliza el contenedor existente sin releer `env_file` (confirmado: `printenv
   AI_ENGINE_URL` dentro del contenedor seguia mostrando el valor viejo). Se uso `docker
   compose up -d django celery_worker celery_beat` (recrea los contenedores con el env
   actual) -- confirmado con `printenv` que el valor nuevo si quedo cargado.
3. Verificado que Django alcanza el servicio NEW por la red real:
   `docker exec ecommerce_sintel_django python -c "requests.get('http://sintel_ai_adk:8101/health')"`
   -> `200 {'status': 'ok', 'orchestrator': 'google-adk'}`.
4. Verificado que `nginx/` no tiene ninguna ruta directa a `sintel_ai` (unico punto de
   integracion real confirmado: `AI_ENGINE_URL`, ya cambiado).
5. `docker compose stop sintel_ai` (no `rm`/`down` -- el contenedor sigue existiendo,
   detenido, para rollback inmediato sin rebuild). Confirmado `Exited (0)`, salida limpia.
6. Django reiniciado sin errores en logs, healthcheck real (`docker ps`) en estado
   `healthy`.

**Estado final:** `sintel_ai_adk` (Google ADK) es ahora el UNICO orquestador de RAG/chat de
atencion al cliente en produccion -- requisito duro del usuario (seccion 0) cumplido.
`sintel_ai` (OLD, LangGraph) esta detenido, no eliminado.

**Rollback (si hiciera falta), pasos exactos:**
1. En `.env`: revertir `AI_ENGINE_URL=http://sintel_ai:8100`.
2. `docker compose up -d django celery_worker celery_beat` (recrea con el env revertido --
   `restart` NO basta, ver hallazgo del paso 2 arriba).
3. `docker compose start sintel_ai` (revive el contenedor detenido, misma imagen, sin
   rebuild).
4. Verificar `docker exec ecommerce_sintel_django printenv AI_ENGINE_URL` -> debe mostrar
   `http://sintel_ai:8100` de nuevo.

**No ejecutado, deliberadamente, fuera de alcance de esta instruccion:** ADK-12
(eliminacion del runtime viejo -- borrar `ai_engine/action_graph.py`/`llm_factory.py`/
`redis_checkpointer.py`/`main.py`/el servicio `sintel_ai` de `docker-compose.yml`) es una
fase separada, con su propio checklist ("cero consumidores verificados, tests, rollback",
seccion 12 del plan original) -- no se borro nada del sistema OLD, solo se detuvo.

## 4quater. Primer mensaje REAL de produccion, contra LM Studio real (2026-09-14, pedido explicito del usuario: "e iniciado LM Studio y manda un mensaje real de prueba")

**El riesgo critico que quedaba abierto tras el swap (JSON_SCHEMA_FOR_FUNC_DECL nunca
verificado contra LM Studio) queda CONFIRMADO RESUELTO** -- primer turno real de
produccion, con identidad real (JWT emitido con `AccessToken.for_user()`, el MISMO
mecanismo real que usa `ai_bridge.py::ask_ai()`, para el usuario de prueba ya existente
`cliente.test@sintel.co`, id=4 -- nunca se extrajo `JWT_SECRET_KEY` de produccion),
mensaje "Cual es el estado de mi pedido?", contra el servicio YA desplegado en produccion
(`sintel_ai_adk`, no un ambiente aislado):

- `intent=order_status`, `agent=OrderAgent` -- router determinista correcto.
- `tool_calls=[{'name': 'OrderStatusTool', 'args': {'limit': 5}}]` -- **el LLM SI disparo
  una function call real contra LM Studio** (el hallazgo que quedaba pendiente).
- `tool_results` con los 5 pedidos REALES del usuario de prueba (uuids/montos/estados
  reales de la base de datos, verificados contra `Order.objects.filter(user=u)`).
- Respuesta final grounded en los datos reales (uuids/montos/estados citados
  correctamente, ningun dato inventado).

**Bug real encontrado y corregido en el mismo ciclo:** el primer intento fallo con 200 +
degradacion controlada (`engine_unavailable`) -- `cost_control.py` (reusado de `ai_engine/`
en el Dockerfile) importa `redis.asyncio`, pero `redis` nunca se agrego a
`ai_engine_adk/requirements.txt`. Cualquier turno real habria fallado con esto hasta
corregirlo -- no se detecto en las pruebas de `adk_poc/` porque ahi `redis` ya estaba
instalado por otras razones (ADK-10). Fix: `redis>=5.0.0,<7.0.0` agregado (misma version
que `ai_engine/requirements.txt`), imagen reconstruida y redesplegada
(`docker compose build sintel_ai_adk && docker compose up -d sintel_ai_adk`), reintentado
con exito.

**Hallazgo NO bloqueante, pendiente de pulido (no de este cutover, seguimiento futuro):**
la respuesta final incluye el razonamiento interno del modelo (`qwen/qwen3.5-9b` via LM
Studio) mezclado antes de la respuesta real ("El usuario quiere saber el estado de su
pedido. Para responder a esta consulta, necesito usar la herramienta...") -- un cliente
real veria ese "pensar en voz alta" del modelo, no solo la respuesta limpia. No es un
problema de seguridad ni de correctness (los datos citados son reales y correctos) -- es
un problema de UX/prompt-engineering especifico de como este modelo emite su
razonamiento, a revisar en un seguimiento (posible fix: instruccion explicita de no incluir
razonamiento, o configuracion de LiteLlm/LM Studio para separar `reasoning_content` de
`content` si el modelo lo soporta).

## 4quinquies. Hallazgo critico: DOS stacks Docker separados -- todo lo anterior de esta
## sesion vivio en STAGING, no en la produccion real (2026-09-14)

**Confirmado con el usuario en vivo ("si confirmo es produccion sintel.net.co"):**
`https://sintel.net.co/` lo sirve el proyecto Docker Compose **`sintel_production`**
(`docker-compose.prod.yml`, contenedores `sintel_prod_*`, ingreso via Cloudflare Tunnel
`sintel_prod_cloudflared` -- sin puertos publicados directamente al host) -- un stack
**completamente separado** del proyecto `ecommerce_sintel` (`docker-compose.yml`,
contenedores `ecommerce_sintel_*`, nginx publicado en `:8080`) que es el que se uso para
TODO el trabajo de esta sesion (ADK-00 a ADK-11, cutover, fix del reasoning leak).

**Implicacion real, verificada:** el cutover a Google ADK (seccion 4ter) y el fix del leak
de razonamiento (`AUDITORIA/REASONING_LEAK_FIX_REPORT.md`) **NUNCA se aplicaron a
`sintel_production`**. Ese stack real sigue corriendo `sintel_ai` viejo (imagen
`ecommerce_sintel_ai:prod`, LangGraph) sin ningun cambio de esta sesion.

**Hallazgo adicional en `sintel_production` (no relacionado con el trabajo de esta sesion,
descubierto investigando un reporte del usuario de "no veo las respuestas del chat en la
UI"):** `settings.AI_SUPPORT_CHAT_ENABLED = False` en produccion real -- el chat de IA esta
**deshabilitado por feature flag global**, no por ningun bug. Confirmado via Django shell
(solo lectura): un usuario real (`ceo@sintel.net.co`, no staff, sala `OPEN`, sin pausa, sin
admin asignado) mando 4 mensajes reales que se guardaron correctamente (`[CHAT]
status=sent`) pero JAMAS dispararon `_ai_reply()` (nunca aparece `AI request
status=started` en los logs) -- `is_ai_mode_active()` corta en la primera condicion
(`AI_SUPPORT_CHAT_ENABLED`) antes de llegar a nada relacionado con `sintel_ai`.

**Decision del usuario (2026-09-14): Opcion 1 -- dejar `AI_SUPPORT_CHAT_ENABLED=False` en
`sintel_production` tal como esta.** No se modifico nada en ese stack. El chat de soporte
en produccion real sigue sin IA (los clientes reciben el flujo de soporte humano normal,
sin degradacion -- los mensajes SI se guardan y son visibles para un agente humano, la IA
simplemente no responde). Las otras dos opciones evaluadas y descartadas por ahora:
(2) activar el flag con el `sintel_ai` viejo tal cual, sin el fix de razonamiento ni ADK;
(3) migrar primero el cutover+fix a `docker-compose.prod.yml` y luego activar -- **esta
sigue siendo la ruta recomendada cuando se decida activar IA en produccion real**, no
descartada, solo no ejecutada ahora.

**Estado real resultante:** `ecommerce_sintel` (staging) corre Google ADK + el fix del
reasoning leak, verificado con trafico real de esa sala de staging. `sintel_production`
(real) sigue exactamente como estaba antes de esta sesion completa -- sin ADK, sin el fix,
y con IA deshabilitada por flag (no por fallo). Ningun cliente real de `sintel.net.co` fue
afectado, positiva ni negativamente, por ningun cambio de esta sesion.

## 5. Gate final antes de ejecutar cualquier paso de este plan

Ningun paso de la seccion 3 (Opcion A) se ejecuta sin autorizacion explicita, item por
item -- consistente con el criterio ya aplicado en esta mision para acciones dificiles de
revertir o que afectan sistemas compartidos. El checkpoint obligatorio de la mision
(seccion 24 del plan original) sigue vigente: cualquier regresion de seguridad, perdida de
datos, ruptura de contrato, test fallido o ambiguedad de migracion detiene el avance para
reportar antes de continuar. **Estado a 2026-09-14: pasos 1-5 de la Opcion A completos y
ejecutados (seccion 4ter); pendiente real: ADK-12 (eliminacion de OLD) y verificar
tool-calling contra LM Studio real en cuanto vuelva a estar disponible.**
