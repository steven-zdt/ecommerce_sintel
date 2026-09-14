# REASONING_LEAK_FIX_REPORT.md

Informe final (FASE 20 de la mision "auditoria y correccion integral del leak de
reasoning de Qwen3.5", 2026-09-14). Complementa `AUDITORIA/ADK_CUTOVER_PLAN.md`
(seccion 4quater documenta el hallazgo original en produccion).

## 1. Diagnostico

**Causa raiz:** un unico punto de codigo propio (`sintel_root_workflow.py::
run_sintel_turn()`) concatenaba **todos** los `Part.text` de **todos** los eventos de
ADK al construir la respuesta publica, sin filtrar `Part.thought` -- el campo REAL de
`google.genai.types` que ADK ya usa para marcar razonamiento interno.

**NO era la causa** (cada uno verificado con evidencia real, no descartado por
suposicion):
- **El modelo (Qwen3.5):** produce razonamiento normal, como cualquier modelo hibrido.
- **El backend (LM Studio):** SI separa `reasoning_content` de `content` en su
  respuesta HTTP real -- confirmado con una llamada `litellm.completion()` cruda
  contra el LM Studio real del usuario.
- **LiteLLM:** propaga `reasoning_content` intacto desde el proveedor.
- **Google ADK:** `google/adk/models/lite_llm.py` (codigo real instalado, version
  2.9.0) ya convierte ese campo en `types.Part(text=..., thought=True)` -- la propia
  libreria documenta en un comentario real: *"'reasoning' (usado por LM Studio,
  vLLM)"*. Este es exactamente nuestro caso, ya contemplado por el framework.
- **El historial multi-turn de ADK:** al reconstruir el mensaje saliente para el
  proveedor en turnos siguientes, ADK separa `reasoning_content` de `content` de
  nuevo (`lite_llm.py` linea ~1458) -- nunca reenvia razonamiento como contenido
  normal.

## 2. Punto exacto del leakage

- **Archivo:** `ecommerce_sintel/ai_engine_adk/sintel_root_workflow.py`
- **Simbolo:** `run_sintel_turn()`, construccion de la variable local `final_text`
  (antes de la correccion)
- **Flujo:** `Runner.run_async()` (ADK) emite `Event`s con `Content.parts` que
  incluyen tanto `Part(text=razonamiento, thought=True)` como
  `Part(text=respuesta_publica)` (sin `thought`) -- el codigo viejo los concatenaba
  todos por igual, sin distinguir `part.thought`.

## 3. Cambios realizados

| Archivo | Simbolo | Cambio |
|---|---|---|
| `ai_engine_adk/public_response.py` | **nuevo modulo** | `extract_public_response(events, conversation_id="")` -- unico punto de conversion `Event` de ADK -> payload publico. Filtra `part.thought` (mecanismo PRIMARIO) + filtro defensivo secundario de tags `<think>` completos con logging `PUBLIC_REASONING_LEAK_DETECTED` si dispara. Reexporta `REQUEST_CONFIRMATION_FUNCTION_CALL_NAME` (antes duplicada en 2 archivos). |
| `ai_engine_adk/sintel_root_workflow.py` | `run_sintel_turn()` | Reemplaza la construccion manual de `tool_calls`/`tool_results`/`final_text` (3 bloques separados) por una sola llamada a `extract_public_response()`. |
| `ai_engine_adk/tests/test_reasoning_separation.py` | **nuevo archivo** | 11 tests (ver seccion 5). |

**No se creo ninguna clase `InternalReasoning`/`PublicContent`/`ToolCall` nueva** --
se reutilizo el contrato semantico que ADK YA tiene (`Part.thought`,
`Event.get_function_calls()`/`get_function_responses()`), consistente con la regla
dura de la mision de no duplicar arquitectura existente.

**No se toco:** `ai_engine/` (sistema OLD, ya detenido, sin relacion con este bug),
`ai_editor/` (sistema separado, no usa este mismo adapter LiteLlm/ADK todavia -- ver
seccion 9), Django/PostgreSQL/pgvector/project_knowledge_graph/RetrievalService/
Tool Registry/Commands/Selectors/Policy Layer/Session (ninguno relacionado con la
causa raiz real).

## 4. Arquitectura resultante

```
Qwen3.5 (LM Studio)
    │
    ├── reasoning_content ──► LiteLLM ──► ADK LiteLlm._extract_reasoning_value()
    │                                          │
    │                                          ▼
    │                                 Part(text=..., thought=True)
    │                                          │
    └── content ──────────► LiteLLM ──► ADK    │            (YA lo hacia ADK,
                                         │      │             sin cambios aqui)
                                         ▼      │
                              Part(text=...)    │
                                         │      │
                                         ▼      ▼
                          sintel_root_workflow.run_sintel_turn()
                                         │
                                         ▼
                    public_response.extract_public_response()  ◄── CORRECCION
                          │                    │              │    (unico punto
                          ▼                    ▼               ▼    nuevo real)
                  PUBLIC_CONTENT          TOOL_CALL      TOOL_RESULT
                  (response)          (tool_calls[])   (tool_results[])
                          │                    │               │
                          └────────────────────┴───────────────┘
                                         │
                                         ▼
                          ChatResponse (main.py, sin campos de reasoning)
                                         │
                                         ▼
                  ai_bridge.py (Django) ──► support/consumers.py:322
                                         │
                                         ▼
                                      CLIENTE
```

`internal_reasoning` (razonamiento) se descarta despues de loguearse (nivel INFO,
solo longitud, no el texto completo -- minimiza retencion de un dato interno) --
nunca cruza hacia `ChatResponse`.

## 5. Tests

**11/11 pasando** (`ai_engine_adk/tests/test_reasoning_separation.py`, verificado en
un contenedor desechable antes del redeploy, y de nuevo tras el redeploy real):

- `test_t1_simple_response_without_tool_has_no_reasoning` -- PASS
- `test_t2_reasoning_plus_final_response_only_final_is_public` -- PASS
- `test_t3_reasoning_tool_call_tool_result_final_response` -- PASS
- `test_t3_confirmation_synthetic_call_excluded_from_tool_calls` -- PASS
- `test_t8_reasoning_with_think_tags_stays_internal` -- PASS
- `test_t9_defensive_filter_strips_real_think_tag_leak` -- PASS
- `test_t9_defensive_filter_does_not_destroy_legitimate_content_without_full_tag` -- PASS
- `test_t9_defensive_filter_logs_error_when_triggered` -- PASS
- `test_t11_chat_response_schema_has_no_reasoning_fields` -- PASS
- `test_t6_e2e_multiturn_reasoning_never_leaks_across_turns` -- PASS (**contra LM Studio real**)
- `test_t12_tool_calling_still_works_after_the_fix` -- PASS (**contra LM Studio real**)

**T4/T5 (streaming) deliberadamente NO agregados:** no existe una ruta de streaming
activa en `ai_engine_adk`/`main.py` hoy (un solo `POST /chat`, sin SSE/WS en este
servicio -- el WebSocket real vive en Django, `support/consumers.py`, y consume el
`response` ya agregado de este servicio, nunca eventos ADK crudos). Fabricar un test
de streaming para una ruta de codigo que no existe violaria la regla de la mision
"no introducir stubs" / "validar contra el codigo real". Si se agrega streaming en el
futuro, `extract_public_response()` es agnostico al origen de los eventos (batch o
incremental) y deberia seguir siendo correcto, pero eso queda sin probar hasta que
esa ruta exista de verdad.

**Regresion:** este fix modifico exclusivamente `ai_engine_adk/` (servicio nuevo,
desplegado en ADK-11) -- no toco ningun archivo de `ai_engine/` (OLD, ya detenido),
por lo que no aplica una re-ejecucion de esa suite (162/162, ya verificada en el
commit de extraccion de `routing.py`/`model_chain.py`, sin relacion con este bug).

## 6. Evidencia de streaming

No aplica -- ver seccion 5. No existe una ruta de streaming real en el sistema hoy;
no se genero evidencia fabricada de algo que no esta implementado.

## 7. Evidencia multi-turn

`test_t6_e2e_multiturn_reasoning_never_leaks_across_turns` -- turno 1 (pregunta de
pedido, dispara razonamiento real) seguido de turno 2 (seguimiento, misma
`conversation_id`) contra LM Studio real: ninguno de los dos turnos contiene
`<think`, `reasoning_content`, ni frases de razonamiento ("el usuario...") en su
`response` publico; el texto del turno 1 no se repite literalmente en el turno 2.

## 8. Evidencia de tool calling

`test_t12_tool_calling_still_works_after_the_fix` (E2E, LM Studio real):
`OrderStatusTool` se dispara correctamente (`tool_calls` no vacio), `intent`/`agent`
correctos, respuesta publica generada y limpia.

**Confirmado ademas en produccion real**, tras el redeploy (no solo en el test):
2 mensajes reales via el servicio ya desplegado --
- *"Cual es el estado de mi pedido?"* → `OrderStatusTool` disparado, tabla markdown
  limpia con los pedidos reales, sin ningun razonamiento visible.
- *"Que garantia tienen los equipos?"* → `EquipmentSearchTool` disparado (router
  determinista clasifico como `renting_search`, comportamiento ya existente y
  correcto), respuesta limpia explicando que no hay informacion de garantia
  disponible, sin razonamiento visible.

## 9. Riesgos pendientes (reales, no exhaustivos por exhaustividad)

- **`ai_editor` no comparte este fix:** el pipeline de `ai_editor` (`generation.py`,
  LangChain-based, ver ADK-07/ADK-09) es un sistema separado que NO usa
  `ai_engine_adk`/`public_response.py` -- si `ai_editor` llega a integrarse con ADK/
  LiteLLM en el futuro (fuera de alcance de esta correccion, ver FASE 7 de la
  mision: *"thinking = ON, reasoning = INTERNAL ONLY"* para ese caso), necesitara su
  propia revision con el mismo criterio, no automaticamente heredado de este fix.
- **Backend persistente de sesion (ADK-08, ya documentado, sin relacion con este
  bug):** sigue pendiente de eleccion -- no cambia por este fix.
- **`enable_thinking=False` a nivel de proveedor: intentado, NO funciono.** Se probo
  `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` (convencion real
  usada por otros motores de serving como vLLM/SGLang para modelos hibridos) contra
  el LM Studio real -- `reasoning_content` siguio poblado, sin cambio observable.
  Esto sugiere que el toggle de "thinking" de este modelo/version de LM Studio es un
  ajuste de la interfaz grafica de LM Studio (carga del modelo), no un parametro por
  peticion de la API OpenAI-compatible -- fuera de mi alcance verificar/cambiar de
  forma remota. **No es necesario para que la correccion funcione** -- el mapper ya
  garantiza la separacion aunque el modelo siga "pensando" en cada turno; esto solo
  habria sido una optimizacion de costo/latencia adicional (menos tokens de
  razonamiento generados), no una medida de seguridad.
- **`main.py`'s `metrics` field:** sigue `None` (TurnMetrics real, pendiente desde
  ADK-11 original, sin relacion con este bug).

## 10. Recomendacion de modelo

**No fue necesario cambiar Qwen3.5 para corregir la fuga de razonamiento.** La causa
raiz era 100% de la capa de adaptacion propia de SINTEL (`sintel_root_workflow.py`),
no del modelo, no del backend (LM Studio), no de LiteLLM, no de Google ADK. Los
cuatro componentes de la cadena real, verificados uno por uno con evidencia (no
suposicion), ya se comportaban correctamente o exactamente como esta documentado
oficialmente -- el unico eslabon roto era codigo propio de esta migracion, ahora
corregido.

Evaluar Gemma (u otro modelo) como benchmark A/B queda, como se pidio, fuera de esta
tarea -- y si se hace, debe hacerse manteniendo EXACTAMENTE el mismo contrato
(`reasoning=INTERNAL`, `tool_calls=INTERNAL`, `tool_results=INTERNAL`,
`final_content=PUBLIC`) ya construido aqui, no como una forma alternativa de "ocultar"
el sintoma sin entender la causa.
