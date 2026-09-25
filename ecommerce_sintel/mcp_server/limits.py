"""
mcp_server/limits.py -- rate limit y presupuestos (plan MCP sec. 16).

Ventana deslizante en memoria (un proceso): global, por principal, por operacion y por recurso. Ademas topes de registros por peticion, profundidad de paginacion y bytes de
payload, para que una enumeracion accidental de todo el ecommerce sea imposible. En memoria => se reinicia con el proceso; con varias replicas cada una cuenta aparte (limite documentado).
"""
import json
import time
from collections import defaultdict, deque

from . import errors
from .config import Settings
from .errors import McpToolError

WINDOW_SECONDS = 60


class SlidingWindow:
    def __init__(self, clock=time.monotonic):
        self._hits = defaultdict(deque)
        self._clock = clock

    def hit(self, key: str, limit: int, window: int = WINDOW_SECONDS) -> bool:
        """True si la llamada entra en el cupo (y la cuenta); False si ya se alcanzo el limite."""
        now = self._clock()
        q = self._hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


class Limiter:
    def __init__(self, settings: Settings, clock=time.monotonic):
        self.s = settings
        self.window = SlidingWindow(clock)

    def check(self, principal: str, tool: str, resource: str | None, is_write: bool) -> None:
        s = self.s
        checks = [("global", "global", s.rate_limit_per_minute * 10),
                  (f"p:{principal}", "principal", s.rate_limit_per_minute),
                  (f"o:{principal}:{tool}", "operacion", s.write_rate_limit_per_minute if is_write else s.rate_limit_per_minute)]
        if resource:
            checks.append((f"r:{principal}:{resource}", "recurso", s.write_rate_limit_per_minute * 3 if is_write else s.rate_limit_per_minute))
        for key, label, limit in checks:
            if not self.window.hit(key, limit):
                raise McpToolError(errors.RATE_LIMITED, f"Limite de {limit} llamadas por minuto alcanzado ({label}). Espera y reintenta.", scope=label)

    def clamp_limit(self, limit) -> int:
        try:
            value = int(limit) if limit is not None else self.s.max_records
        except (TypeError, ValueError):
            raise McpToolError(errors.INVALID_ARGUMENT, "limit debe ser un entero.")
        if value < 1:
            raise McpToolError(errors.INVALID_ARGUMENT, "limit debe ser >= 1.")
        return min(value, self.s.max_records)

    def check_page(self, page) -> int:
        try:
            value = int(page) if page is not None else 1
        except (TypeError, ValueError):
            raise McpToolError(errors.INVALID_ARGUMENT, "page debe ser un entero.")
        if value < 1:
            raise McpToolError(errors.INVALID_ARGUMENT, "page debe ser >= 1.")
        if value > self.s.max_page_depth:
            raise McpToolError(errors.LIMIT_EXCEEDED, f"Profundidad de paginacion maxima: {self.s.max_page_depth}. Usa filtros para acotar.", max_page=self.s.max_page_depth)
        return value

    def check_payload(self, payload) -> None:
        size = len(json.dumps(payload, default=str).encode("utf-8"))
        if size > self.s.max_body_bytes // 4:
            raise McpToolError(errors.LIMIT_EXCEEDED, f"Payload de {size} bytes excede el maximo de {self.s.max_body_bytes // 4}.", max_bytes=self.s.max_body_bytes // 4)
