"""
mcp_server/confirmations.py -- fichas de confirmacion e idempotencia (plan MCP sec. 11-13).

Una escritura de riesgo medio/alto exige la ficha que devolvio su PREVIEW. La ficha (HMAC-SHA256) va atada al principal, la herramienta, el recurso, la operacion, el objetivo, el hash EXACTO
del payload y la version del registro: cambiar cualquiera invalida la ficha. Es de un solo uso y caduca. Es la prueba de que la accion se previsualizo con esos mismos parametros; la
decision humana la toma el cliente MCP al aprobar la llamada (limite conocido: si el cliente aprueba en automatico, el MCP no puede impedirlo).
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

from . import errors
from .errors import McpToolError


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class Confirmations:
    def __init__(self, secret: str, ttl: int, clock=time.time):
        self._key = secret.encode()
        self._ttl = ttl
        self._clock = clock
        self._used: dict[str, float] = {}

    def issue(self, *, principal: str, tool: str, resource: str, operation: str, target: str, payload_hash: str, version: str = "") -> dict:
        body = {"p": principal, "t": tool, "r": resource, "o": operation, "g": target, "h": payload_hash, "v": version, "e": int(self._clock()) + self._ttl, "n": secrets.token_hex(8)}  # nonce: dos previews del mismo dato en el mismo segundo dan fichas distintas
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        sig = hmac.new(self._key, raw, hashlib.sha256).digest()
        return {"confirmation_token": f"{_b64(raw)}.{_b64(sig)}", "expires_in_seconds": self._ttl}

    def verify(self, token: str | None, *, principal: str, tool: str, resource: str, operation: str, target: str, payload_hash: str, version: str = "") -> None:
        if not token:
            raise McpToolError(errors.CONFIRMATION_REQUIRED, "Esta operacion requiere confirmacion: ejecuta primero su preview y reutiliza el confirmation_token.")
        try:
            raw_b64, sig_b64 = token.split(".", 1)
            raw, sig = _unb64(raw_b64), _unb64(sig_b64)
            body = json.loads(raw)
        except Exception:  # noqa: BLE001 - cualquier token mal formado es simplemente invalido
            raise McpToolError(errors.CONFIRMATION_INVALID, "confirmation_token invalido.")
        expected = hmac.new(self._key, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            raise McpToolError(errors.CONFIRMATION_INVALID, "confirmation_token invalido.")
        if body.get("e", 0) < self._clock():
            raise McpToolError(errors.CONFIRMATION_INVALID, "confirmation_token caducado: repite el preview.")
        wanted = {"p": principal, "t": tool, "r": resource, "o": operation, "g": target, "h": payload_hash, "v": version}
        if any(body.get(k) != v for k, v in wanted.items()):
            raise McpToolError(errors.CONFIRMATION_INVALID, "La ficha no corresponde a esta operacion, objetivo, datos o version: repite el preview.")
        if token in self._used:
            raise McpToolError(errors.CONFIRMATION_INVALID, "confirmation_token ya utilizado.")
        now = self._clock()
        self._used = {t: exp for t, exp in self._used.items() if exp > now}  # limpieza de caducados
        self._used[token] = body["e"]


class IdempotencyStore:
    """Resultados por (principal, tool, idempotency_key) durante 24 h. Misma clave + mismo payload => devuelve el resultado guardado (no repite la escritura);
    misma clave + payload distinto => IDEMPOTENCY_KEY_REUSED. En memoria: sobrevive a reintentos y reconexiones, no a un reinicio del proceso."""

    def __init__(self, ttl: int = 86400, clock=time.time, max_entries: int = 5000):
        self._ttl, self._clock, self._max = ttl, clock, max_entries
        self._data: dict[str, tuple] = {}

    def _purge(self) -> None:
        now = self._clock()
        self._data = {k: v for k, v in self._data.items() if v[0] > now}
        while len(self._data) > self._max:
            self._data.pop(next(iter(self._data)))

    def lookup(self, principal: str, tool: str, key: str, payload_hash: str):
        self._purge()
        entry = self._data.get(f"{principal}|{tool}|{key}")
        if entry is None:
            return None
        if entry[1] != payload_hash:
            raise McpToolError(errors.IDEMPOTENCY_KEY_REUSED, "Esa idempotency_key ya se uso con datos distintos: usa una clave nueva.")
        return entry[2]

    def store(self, principal: str, tool: str, key: str, payload_hash: str, result: dict) -> None:
        self._data[f"{principal}|{tool}|{key}"] = (self._clock() + self._ttl, payload_hash, result)
