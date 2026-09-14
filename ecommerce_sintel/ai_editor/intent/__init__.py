"""
ai_editor.intent -- POST-GRAPH 2 "Change Intent" (rediseno "AI Editor
Runtime", 2026-08-11). IMPLEMENTADO (deja de ser scaffold en esta fase).

Convierte una solicitud humana en lenguaje natural en un `ChangeIntent`
estructurado (domain/intent/entities/scope/confidence/ambiguities), usando
`ai_editor.llm` (independiente, ver ese paquete) para la interpretacion y
`ai_editor.graph_client` (POST-GRAPH 1) para CONFIRMAR que el dominio
propuesto corresponde a una app real -- nunca confia ciegamente en lo que
el LLM interpreto. Si la solicitud es ambigua o el dominio no se confirma,
el `ChangeIntent` resultante queda con `status="NEEDS_CLARIFICATION"` en
vez de avanzar con una suposicion.
"""
from ai_editor.intent.parser import interpret_request
from ai_editor.intent.schema import (
    STATUS_NEEDS_CLARIFICATION,
    STATUS_RESOLVED,
    ChangeIntent,
)

__all__ = [
    "interpret_request",
    "ChangeIntent",
    "STATUS_RESOLVED",
    "STATUS_NEEDS_CLARIFICATION",
]
