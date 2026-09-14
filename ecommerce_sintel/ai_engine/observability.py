"""
Observabilidad del AI Core (Componente 6, Fase 6).

Metricas por turno del Action Graph emitidas como UNA linea JSON via logging
estructurado (logger "observability"). Integracion Prometheus/Grafana/
OpenTelemetry: preparada pero NO instalada (misma decision de costo que el
roadmap de Cloudflare, Fase 18) — cuando el usuario decida instalarla, basta
un handler/exporter sobre este logger sin tocar el grafo.

Uso: run_action_chat crea TurnMetrics y lo pasa por config["configurable"]
["metrics"] (mutable, NO viaja en el estado checkpointeado); los nodos
incrementan contadores; al final emit() escribe la linea.
"""
import json
import logging
import time

logger = logging.getLogger("observability")


class TurnMetrics:

    def __init__(self, conversation_id: str, user_id) -> None:
        self._start = time.monotonic()
        self.data: dict = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "agent": None,
            "intent": None,
            "llm_calls": 0,
            "llm_tokens_in": 0,
            "llm_tokens_out": 0,
            "tool_calls": 0,
            "tool_errors": 0,
            "tools": [],            # [{tool, ms, ok}]
            "fallback_used": False,
            "handoff": None,        # "AgenteA->AgenteB" si hubo derivacion
            "needs_confirmation": False,
            "write_executed": False,
            "duration_ms": None,
        }

    def record_llm(self, ai_msg) -> None:
        self.data["llm_calls"] += 1
        usage = getattr(ai_msg, "usage_metadata", None) or {}
        self.data["llm_tokens_in"] += usage.get("input_tokens", 0) or 0
        self.data["llm_tokens_out"] += usage.get("output_tokens", 0) or 0

    def record_tool(self, tool_name: str, elapsed_ms: int, ok: bool) -> None:
        self.data["tool_calls"] += 1
        if not ok:
            self.data["tool_errors"] += 1
        self.data["tools"].append({"tool": tool_name, "ms": elapsed_ms, "ok": ok})

    def emit(self) -> None:
        self.data["duration_ms"] = int((time.monotonic() - self._start) * 1000)
        try:
            logger.info("[metrics] %s", json.dumps(self.data, ensure_ascii=False, default=str))
        except Exception:
            logger.exception("[metrics] fallo emitiendo metricas")


def metrics_from_config(config: dict) -> TurnMetrics | None:
    return (config.get("configurable") or {}).get("metrics")
