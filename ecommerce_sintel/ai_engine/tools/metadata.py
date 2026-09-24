"""
ToolMetadata (Componente 13 del plan) y ToolContext.

Cada Tool declara su metadata junto a la funcion: la Policy Layer (Fase 4)
consulta risk/requires_confirmation antes de ejecutar, y Observabilidad
(Fase 6) etiqueta metricas por Tool. Se declara desde la Fase 2 aunque las
Tools sean de solo lectura, para que ambos consumidores tengan datos desde
el dia uno.
"""
from dataclasses import dataclass, field

from pydantic import BaseModel


class ToolMetadata(BaseModel):
    name: str
    description: str
    owner: str                          # app Django duena, para trazabilidad
    capabilities: list[str]             # capability_ids que implementa
    permissions: list[str] = []         # permission classes Django equivalentes
    risk: str = "low"                   # low | medium | high
    audit_level: str = "summary"        # full | summary | none
    rate_limit: str = ""                # ej. "10/hour/user" -- aplicado por la Policy Layer
    requires_confirmation: bool = False
    side_effects: bool = False          # True = escritura: pasa por Policy Layer SIEMPRE
    timeout_ms: int = 8000
    version: str = "v1"                 # Componente 12: versionado desde el dia uno
    args_schema: dict = {}              # JSON-schema de argumentos (para bind_tools, Fase 3)
    # HARDENING F4 (2026-09-24): completados por tools/classification.py::apply_policy en el registro.
    level: int = -1                     # 0 lectura | 1 escritura local | 2 consecuencia | 3 externo | 4 destructivo/financiero
    idempotent: bool = False            # True = el adapter del ADK deduplica repeticiones identicas
    resource_scope: str = ""            # ambito del recurso (informativo para auditoria)


@dataclass
class ToolContext:
    """
    Contexto de invocacion de una Tool.

    `user` es el dict resuelto por Django (Fase 1, /internal/ai-context/).
    `token` es el JWT del usuario final, que la Tool reenvia a Django --
    nunca se persiste ni se loggea.
    """
    user: dict
    token: str = field(repr=False, default="")
