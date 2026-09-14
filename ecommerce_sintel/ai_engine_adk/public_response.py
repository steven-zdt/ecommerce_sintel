"""
Frontera publica explicita entre eventos REALES de ADK
(`google.adk.events.Event`) y lo que SINTEL expone al cliente (WebSocket
widget web, WhatsApp via Celery). Ver auditoria del leak de razonamiento de
Qwen3.5/LM Studio (mision "auditoria y correccion integral del leak de
reasoning", 2026-09-14) y AUDITORIA/ADK_CUTOVER_PLAN.md.

## Causa raiz real (verificada, no hipotesis)

1. LM Studio SI separa razonamiento de contenido a nivel de proveedor --
   confirmado con una llamada `litellm.completion()` cruda: el mensaje real
   trae `reasoning_content` (razonamiento) Y `content` (respuesta limpia)
   como campos DISTINTOS. El modelo/proveedor no es la causa.
2. ADK (`google/adk/models/lite_llm.py`, instalado, real) YA convierte
   `reasoning_content`/`reasoning` (la propia libreria documenta:
   "'reasoning' (usado por LM Studio, vLLM)") en `types.Part(text=...,
   thought=True)` -- un campo REAL del framework
   (`google.genai.types.Part.thought`), no algo inventado aqui. LiteLLM/ADK
   tampoco es la causa.
3. El leak real estaba en `sintel_root_workflow.py::run_sintel_turn()`: el
   `final_text` se armaba concatenando TODOS los `Part.text` de TODOS los
   eventos, sin filtrar `part.thought` -- unico punto de fuga real,
   localizado con precision.

## Por que este modulo, y no una arquitectura paralela

No se crean clases `InternalReasoning`/`PublicContent`/`ToolCall` nuevas --
ADK YA tiene ese contrato semantico (`Part.thought`,
`Event.get_function_calls()`/`get_function_responses()`). Este modulo es el
UNICO punto de conversion Event -> payload publico -- un "PublicResponseMapper"
delgado sobre tipos reales de ADK, no un servicio paralelo.

## Multi-turn (verificado, no requiere cambio aqui)

`lite_llm.py` (mismo modulo real) YA reconstruye el historial saliente
separando `reasoning_content` de `content` en el mensaje assistant de
vuelta al proveedor (linea ~1458: `_assistant_message(content=final_content,
tool_calls=..., reasoning_content=reasoning_content or None)`) -- ADK no
reenvia thought como contenido normal en turnos siguientes. Nada que
corregir en ese punto.

## Streaming (verificado, no aplica hoy)

`Runner.run_async()` en este pipeline no usa un `run_config` de streaming
-- no hay una ruta de streaming activa en `ai_engine_adk`/`main.py` (un
solo POST /chat, sin SSE/WS en este servicio; el WebSocket real vive en
Django, `support/consumers.py`, y consume el `response` YA agregado de este
servicio, nunca eventos ADK crudos). Este mapper es agnostico a streaming
(filtra por `part.thought` sin importar si los parts llegan en un batch o
incrementalmente) -- seria correcto si se activara streaming en el futuro,
pero construir esa ruta esta fuera de alcance de esta correccion (no
convertir el fix en una migracion de arquitectura).
"""
import logging
import re

logger = logging.getLogger("public_response")

# Confirmacion sintetica que emite ADK al pausar (ver sintel_root_workflow.py)
# -- no es una tool de negocio real, se excluye de tool_calls/tool_results.
REQUEST_CONFIRMATION_FUNCTION_CALL_NAME = "adk_request_confirmation"

# Filtro DEFENSIVO (secundario, no el mecanismo principal -- la separacion
# real ya ocurre via Part.thought). Verificado que Qwen3.5/LM Studio NO usa
# este formato (separa via reasoning_content limpio) -- este filtro protege
# contra un proveedor/modelo FUTURO que si emita razonamiento inline con
# tags, sin que ADK lo haya podido clasificar estructuralmente.
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def extract_public_response(events, *, conversation_id: str = "") -> tuple[str, str, list[dict], list[dict]]:
    """UNICO punto de conversion de eventos reales de ADK al payload publico
    de SINTEL. Ningun otro lugar del codigo debe leer `event.content.parts`
    directamente para construir una respuesta destinada al cliente.

    Devuelve (public_content, internal_reasoning, tool_calls, tool_results).

    `internal_reasoning` es SOLO para observabilidad interna (logging) --
    ningun llamador debe incluirlo en una respuesta HTTP/WebSocket. No se
    persiste por defecto (ver docstring de logging mas abajo) para
    minimizar retencion innecesaria de un dato interno.
    """
    public_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: list[dict] = []
    tool_results: list[dict] = []

    for event in events:
        for fc in event.get_function_calls():
            if fc.name != REQUEST_CONFIRMATION_FUNCTION_CALL_NAME:
                tool_calls.append({"name": fc.name, "args": dict(fc.args or {})})
        for fr in event.get_function_responses():
            if fr.name != REQUEST_CONFIRMATION_FUNCTION_CALL_NAME:
                tool_results.append({"name": fr.name, "response": fr.response})

        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            if not part.text:
                continue
            # `Part.thought` es el campo REAL de ADK (google.genai.types)
            # que distingue razonamiento interno de contenido publico -- ya
            # poblado por google/adk/models/lite_llm.py desde
            # reasoning_content/reasoning del proveedor (verificado contra
            # Qwen3.5/LM Studio real). Este `if` ES la correccion
            # arquitectonica -- nunca se agregan Parts de razonamiento a
            # `public_parts`.
            if part.thought:
                reasoning_parts.append(part.text)
            else:
                public_parts.append(part.text)

    public_content = "".join(public_parts)
    internal_reasoning = "".join(reasoning_parts)

    if internal_reasoning:
        # Observabilidad interna (FASE 16 de la mision) -- nivel INFO,
        # nunca en una respuesta publica. Solo se loguea longitud, no el
        # contenido completo del razonamiento (dato interno, minimizar
        # exposicion incluso en logs).
        logger.info(
            "[reasoning] turno con razonamiento interno separado correctamente "
            "conversation_id=%s reasoning_chars=%d public_chars=%d",
            conversation_id, len(internal_reasoning), len(public_content),
        )

    # Filtro defensivo (ver docstring del modulo) -- si esto dispara, es un
    # DEFECTO TECNICO real (la separacion estructural de arriba fallo para
    # este proveedor/formato), se loguea como ERROR explicito, nunca en
    # silencio.
    if _THINK_TAG_RE.search(public_content):
        logger.error(
            "PUBLIC_REASONING_LEAK_DETECTED conversation_id=%s -- se encontraron "
            "tags <think>...</think> en contenido YA clasificado como publico "
            "(Part.thought no separo este caso). Esto indica un proveedor/modelo "
            "que no sigue el formato reasoning_content esperado -- revisar.",
            conversation_id,
        )
        public_content = _THINK_TAG_RE.sub("", public_content).strip()

    return public_content, internal_reasoning, tool_calls, tool_results
