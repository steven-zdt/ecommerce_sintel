"""
Correccion del leak de razonamiento de Qwen3.5/LM Studio hacia el cliente
(mision "auditoria y correccion integral", 2026-09-14). Ver
public_response.py para la causa raiz real y AUDITORIA/ADK_CUTOVER_PLAN.md.

T1-T3, T8, T9, T11: unitarios, con objetos REALES de ADK
(`google.adk.events.event.Event`, `google.genai.types.Content/Part`) --
no son mocks de la logica bajo prueba, son los MISMOS tipos que ADK usa en
produccion, construidos directamente para fijar casos deterministas sin
depender de un LLM real.

T6, T12: end-to-end contra LM Studio REAL (mismo backend de produccion,
mismo modelo `qwen/qwen3.5-9b`) -- confirman que la separacion estructural
sobrevive un flujo real completo, no solo la funcion pura.

T4/T5 (streaming) deliberadamente NO incluidos: no existe una ruta de
streaming activa en `ai_engine_adk`/`main.py` hoy (un solo POST /chat, sin
SSE/WS en este servicio) -- ver docstring de `public_response.py`.
Fabricar un test para una ruta de codigo que no existe violaria la regla
de la mision "no introducir stubs" / "validar contra el codigo real, no
snippets historicos".
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types
from google.adk.events.event import Event

from public_response import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME, extract_public_response


def _event(*, author="agent", text=None, thought=False, function_call=None, function_response=None):
    parts = []
    if text is not None:
        parts.append(types.Part(text=text, thought=thought))
    if function_call is not None:
        parts.append(types.Part(function_call=function_call))
    if function_response is not None:
        parts.append(types.Part(function_response=function_response))
    content = types.Content(role="model", parts=parts) if parts else None
    return Event(author=author, content=content)


# ── T1: respuesta simple sin tool ────────────────────────────────────────

def test_t1_simple_response_without_tool_has_no_reasoning():
    events = [_event(text="Hola, tu cuenta esta activa.")]
    public, reasoning, tool_calls, tool_results = extract_public_response(events)
    assert public == "Hola, tu cuenta esta activa."
    assert reasoning == ""
    assert tool_calls == []
    assert tool_results == []


# ── T2: reasoning + respuesta final ──────────────────────────────────────

def test_t2_reasoning_plus_final_response_only_final_is_public():
    events = [
        _event(text="El usuario quiere saber X, voy a responder Y.", thought=True),
        _event(text="Tu cuenta esta activa."),
    ]
    public, reasoning, _, _ = extract_public_response(events)
    assert public == "Tu cuenta esta activa."
    assert "voy a responder" in reasoning
    assert "voy a responder" not in public


# ── T3: reasoning + tool_call + tool_result + respuesta final ────────────

def test_t3_reasoning_tool_call_tool_result_final_response():
    fc = types.FunctionCall(id="call_1", name="OrderStatusTool", args={"limit": 5})
    fr = types.FunctionResponse(id="call_1", name="OrderStatusTool", response={"orders": []})
    events = [
        _event(text="Necesito consultar el pedido con OrderStatusTool.", thought=True),
        _event(function_call=fc),
        _event(function_response=fr),
        _event(text="No tienes pedidos recientes.", thought=True),  # reasoning post-tool
        _event(text="No tienes pedidos recientes."),
    ]
    public, reasoning, tool_calls, tool_results = extract_public_response(events)
    assert public == "No tienes pedidos recientes."
    assert "Necesito consultar" in reasoning
    assert tool_calls == [{"name": "OrderStatusTool", "args": {"limit": 5}}]
    assert tool_results == [{"name": "OrderStatusTool", "response": {"orders": []}}]
    # el reasoning post-tool NUNCA debe aparecer en publico, ni duplicado
    assert public.count("No tienes pedidos recientes.") == 1


def test_t3_confirmation_synthetic_call_excluded_from_tool_calls():
    """adk_request_confirmation no es una tool de negocio real -- no debe
    aparecer en tool_calls/tool_results publicos."""
    fc = types.FunctionCall(id="fc_1", name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME, args={})
    fr = types.FunctionResponse(id="fc_1", name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME, response={})
    events = [_event(function_call=fc), _event(function_response=fr)]
    _, _, tool_calls, tool_results = extract_public_response(events)
    assert tool_calls == []
    assert tool_results == []


# ── T8: reasoning con <think> literal debe permanecer interno ───────────

def test_t8_reasoning_with_think_tags_stays_internal():
    """Aunque el texto de razonamiento contenga literalmente <think>...
    </think>, si Part.thought=True, la separacion PRIMARIA (no el filtro
    defensivo) ya lo mantiene fuera de lo publico."""
    events = [
        _event(text="<think>el usuario pregunta por su pedido</think>", thought=True),
        _event(text="Tu pedido esta en camino."),
    ]
    public, reasoning, _, _ = extract_public_response(events)
    assert public == "Tu pedido esta en camino."
    assert "<think>" not in public
    assert "<think>" in reasoning


# ── T9: filtro defensivo no destruye contenido legitimo ──────────────────

def test_t9_defensive_filter_strips_real_think_tag_leak():
    """Caso realista del filtro DEFENSIVO (no el mecanismo principal): un
    Part marcado incorrectamente como publico (thought=False/None) que aun
    asi trae tags <think> completos -- simula un proveedor futuro que no
    separe igual que LM Studio."""
    events = [_event(text="<think>razonamiento colado</think>Tu pedido esta en camino.")]
    public, _, _, _ = extract_public_response(events)
    assert public == "Tu pedido esta en camino."
    assert "<think>" not in public
    assert "razonamiento colado" not in public


def test_t9_defensive_filter_does_not_destroy_legitimate_content_without_full_tag():
    """Una cadena parecida ('think', un tag suelto sin cierre) NO debe
    disparar el filtro y destruir contenido real -- solo pares completos
    <think>...</think>."""
    events = [_event(text="Creo (I think) que tu pedido llega manana.")]
    public, _, _, _ = extract_public_response(events)
    assert public == "Creo (I think) que tu pedido llega manana."


def test_t9_defensive_filter_logs_error_when_triggered(caplog):
    import logging
    events = [_event(text="<think>x</think>Respuesta real.")]
    with caplog.at_level(logging.ERROR, logger="public_response"):
        extract_public_response(events, conversation_id="conv-test-9")
    assert any("PUBLIC_REASONING_LEAK_DETECTED" in r.message for r in caplog.records)


# ── T11: el payload publico nunca contiene campos internos de reasoning ──

def test_t11_chat_response_schema_has_no_reasoning_fields():
    from main import ChatResponse
    forbidden = {"reasoning", "reasoning_content", "thinking_blocks", "thought", "planning"}
    assert forbidden.isdisjoint(ChatResponse.model_fields.keys())


@pytest.mark.asyncio
async def test_t6_e2e_multiturn_reasoning_never_leaks_across_turns():
    """E2E contra LM Studio real: turno 1 provoca razonamiento real; turno 2
    (seguimiento) no debe traer el razonamiento del turno 1 en su
    respuesta publica ni duplicado."""
    from unittest.mock import AsyncMock, patch
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": 42, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": 42, "email": "t6@sintel.dev", "user_type": "customer"}
    order_response = {"results": [{"uuid": "ord-t6", "status": "shipped"}]}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)), \
         patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)):
        turn1 = await run_sintel_turn(
            message="Cual es el estado de mi pedido?", token=token, conversation_id="t6-conv",
        )
        turn2 = await run_sintel_turn(
            message="Gracias, y el envio ya salio?", token=token, conversation_id="t6-conv",
        )

    for turn in (turn1, turn2):
        assert "<think" not in turn["response"].lower()
        assert "reasoning_content" not in turn["response"]
        assert "el usuario" not in turn["response"].lower(), (
            f"posible razonamiento filtrado en la respuesta publica: {turn['response']!r}"
        )
    # el turno 2 no debe repetir literalmente el texto de razonamiento del turno 1
    assert turn1["response"] not in turn2["response"] or turn1["response"] == ""


@pytest.mark.asyncio
async def test_t12_tool_calling_still_works_after_the_fix():
    """Regresion critica: la correccion del leak NO debe romper tool
    calling real -- mismo caso ya probado en produccion (ADK_CUTOVER_PLAN
    seccion 4quater), fijado aqui como test permanente."""
    from unittest.mock import AsyncMock, patch
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": 43, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": 43, "email": "t12@sintel.dev", "user_type": "customer"}
    order_response = {"results": [{"uuid": "ord-t12", "status": "paid"}]}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)), \
         patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)):
        result = await run_sintel_turn(
            message="Cual es el estado de mi pedido?", token=token, conversation_id="t12-conv",
        )

    assert result["intent"] == "order_status"
    assert result["agent"] == "OrderAgent"
    assert any(tc["name"] == "OrderStatusTool" for tc in result["tool_calls"]), (
        f"OrderStatusTool no se disparo: {result['tool_calls']}"
    )
    assert result["response"], "El turno no genero respuesta publica"
    assert "<think" not in result["response"].lower()
