"""
HARDENING F9 (2026-09-24) -- observabilidad. Propuesta: ai_engine_adk/.AGENT/HARDENING_F9_PROPOSAL_2026-09-24.md.

ESCRITO PERO NO EJECUTADO (regla vigente del usuario: no correr tests sin su autorizacion). Deterministas, sin LLM ni red.
"""
import json
import logging

import pytest

import observability_logging as obs

JWT = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjN9.abcdefghijklmnopqrstuvwxyz012345"
SECRET = "s3cr3t-service-token-de-prueba-0123456789"


def _record(msg, level=logging.INFO):
    return logging.LogRecord("t", level, __file__, 1, msg, (), None)


# -- correlacion
def test_valid_id_acepta_solo_forma_segura():
    assert obs.valid_id("req-abc12345") == "req-abc12345"
    for bad in (None, "", "corto", "con espacios!!", "x" * 65, "a;b;c;d;e;f;g;h", 123):
        assert obs.valid_id(bad) is None


def test_contexto_se_fija_y_se_restaura():
    tokens = obs.set_context(request_id="req-abc12345", session_id="room-1234567")
    assert obs.current_request_id() == "req-abc12345"
    obs.reset_context(tokens)
    assert obs.current_request_id() is None


def test_filtro_agrega_request_id_al_registro():
    tokens = obs.set_context(request_id="req-abc12345", session_id=None)
    try:
        record = _record("hola")
        obs.ContextFilter().filter(record)
    finally:
        obs.reset_context(tokens)
    assert record.request_id == "req-abc12345" and record.rid_suffix == " rid=req-abc12345"


# -- privacidad
def test_redaccion_de_jwt_bearer_y_secreto_del_entorno(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", SECRET)
    text = obs.redact(f"jwt {JWT} y Bearer abcdefghijklmnop1234567890 y {SECRET}")
    assert JWT not in text and "abcdefghijklmnop1234567890" not in text and SECRET not in text
    assert text.count(obs.REDACTED) == 3


def test_filtro_de_redaccion_limpia_el_mensaje_formateado(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_TOKEN", SECRET)
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "token=%s", (SECRET,), None)
    obs.RedactionFilter().filter(record)
    assert SECRET not in record.getMessage()


# -- taxonomia / JSON
@pytest.mark.parametrize("message,stream", [
    ("security_event=ai_tool_args_invalid tool=X", "SECURITY"),
    ('ai_turn_metrics {"a": 1}', "PERFORMANCE"),
    ("ai_operation_event=provider_failed provider=ollama", "AI_OPERATION"),
    ("ai_tool_audit invocation_id=1", "AI_OPERATION"),
    ("memory_event=saved", "AI_OPERATION"),
    ("marketing_event=sent", "BUSINESS"),
    ("cualquier otra cosa", "APP"),
])
def test_stream_por_prefijo(message, stream):
    assert obs.stream_for(message) == stream


def test_json_formatter_una_linea_con_stream_y_campos():
    tokens = obs.set_context(request_id="req-abc12345", session_id="room-1234567")
    try:
        record = _record("ai_operation_event=provider_failed provider=ollama error=Timeout")
        obs.ContextFilter().filter(record)
        line = obs.JsonFormatter().format(record)
    finally:
        obs.reset_context(tokens)
    data = json.loads(line)
    assert "\n" not in line and data["stream"] == "AI_OPERATION" and data["request_id"] == "req-abc12345"
    assert data["fields"]["provider"] == "ollama" and data["fields"]["error"] == "Timeout"


def test_log_format_default_es_texto(monkeypatch):
    monkeypatch.delenv("LOG_FORMAT", raising=False)
    assert obs.log_format() == "text"
    monkeypatch.setenv("LOG_FORMAT", "JSON")
    assert obs.log_format() == "json"


# -- metricas por turno
def test_payload_de_turno_sin_contenido_y_con_traza_y_tokens():
    metrics = {
        "request_id": "req-abc12345", "agent": "SupportAgent", "intent": "support", "duration_ms": 1200,
        "llm_tokens_in": 100, "llm_tokens_out": 20, "tokens_per_s": 10.0, "tool_calls": 2,
        "model_trace": {"provider": "ollama", "model": "qwen3.5:9b", "fallback_used": False, "breaker_state": "CLOSED", "attempts": 1},
        "output_flags": ["reasoning_stripped"], "response": "NO DEBE SALIR", "message": "NO DEBE SALIR",
    }
    payload = obs.build_turn_payload(metrics, status="ok", source="customer", channel="web")
    assert payload["provider"] == "ollama" and payload["llm_tokens_in"] == 100 and payload["output_flags"] == ["reasoning_stripped"]
    assert "response" not in payload and "message" not in payload and "NO DEBE SALIR" not in json.dumps(payload)


def test_emit_turn_metrics_una_linea_json(caplog):
    with caplog.at_level(logging.INFO, logger="ai_turn_metrics"):
        obs.emit_turn_metrics({"request_id": "req-abc12345"}, status="degraded")
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("ai_turn_metrics ")]
    assert len(lines) == 1 and json.loads(lines[0][len("ai_turn_metrics "):])["status"] == "degraded"


def test_tokens_per_second():
    assert obs.tokens_per_second(100, 2000) == 50.0
    assert obs.tokens_per_second(0, 2000) is None and obs.tokens_per_second(10, None) is None


# -- suma de tokens en model_runtime
async def test_usage_metadata_se_suma_por_llamada():
    import model_runtime as mr

    class Meta:
        prompt_token_count, candidates_token_count = 100, 10

    class Resp:
        usage_metadata = Meta()

    mr.begin_turn_trace()
    for _ in range(2):
        mr._add_usage(Resp())
        mr._close_call_usage()
    assert mr.get_turn_usage() == {"llm_calls": 2, "prompt_tokens": 200, "completion_tokens": 20}


def test_chat_usa_la_cabecera_como_request_id(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from auth import get_validated_token, require_service_token

    seen = {}

    async def fake_turn(**_kw):
        seen["rid"] = obs.current_request_id()
        return {"conversation_id": "c1", "intent": "x", "agent": "SupportAgent", "tool_calls": [], "tool_results": [],
                "needs_confirmation": False, "confirmation": None, "response": "ok", "metrics": {}}

    monkeypatch.setattr(main, "run_sintel_turn", fake_turn)
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    try:
        TestClient(main.app).post("/chat", json={"message": "hola", "conversation_id": "c1"}, headers={"X-Request-ID": "req-abc12345"})
    finally:
        main.app.dependency_overrides.clear()
    assert seen["rid"] == "req-abc12345"
