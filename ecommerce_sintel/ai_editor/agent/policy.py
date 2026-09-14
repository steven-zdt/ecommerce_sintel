"""
`AgentPolicy` -- FASE 52 "Agent Policy" (plan "AI Change Proposal
Engine", 2026-08-11).

Limites que `loop.run_autonomous_change_loop()` (FASE 51+53) respeta.
Deliberadamente NO existe un campo `allow_auto_promote`/`require_human_
approval` -- no hace falta un flag para apagar una capacidad que este
paquete nunca tiene: `ai_editor.agent` no importa `ai_editor.generation.
promotion` ni `ai_editor.repository.promote` en ningun archivo (ver
`test_never_imports_promotion_or_repository_promote` en la suite de
tests) -- la REGLA FINAL DE SEGURIDAD del prompt maestro ("Nunca permitir
LLM -> WRITE -> PRODUCTION directamente") queda garantizada de forma
ESTRUCTURAL, no por convencion de un valor de config que alguien podria
cambiar. El loop autonomo siempre termina, como maximo, en
`APPROVAL_REQUIRED` (ver `generation.pipeline_states`) -- promover sigue
siendo, sin excepcion, una llamada aparte a `generation.promotion.
review_and_promote()` con `decision`/`confirm` provistos por un humano
real.
"""
from dataclasses import dataclass

from ai_editor.generation.retry import DEFAULT_MAX_RETRIES


@dataclass(frozen=True)
class AgentPolicy:
    """`max_retries`: reenviado tal cual a `generate_with_retry()` (FASE
    30) -- mismo default (`DEFAULT_MAX_RETRIES=3`). `provider`: fuerza un
    LLM especifico (ver `ai_editor.llm`) para AMBAS llamadas al LLM del
    loop (`interpret_request()` y `generate_with_retry()`) -- `None`
    usa el default configurado por env var (`AI_EDITOR_LLM_PROVIDER`,
    Ollama local si no se configura nada)."""

    max_retries: int = DEFAULT_MAX_RETRIES
    provider: str | None = None

    def __post_init__(self) -> None:
        if self.max_retries < 1:
            raise ValueError(f"max_retries debe ser >= 1 (recibido: {self.max_retries})")


__all__ = ["AgentPolicy"]
