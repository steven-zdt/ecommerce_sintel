"""
AgentRegistry del AI Core (Fase 6) — Agent Profiles (Componente 11).

Cada agente se declara COMPLETO en agents/profiles/*.yaml (nombre,
descripcion, objetivo, personalidad, herramientas, permisos, capacidades,
memoria, reglas de escalamiento, tono) — nunca "solo por nombre". Al cargar
se valida contra el CapabilityRegistry y el ToolRegistry: una capability o
Tool inexistente rompe el arranque en vez de fallar silenciosamente en
runtime.

Los permisos declarados son las MISMAS permission classes de Django (el
enforcement real vive en los endpoints internos); aqui delimitan que
capabilities puede ofrecer cada agente al LLM — no un sistema paralelo.
"""
import logging
import re
from pathlib import Path

import yaml
from pydantic import BaseModel

logger = logging.getLogger("agents")

_PROFILES_DIR = Path(__file__).parent / "profiles"


class EscalationRule(BaseModel):
    cuando: str          # regex sobre el mensaje del cliente
    derivar_a: str       # nombre del agente destino


class AgentProfile(BaseModel):
    name: str
    description: str
    objetivo: str
    personalidad: str
    herramientas: list[str]
    permisos: list[str]
    capacidades: list[str]
    intents: list[str]
    memoria: str
    reglas_escalamiento: list[EscalationRule] = []
    tono: str
    version: str = "v1"


_AGENTS: dict[str, AgentProfile] = {}
_INTENT_TO_AGENT: dict[str, str] = {}
_DEFAULT_AGENT = "SupportAgent"


def _load_profiles() -> None:
    from capabilities import CapabilityRegistry
    import tools as tool_registry

    for path in sorted(_PROFILES_DIR.glob("*.yaml")):
        profile = AgentProfile(**yaml.safe_load(path.read_text(encoding="utf-8")))
        for cap_id in profile.capacidades:
            if CapabilityRegistry.get(cap_id) is None:
                raise ValueError(f"{path.name}: capability inexistente '{cap_id}'")
        for tool_name in profile.herramientas:
            if tool_registry.get_tool(tool_name) is None:
                raise ValueError(f"{path.name}: tool inexistente '{tool_name}'")
        for rule in profile.reglas_escalamiento:
            re.compile(rule.cuando)  # regex invalida -> error al cargar
        _AGENTS[profile.name] = profile
        for intent in profile.intents:
            # C1 (AUDITORIA/16, 2026-08-01): antes esto sobreescribia en silencio si dos
            # perfiles declaraban el mismo intent -- el ganador dependia del orden alfabetico
            # del nombre de archivo, y el perdedor quedaba con un intent declarado pero jamas
            # alcanzable via el router, sin ningun aviso. Hallazgo real: marketing_agent.yaml y
            # sales_agent.yaml declaraban ambos "promos" (ya corregido, quitado del primero).
            if intent in _INTENT_TO_AGENT and _INTENT_TO_AGENT[intent] != profile.name:
                raise ValueError(
                    f"{path.name}: intent '{intent}' ya esta asignado a "
                    f"'{_INTENT_TO_AGENT[intent]}' -- un intent solo puede tener un agente."
                )
            _INTENT_TO_AGENT[intent] = profile.name
    logger.info("[agents] %d perfiles cargados: %s", len(_AGENTS), sorted(_AGENTS))


class AgentRegistry:

    @staticmethod
    def get(name: str) -> AgentProfile | None:
        return _AGENTS.get(name)

    @staticmethod
    def list_all() -> list[AgentProfile]:
        return list(_AGENTS.values())

    @staticmethod
    def route(intent: str) -> AgentProfile:
        """Router intencion -> agente (extiende detect_intent, Fase 3)."""
        name = _INTENT_TO_AGENT.get(intent, _DEFAULT_AGENT)
        return _AGENTS[name]

    @staticmethod
    def apply_escalation(agent: AgentProfile, message: str) -> AgentProfile:
        """
        Handoff dentro del mismo turno: si una regla del agente matchea el
        mensaje, deriva al agente declarado (tipicamente SupportAgent).
        """
        for rule in agent.reglas_escalamiento:
            if re.search(rule.cuando, message or "", re.IGNORECASE):
                target = _AGENTS.get(rule.derivar_a)
                if target is not None and target.name != agent.name:
                    logger.info("[agents] handoff %s -> %s (regla: %s)",
                                agent.name, target.name, rule.cuando[:40])
                    return target
        return agent


_load_profiles()

__all__ = ["AgentProfile", "AgentRegistry", "EscalationRule"]
