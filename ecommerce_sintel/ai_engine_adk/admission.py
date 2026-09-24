"""
HARDENING F13/C2 (2026-09-24) -- control de admision de turnos del ADK (concurrencia acotada + cola acotada).

Propuesta: ai_engine_adk/.AGENT/HARDENING_F13_PROPOSAL_2026-09-24.md. Problema: el ADK corre UN worker asyncio que acepta turnos sin limite;
todos terminan en la cola de Ollama (una sola GPU de 8 GB, ~1 turno cada 60-110 s). Bajo carga los turnos esperan en la cola del modelo,
sus llamadas vencen (90 s), el circuit breaker las cuenta como "el proveedor fallo" y salta a LM Studio (la MISMA GPU): cascada. Aqui los
turnos que no caben esperan un tiempo acotado en una cola acotada y, si no, reciben una respuesta degradada inmediata (handoff a un humano).

AI_MAX_CONCURRENT_TURNS=0 (default) = DESACTIVADO (comportamiento anterior, sin limite). Un solo proceso: con varios workers de uvicorn el
limite se multiplica (el despliegue actual usa uno).
"""
import asyncio
import time


class Rejected(Exception):
    """El turno no fue admitido. `reason`: queue_full | queue_timeout."""

    def __init__(self, reason: str, waited_ms: int = 0):
        super().__init__(reason)
        self.reason = reason
        self.waited_ms = waited_ms


class Admission:
    def __init__(self, max_concurrent: int, max_queue: int, max_wait_seconds: float):
        self.max_concurrent = max(0, int(max_concurrent))
        self.max_queue = max(0, int(max_queue))
        self.max_wait_seconds = max(0.0, float(max_wait_seconds))
        self._sem: asyncio.Semaphore | None = None  # se crea en el event loop que la usa
        self.waiting = 0
        self.active = 0

    @property
    def enabled(self) -> bool:
        return self.max_concurrent > 0

    async def acquire(self) -> int:
        """Devuelve los ms esperados en cola. Lanza `Rejected` si la cola esta llena o la espera vence."""
        if not self.enabled:
            return 0
        if self._sem is None:
            self._sem = asyncio.Semaphore(self.max_concurrent)
        if self._sem.locked() and self.waiting >= self.max_queue:
            raise Rejected("queue_full")
        started = time.monotonic()
        self.waiting += 1
        try:
            await asyncio.wait_for(self._sem.acquire(), timeout=self.max_wait_seconds)
        except asyncio.TimeoutError:
            raise Rejected("queue_timeout", int((time.monotonic() - started) * 1000)) from None
        finally:
            self.waiting -= 1
        self.active += 1
        return int((time.monotonic() - started) * 1000)

    def release(self) -> None:
        if self.enabled and self._sem is not None and self.active > 0:
            self.active -= 1
            self._sem.release()

    def snapshot(self) -> dict:
        return {"enabled": self.enabled, "max_concurrent": self.max_concurrent, "max_queue": self.max_queue,
                "active": self.active, "waiting": self.waiting}
