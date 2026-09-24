"""
HARDENING F17/C1 (2026-09-24) -- canary del motor de IA: elige a que ADK va cada usuario ("stable" o "canary").

Propuesta: ai_engine_adk/.AGENT/HARDENING_F17_PROPOSAL_2026-09-24.md. El plan (sec. 21) prohibe "build -> production immediately": una nueva
version del ADK/prompt/agentes/tools/modelo se prueba primero con usuarios internos y luego con una fraccion pequena del trafico.

Reglas (todas por variable de entorno; DEFAULT = TODO a stable, comportamiento anterior):
  AI_CANARY_ENGINE_URL   URL del ADK canary (vacia = canary apagado; es el KILL SWITCH: vaciarla devuelve todo a stable).
  AI_CANARY_USER_EMAILS  correos (separados por coma) de usuarios INTERNOS que SIEMPRE van a canary.
  AI_CANARY_PERCENT      0-100: porcentaje de los DEMAS usuarios, asignado de forma DETERMINISTA por usuario (hash del id), de modo que un
                         mismo usuario no salta entre versiones a mitad de una conversacion mientras el porcentaje no cambie.
Sin estado, sin BD, sin red: solo lee settings.
"""
import hashlib

from django.conf import settings

STABLE = 'stable'
CANARY = 'canary'


def _emails() -> set[str]:
    raw = getattr(settings, 'AI_CANARY_USER_EMAILS', '') or ''
    if isinstance(raw, (list, tuple, set)):
        return {str(e).strip().lower() for e in raw if str(e).strip()}
    return {e.strip().lower() for e in str(raw).split(',') if e.strip()}


def bucket(user) -> int:
    """0-99, estable por usuario."""
    key = f"ai-canary:{getattr(user, 'pk', None) or getattr(user, 'id', None) or getattr(user, 'email', '')}"
    return int(hashlib.sha256(key.encode()).hexdigest(), 16) % 100


def track_for(user) -> str:
    if not getattr(settings, 'AI_CANARY_ENGINE_URL', ''):
        return STABLE
    if (getattr(user, 'email', '') or '').strip().lower() in _emails():
        return CANARY
    percent = int(getattr(settings, 'AI_CANARY_PERCENT', 0) or 0)
    if percent > 0 and bucket(user) < min(percent, 100):
        return CANARY
    return STABLE


def resolve_engine(user) -> tuple[str, str]:
    """(url_base_del_adk, track)."""
    track = track_for(user)
    return (settings.AI_CANARY_ENGINE_URL if track == CANARY else settings.AI_ENGINE_URL), track


def stable_engine() -> tuple[str, str]:
    return settings.AI_ENGINE_URL, STABLE
