"""
ai_editor.resolver -- POST-GRAPH 3 "Change Resolver" (rediseno "AI Editor
Runtime", 2026-08-11). IMPLEMENTADO (deja de ser scaffold en esta fase).

Convierte un `ChangeIntent` (POST-GRAPH 2) en un `ChangeContext` completo,
resolviendo cada entidad mencionada contra el grafo real (nunca inventa
archivos/simbolos/dependencias que el grafo no confirme) y componiendo
`resolve_change()`/`build_context_packet()` (ya reales desde Fase 11/12)
para el resultado final.
"""
from ai_editor.resolver.resolver import resolve_change_context
from ai_editor.resolver.schema import (
    STATUS_PARTIALLY_RESOLVED,
    STATUS_RESOLVED,
    STATUS_UNRESOLVED,
    ChangeContext,
)

__all__ = [
    "resolve_change_context",
    "ChangeContext",
    "STATUS_RESOLVED",
    "STATUS_PARTIALLY_RESOLVED",
    "STATUS_UNRESOLVED",
]
