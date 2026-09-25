"""
mcp_server/audit.py -- logging estructurado JSON + auditoria de llamadas (plan MCP sec. 15, 45).

Cada llamada de escritura (y cada denegacion) deja UNA linea JSON con caller, principal, recurso, tool, operacion, objetivo, campos cambiados, riesgo, confirmacion,
request_id, trace_id, marca de tiempo y resultado. Nunca se registran passwords, JWT, API keys, OTP ni cabeceras Authorization (redact + el token jamas entra al contexto).
"""
import contextvars
import json
import logging
import sys
import time
import uuid
from collections import Counter

from . import sanitize

request_id_var = contextvars.ContextVar("mcp_request_id", default="-")
trace_id_var = contextvars.ContextVar("mcp_trace_id", default="-")
session_id_var = contextvars.ContextVar("mcp_session_id", default="-")

audit_logger = logging.getLogger("mcp.audit")
app_logger = logging.getLogger("mcp")

# Contadores en memoria para /mcp-health y metricas (plan sec. 45). Sin datos de negocio.
METRICS = Counter()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + "Z",
            "level": record.levelname, "logger": record.name, "msg": record.getMessage(),
            "request_id": request_id_var.get(), "trace_id": trace_id_var.get(),
        }
        extra = getattr(record, "mcp", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"  # sin traceback: puede llevar valores
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # httpx registra URLs completas de cada llamada: se baja a WARNING para no filtrar ids en logs de acceso.
    logging.getLogger("httpx").setLevel(logging.WARNING)


def new_ids() -> tuple:
    request_id_var.set("req-" + uuid.uuid4().hex[:16])
    trace_id_var.set("trc-" + uuid.uuid4().hex[:16])
    return request_id_var.get(), trace_id_var.get()


DURABLE_EVENTS = {"write_result", "write_conflict", "tool_denied"}


def durable_payload(event: str, **f) -> dict:
    """Solo nombres/ids/codigos (nada de valores de datos): lo que se envia a Django."""
    keys = ("tool", "resource", "operation", "target", "risk", "confirmation", "result", "changed_fields")
    payload = {k: f[k] for k in keys if f.get(k) not in (None, "", "-", [])}
    if "changed_fields" in payload:
        payload["changed_fields"] = sorted(str(x) for x in payload["changed_fields"])
    payload["event"] = event
    payload["request_id"] = request_id_var.get()
    payload["trace_id"] = trace_id_var.get()
    return payload


def audit(event: str, *, principal: str = "-", tool: str = "-", resource: str = "-", operation: str = "-", target: str = "-",
          changed_fields=None, risk: str = "-", confirmation: str = "-", result: str = "-", **extra) -> None:
    METRICS[f"event.{event}"] += 1
    METRICS[f"result.{result}"] += 1
    fields = {
        "event": event, "principal": principal, "tool": tool, "resource": resource, "operation": operation, "target": target,
        "changed_fields": sorted(changed_fields or []), "risk": risk, "confirmation": confirmation, "result": result,
        "session_id": session_id_var.get(),
    }
    fields.update(sanitize.redact(extra))
    audit_logger.info(event, extra={"mcp": fields})
