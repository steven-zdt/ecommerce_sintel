"""
HARDENING F8 (2026-09-24) -- seguridad de la SALIDA publica del asistente (plan sec. 12).

Se aplica a `final_text` justo despues de `public_response.extract_public_response` y antes de devolverlo a Django (widget web / WhatsApp).
Propuesta y decisiones: ai_engine_adk/.AGENT/HARDENING_F8_PROPOSAL_2026-09-24.md.

Igual que F5: NINGUNA de estas capas es la autoridad de seguridad. Reducen la superficie y dejan telemetria; los controles reales siguen siendo
estructurales (scope de Tools, permisos, confirmacion). Los eventos NUNCA incluyen el texto ni el valor redactado, solo categorias.

Pipeline (`guard_public_response`):
  1. razonamiento: quita <think>...</think>, un <think> SIN cerrar (respuesta truncada por AI_*_MAX_OUTPUT_TOKENS) y etiquetas sueltas
  2. saneo Unicode (F5)
  3. secretos -> "[dato oculto]" (JWT, Bearer, claves tipicas, `clave=valor`, y el valor EXACTO de secretos del entorno del proceso)
  4. fuga de infraestructura / prompt de sistema -> se REEMPLAZA TODA la respuesta por un mensaje seguro (decision del usuario)
  5. enlaces (solo superficie cliente): dominios permitidos; los demas -> "[enlace removido]" con AI_OUTPUT_LINKS_ENFORCE, o solo se registra (monitor)
  6. largo maximo (AI_OUTPUT_MAX_CHARS) con corte en limite de frase
"""
import logging
import os
import re
from urllib.parse import urlparse

import input_guard

logger = logging.getLogger("output_guard")

SAFE_MESSAGE = ("Por seguridad no puedo compartir esa informacion. "
                "Un agente humano puede ayudarte con tu consulta.")
REDACTED = "[dato oculto]"
LINK_REMOVED = "[enlace removido]"

#  1. razonamiento 
_THINK_CLOSED_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)
_THINK_OPEN_RE = re.compile(r"<think>.*\Z", re.IGNORECASE | re.DOTALL)   # sin cerrar: hasta el final
_THINK_STRAY_RE = re.compile(r"</?think>", re.IGNORECASE)

#  3. secretos 
_SECRET_PATTERNS = [
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("bearer", re.compile(r"\b[Bb]earer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("api_key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b")),
]
_KEYVALUE_RE = re.compile(
    r"(?i)\b(api[_ -]?key|secret|token|password|passwd|contrasena|clave)\b(\s*[:=]\s*)([^\s,;\"']{8,})")
# Variables del entorno del proceso cuyo VALOR exacto jamas debe salir (solo valores >= 16 caracteres).
_SECRET_ENV_NAMES = (
    "AI_SERVICE_TOKEN", "AI_SERVICE_TOKEN_PREVIOUS", "JWT_SECRET_KEY", "SECRET_KEY", "DB_PASSWORD", "POSTGRES_PASSWORD",
    "REDIS_PASSWORD", "EMAIL_HOST_PASSWORD", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "WOMPI_PRIVATE_KEY",
    "WOMPI_INTEGRITY_SECRET", "WOMPI_EVENTS_SECRET", "WA_GATEWAY_INTERNAL_TOKEN", "META_ACCESS_TOKEN",
)

#  4. infraestructura / prompt (lista ESTRECHA: nombres reales de este stack, no palabras genericas) 
_INFRA_PATTERNS = [
    ("internal_host", re.compile(r"\b(?:sintel[_-]ollama|sintel[_-]ai(?:[_-]adk)?|sintel[_-]prod[_-]\w+|ecommerce[_-]sintel[_-]\w+|sintel-ai-private|sintel-network|host\.docker\.internal)\b", re.I)),
    ("container_path", re.compile(r"(?<![\w.])/(?:app|code)/[\w./-]+")),
    ("env_file", re.compile(r"(?<![\w])\.env(?:\.production)?\b")),
    ("traceback", re.compile(r"Traceback \(most recent call last\)")),
    ("internal_url", re.compile(r"\b(?:localhost|127\.0\.0\.1):\d{3,5}|\b(?:redis|postgres(?:ql)?|amqp)://", re.I)),
]
_PROMPT_MARKERS = (
    "Politica de precedencia (no negociable)",
    "AVISO DE SEGURIDAD: el bloque delimitado",
    "DATOS_NO_CONFIABLES",
    "Usa siempre una tool para responder con datos reales",
)

#  5. enlaces 
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.IGNORECASE)


def _allowed_hosts() -> list[str]:
    import config as ai_config

    return [h.lower() for h in ai_config.AI_OUTPUT_ALLOWED_LINK_HOSTS]


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in _allowed_hosts())


def _configured_secret_values() -> list[str]:
    return [v for name in _SECRET_ENV_NAMES if len((v := os.environ.get(name, ""))) >= 16]


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    boundary = max(cut.rfind(". "), cut.rfind("\n"), cut.rfind("? "), cut.rfind("! "))
    if boundary >= int(max_chars * 0.75):
        cut = cut[: boundary + 1]
    return cut.rstrip() + "\u2026"


def guard_public_response(text: str, *, surface: str = "customer") -> tuple[str, list[str]]:
    """Devuelve (texto_seguro, flags). `flags` son categorias (sin contenido). surface: "customer" | "admin"."""
    import config as ai_config

    flags: list[str] = []
    if not text:
        return text or "", flags
    original = text

    # 1. razonamiento
    text = _THINK_CLOSED_RE.sub("", text)
    if _THINK_OPEN_RE.search(text):
        text = _THINK_OPEN_RE.sub("", text)
        flags.append("reasoning_unclosed")
    text = _THINK_STRAY_RE.sub("", text)
    if text != original and "reasoning_unclosed" not in flags:
        flags.append("reasoning_stripped")

    # 2. saneo Unicode
    text = input_guard.sanitize_text(text).strip()

    # 3. secretos
    for value in _configured_secret_values():
        if value in text:
            text = text.replace(value, REDACTED)
            flags.append("secret_value")
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            text = pattern.sub(REDACTED, text)
            flags.append(f"secret_{name}")
    if _KEYVALUE_RE.search(text):
        text = _KEYVALUE_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", text)
        flags.append("secret_keyvalue")

    # 4. infraestructura / prompt de sistema -> se reemplaza TODA la respuesta
    leaks = [name for name, p in _INFRA_PATTERNS if p.search(text)]
    if any(marker in text for marker in _PROMPT_MARKERS):
        leaks.append("system_prompt")
    if leaks:
        flags.extend(f"blocked_{c}" for c in leaks)
        logger.warning("security_event=output_blocked surface=%s categories=%s", surface, leaks)
        return SAFE_MESSAGE, flags

    # 5. enlaces (solo cliente)
    if surface != "admin":
        bad = [u for u in _URL_RE.findall(text) if not _host_allowed(u)]
        if bad:
            flags.append("link_not_allowed")
            logger.warning("security_event=output_link_flagged enforced=%s count=%s", ai_config.AI_OUTPUT_LINKS_ENFORCE, len(bad))
            if ai_config.AI_OUTPUT_LINKS_ENFORCE:
                text = _URL_RE.sub(lambda m: m.group(0) if _host_allowed(m.group(0)) else LINK_REMOVED, text)

    # 6. largo
    truncated = _truncate(text, ai_config.AI_OUTPUT_MAX_CHARS)
    if truncated != text:
        flags.append("truncated")
        text = truncated

    redactions = [f for f in flags if f.startswith("secret_")]
    if redactions:
        logger.warning("security_event=output_redacted surface=%s categories=%s", surface, redactions)
    if "truncated" in flags:
        logger.info("ai_operation_event=output_truncated surface=%s max_chars=%s", surface, ai_config.AI_OUTPUT_MAX_CHARS)
    return text, flags
