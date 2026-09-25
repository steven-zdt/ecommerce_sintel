"""
HARDENING F9 (2026-09-24) -- observabilidad: correlacion, taxonomia de logs, JSON opt-in, metricas por turno y privacidad de logs.

Plan: PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md sec. 13; propuesta y decisiones:
ai_engine_adk/.AGENT/HARDENING_F9_PROPOSAL_2026-09-24.md.

Solo biblioteca estandar y SIN imports del resto del proyecto: lo usan el ADK (`import observability_logging`) y Django
(`ai_engine_adk.observability_logging`, mismo criterio que input_guard en ai_knowledge/ingestion.py).

Contenido:
- ContextVars `request_id_var` / `session_id_var` + `ContextFilter` (agrega request_id/session_id a TODOS los registros).
- `RedactionFilter`: red de seguridad global -- redacta JWT, Bearer y el valor EXACTO de secretos del entorno en cualquier mensaje.
- `JsonFormatter` (LOG_FORMAT=json): una linea por evento con `stream` (SECURITY / AI_OPERATION / PERFORMANCE / BUSINESS / APP),
  request_id, session_id y los pares key=value del mensaje como campos. El formato texto sigue siendo el default.
- `emit_turn_metrics`: UNA linea `ai_turn_metrics {json}` por turno del ADK (stream PERFORMANCE), sin contenido de mensajes.
"""
import contextvars
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar = contextvars.ContextVar("sintel_request_id", default=None)
session_id_var: contextvars.ContextVar = contextvars.ContextVar("sintel_session_id", default=None)

_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
REDACTED = "[dato oculto]"


# -- Correlacion ---------------------------------------------------------------------------------
def valid_id(value) -> str | None:
    """Acepta solo ids con forma segura (8-64 caracteres alfanumericos . _ -); cualquier otra cosa -> None (se regenera)."""
    return value if isinstance(value, str) and _ID_RE.match(value) else None


def new_request_id(prefix: str = "req") -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def current_request_id() -> str | None:
    return request_id_var.get()


def current_session_id() -> str | None:
    return session_id_var.get()


def set_context(request_id=None, session_id=None):
    """Fija el contexto de la peticion actual; devuelve los tokens para restaurarlo."""
    return (request_id_var.set(valid_id(request_id)), session_id_var.set(valid_id(session_id) or (str(session_id)[:80] if session_id else None)))


def reset_context(tokens) -> None:
    request_id_var.reset(tokens[0])
    session_id_var.reset(tokens[1])


class ContextFilter(logging.Filter):
    """Agrega request_id / session_id (y `rid_suffix` para el formato texto) a cada registro."""

    def filter(self, record: logging.LogRecord) -> bool:
        rid, sid = request_id_var.get(), session_id_var.get()
        record.request_id = rid or "-"
        record.session_id = sid or "-"
        record.rid_suffix = f" rid={rid}" if rid else ""
        return True


# -- Privacidad ----------------------------------------------------------------------------------
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
_BEARER_RE = re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}")
_SECRET_ENV_NAMES = (
    "AI_SERVICE_TOKEN", "AI_SERVICE_TOKEN_PREVIOUS", "JWT_SECRET_KEY", "SECRET_KEY", "DB_PASSWORD", "POSTGRES_PASSWORD",
    "REDIS_PASSWORD", "EMAIL_HOST_PASSWORD", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "WOMPI_PRIVATE_KEY",
    "WOMPI_INTEGRITY_SECRET", "WOMPI_EVENTS_SECRET", "WA_GATEWAY_INTERNAL_TOKEN", "META_ACCESS_TOKEN",
)


def redact(text: str) -> str:
    if not text:
        return text
    for name in _SECRET_ENV_NAMES:
        value = os.environ.get(name, "")
        if len(value) >= 16 and value in text:
            text = text.replace(value, REDACTED)
    text = _JWT_RE.sub(REDACTED, text)
    return _BEARER_RE.sub(REDACTED, text)


class RedactionFilter(logging.Filter):
    """Ningun secreto llega a un log, venga de donde venga (httpx, una excepcion de terceros, un f-string descuidado)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        clean = redact(message)
        if clean != message:
            record.msg, record.args = clean, ()
        return True


# -- Taxonomia y JSON ----------------------------------------------------------------------------
_STREAM_RULES = (
    ("SECURITY", ("security_event=",)),
    ("PERFORMANCE", ("ai_turn_metrics",)),
    ("AI_OPERATION", ("ai_operation_event=", "ai_tool_audit", "memory_event=")),
    ("BUSINESS", ("marketing_event=",)),
)
_KV_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(\[[^\]]*\]|\"[^\"]*\"|'[^']*'|\S+)")


def stream_for(message: str) -> str:
    for stream, prefixes in _STREAM_RULES:
        if any(p in message for p in prefixes):
            return stream
    return "APP"


class JsonFormatter(logging.Formatter):
    """LOG_FORMAT=json: una linea JSON por evento. Los pares key=value del mensaje pasan a `fields`."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "stream": stream_for(message),
            "request_id": getattr(record, "request_id", None) or request_id_var.get() or "-",
            "session_id": getattr(record, "session_id", None) or session_id_var.get() or "-",
            "message": message,
        }
        if message.startswith("ai_turn_metrics "):
            try:
                payload["fields"] = json.loads(message[len("ai_turn_metrics "):])
            except ValueError:
                pass
        else:
            fields = {k: v.strip("'\"") for k, v in _KV_RE.findall(message)[:30]}
            if fields:
                payload["fields"] = fields
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def log_format() -> str:
    return "json" if os.environ.get("LOG_FORMAT", "text").strip().lower() == "json" else "text"


def configure_root(level: int = logging.INFO) -> None:
    """Configura el logging del ADK: filtros de contexto/redaccion siempre; formato JSON solo con LOG_FORMAT=json."""
    handler = logging.StreamHandler(sys.stderr)
    if log_format() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s%(rid_suffix)s"))
    handler.addFilter(ContextFilter())
    handler.addFilter(RedactionFilter())
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)


# -- Metricas por turno --------------------------------------------------------------------------
_TURN_FIELDS = (
    "agent", "intent", "handoff", "escalation", "tool_calls", "needs_confirmation", "retrieval_used", "knowledge_state",
    "grounding_result", "duration_ms", "retrieval_latency_ms", "agent_latency_ms", "grounding_latency_ms", "memory_used",
    "rate_limited", "engine_unavailable", "turn_timeout", "llm_tokens_in", "llm_tokens_out", "tokens", "tokens_per_s", "queue_wait_ms", "queue_rejected", "queue_reason",
)
_TRACE_FIELDS = ("provider", "model", "fallback_used", "fallback_reason", "breaker_state", "attempts", "provider_id", "config_version")


def build_turn_payload(metrics: dict | None, *, status: str, source: str = "", channel: str = "") -> dict:
    """Payload de `ai_turn_metrics` SIN contenido: solo cifras, ids y categorias."""
    metrics = metrics or {}
    payload: dict = {
        "request_id": metrics.get("request_id") or request_id_var.get() or "-",
        "session_id": session_id_var.get() or "-",
        "status": status,
        "source": source or None,
        "channel": channel or None,
    }
    for key in _TURN_FIELDS:
        if key in metrics and metrics[key] is not None:
            payload[key] = metrics[key]
    trace = metrics.get("model_trace") or {}
    for key in _TRACE_FIELDS:
        if trace.get(key) is not None:
            payload[key] = trace[key]
    for key in ("injection_flags", "output_flags"):
        if metrics.get(key):
            payload[key] = metrics[key]
    return payload


def emit_turn_metrics(metrics: dict | None, *, status: str, source: str = "", channel: str = "") -> dict:
    payload = build_turn_payload(metrics, status=status, source=source, channel=channel)
    logging.getLogger("ai_turn_metrics").info("ai_turn_metrics %s", json.dumps(payload, sort_keys=True, default=str))
    return payload


def tokens_per_second(completion_tokens: int, elapsed_ms: int | float | None) -> float | None:
    if not completion_tokens or not elapsed_ms:
        return None
    return round(completion_tokens / (elapsed_ms / 1000.0), 1)


def monotonic_ms() -> float:
    return time.monotonic() * 1000.0
