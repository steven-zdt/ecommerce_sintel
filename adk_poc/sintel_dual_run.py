"""
ADK-10 -- Dual run: comparar el runtime OLD (`action_graph.run_action_chat`,
LangGraph) contra el NEW (`sintel_root_workflow.run_sintel_turn`, ADK) con
la MISMA entrada, antes de considerar promover cualquiera a produccion.

## Alcance real (decision deliberada de riesgo, no un vacio accidental)

El OLD system real corre contra infraestructura REAL y ya viva de este
proyecto -- confirmado con `docker ps`: `ecommerce_sintel_redis` (puerto
host 6380), `ecommerce_sintel_ollama` (11434), `ecommerce_sintel_django`
(8000), `ecommerce_sintel_ai` (8100, el propio proceso ai_engine
corriendo). Este dual run usa Redis y Ollama REALES (mismo Redis del
`CHECKPOINTER_REDIS_URL` real, DB 2 -- namespace propio del checkpointer,
sin overlap con Channels/Cache) -- pero **NO** golpea el Django real ni
extrae el `JWT_SECRET_KEY` real de produccion para firmar un token valido:
`fetch_user_context` se mockea (unico punto de red hacia Django, mismo
criterio de toda la mision) con un fixture realista. Extraer un secreto
real de un contenedor vivo para autenticarse como si fuera un usuario real
es una accion de un tipo de riesgo distinto al resto de esta mision (toca
un secreto de produccion) -- fuera de alcance sin autorizacion explicita
del usuario, documentado como pendiente para ADK-11.

Usa un `user_id`/`conversation_id` sinteticos con un prefijo inconfundible
(`999999`/`dualrun-*`) para no poder colisionar con una conversacion real,
y limpia su propio thread de Redis al terminar (`RedisCheckpointSaver.
delete_thread`) -- no deja basura en la instancia real.

## Que se compara (y que NO)

Se comparan campos ESTRUCTURALES: `intent`, `agent`, si el turno tuvo
`tool_calls`, si la respuesta final vino no vacia. **No** se compara el
texto final palabra por palabra -- ambos lados usan el mismo LLM real
(`llama3.1:8b` via Ollama), pero la generacion de texto no es determinista
turno a turno; exigir igualdad textual haria el dual run inutilmente
fragil sin probar nada real sobre equivalencia funcional.
"""
import os

os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434")
os.environ.setdefault("CHECKPOINTER_REDIS_URL", "redis://localhost:6380/2")
# Hallazgo real: el LOCAL_MODEL_CHAIN real de este proyecto (leido por
# python-decouple desde el .env real, no el default del codigo) encadena
# ollama + LM Studio (openai-compatible, host.docker.internal:1234 -- el
# proveedor real de produccion). get_llm() intenta construir CADA motor de
# la cadena (para with_fallbacks()), y el motor openai-compatible requiere
# `langchain-openai`, que tiene un conflicto de version REAL y duro con
# `litellm` (dependencia de ADK): langchain-openai==0.2.14 exige
# openai<2.0.0, litellm exige openai>=2.20.0 -- rangos que NO se solapan.
# No hay una sola version de openai que sirva a ambos stacks en el MISMO
# venv. Implicacion real para ADK-11: OLD (LangChain) y NEW (ADK/LiteLLM)
# no pueden coexistir como imports del mismo proceso mientras OLD siga
# vivo -- un transicion real necesitaria procesos/servicios separados, no
# un solo proceso important ambos. Se fuerza aqui SOLO el motor ollama-nativo
# (evita construir el motor lmstudio en este dual run -- no se necesita
# LM Studio real para comparar routing/estructura) para no depender de esa
# resolucion todavia sin decidirla.
os.environ["LOCAL_MODEL_CHAIN"] = "ollama|ollama-nativo|http://localhost:11434|llama3.1:8b"

DUAL_RUN_USER_ID = 999999


async def run_old_system(*, message: str, token: str, conversation_id: str) -> dict:
    """Corre el turno REAL por el sistema OLD (action_graph.py,
    run_action_chat) -- Redis y Ollama reales, Django mockeado (ver
    docstring del modulo)."""
    from llm_factory import get_llm
    from action_graph import run_action_chat

    llm = get_llm()
    result = await run_action_chat(
        message=message, conversation_id=conversation_id, token=token,
        user_id=DUAL_RUN_USER_ID, llm=llm, confirm=None,
    )
    return result


async def cleanup_old_system_thread(conversation_id: str) -> None:
    """Borra el thread de prueba del Redis real -- el dual run no debe
    dejar basura en la instancia compartida del proyecto."""
    from config import CHECKPOINTER_REDIS_URL
    from redis_checkpointer import RedisCheckpointSaver

    saver = RedisCheckpointSaver(CHECKPOINTER_REDIS_URL)
    await saver.adelete_thread(f"{DUAL_RUN_USER_ID}:{conversation_id}")


async def run_new_system(*, message: str, token: str, conversation_id: str) -> dict:
    from sintel_root_workflow import run_sintel_turn

    return await run_sintel_turn(message=message, token=token, conversation_id=conversation_id)


async def dual_run(*, message: str, token: str, conversation_id: str) -> dict:
    """Corre AMBOS sistemas con la MISMA entrada y compara los campos
    estructurales clave. Limpia el thread del OLD system al terminar,
    incluso si algo falla."""
    try:
        old_result = await run_old_system(message=message, token=token, conversation_id=conversation_id)
    finally:
        await cleanup_old_system_thread(conversation_id)

    new_result = await run_new_system(message=message, token=token, conversation_id=conversation_id)

    discrepancies = []
    if old_result.get("intent") != new_result.get("intent"):
        discrepancies.append(
            f"intent: OLD={old_result.get('intent')!r} NEW={new_result.get('intent')!r}"
        )
    if old_result.get("agent") != new_result.get("agent"):
        discrepancies.append(
            f"agent: OLD={old_result.get('agent')!r} NEW={new_result.get('agent')!r}"
        )
    old_had_response = bool(old_result.get("response"))
    new_had_response = bool(new_result.get("response"))
    if old_had_response != new_had_response:
        discrepancies.append(
            f"respuesta vacia en un solo lado: OLD={old_had_response} NEW={new_had_response}"
        )

    return {"old": old_result, "new": new_result, "discrepancies": discrepancies}
