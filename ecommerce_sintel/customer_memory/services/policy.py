"""
HARDENING F7/C1+C2+C3 (2026-09-24) -- politica de memoria del cliente (plan sec. 11).

Un unico modulo con: la barrera de escritura (`evaluate_content`), el TTL por categoria y la auditoria estructurada.

Barrera (orden): 1) sanear (F5) -> 2) rechazar AUTORIDAD/INSTRUCCIONES (un recuerdo NUNCA otorga permisos ni cambia el comportamiento:
"soy administrador", "puedes saltarte las confirmaciones", "a partir de ahora ...") -> 3) rechazar DATOS SENSIBLES (credenciales, OTP, tokens,
cuentas, correo, telefono, documento) -> aceptar. Se RECHAZA, no se redacta: un recuerdo con el dato tachado pierde sentido y guardar la fila
seria conservar un fragmento sensible (decision del usuario, 2026-09-24).

Los rechazos devuelven un `reason_code` estable y NUNCA repiten el contenido. Los eventos de auditoria (`memory_event=...`) no llevan contenido
ni email: el cliente se identifica con un hash corto de su uuid.

El clasificador de instrucciones es el de F5 (`ai_engine_adk/input_guard.py`, solo biblioteca estandar), importado como en ai_knowledge/ingestion.py.
"""
import hashlib
import logging
import re
import unicodedata
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ai_engine_adk import input_guard

logger = logging.getLogger('customer_memory.audit')

REASON_EMPTY = 'empty'
REASON_CATEGORY = 'invalid_category'
REASON_AUTHORITY = 'authority_or_instruction'
REASON_SENSITIVE = 'sensitive_data'

DEFAULT_TTL_DAYS = {
    'contact_preference': 365, 'communication_style': 365, 'product_interest': 180, 'general_preference': 180,
}

# Categorias de F5 que hacen NO aceptable un recuerdo (autoridad/instruccion/extraccion de secretos).
_AUTHORITY_DETECTOR_CATEGORIES = {
    'override_instructions', 'role_impersonation', 'fake_system_message', 'confirmation_bypass',
    'tool_escalation', 'system_prompt_extraction', 'secret_request', 'delimiter_forgery',
}


def _fold(text: str) -> str:
    nfd = unicodedata.normalize('NFD', (text or '').lower())
    return ''.join(ch for ch in nfd if unicodedata.category(ch) != 'Mn')


_AUTHORITY_PATTERNS = [re.compile(p) for p in (
    r'a\s+partir\s+de\s+ahora',
    r'de\s+ahora\s+en\s+adelante',
    r'siempre\s+(debes|tienes\s+que|has\s+de)',
    r'(no|nunca)\s+(me\s+)?(pidas|pidan|solicites|preguntes)',
    r'(puedes|pueden|podras)\s+(saltar(te|se|les)?|omitir|ignorar|no\s+pedir)',
    r'tengo\s+(acceso|permiso|autorizacion|privilegios?)\s+(especial|total|de\s+admin\w*|completo)?',
    r'estoy\s+autorizad[oa]',
    r'(soy|somos)\s+(el\s+|la\s+)?(admin\b|administrador\s+(del\s+)?(sistema|panel|sitio|plataforma|sintel)|superusuario|root\b|dueno\s+de\s+sintel|gerente\s+de\s+sintel|propietario\s+de\s+sintel)',
    r'(this|the)\s+user\s+(is|has)\s+(authorized|admin)',
    r'el\s+(usuario|cliente)\s+(esta\s+)?autoriz\w+',
    r'sin\s+(pedir\s+)?confirmacion',
    r'recuerda\s+que\s+(eres|debes|puedes|tienes)',
)]

_SENSITIVE_PATTERNS = [re.compile(p, re.I) for p in (
    r'\b(otp|codigo\s+(de\s+)?(verificacion|seguridad|confirmacion|acceso)|token|jwt|bearer|api\s*key|apikey|(client|api|app)\s*secret|secret\s*key|clave\s+(de\s+)?(acceso|api|secreta|bancaria)|contrasena|password|passwd|\bpin\b|cvv|cvc|numero\s+de\s+tarjeta)\b',
    r'[\w.+-]+@[\w-]+\.[\w.-]+',                                   # correo
    r'(?:\d[\s\-\.]?){7,}',                                         # telefono / cuenta / tarjeta / documento (7+ digitos, con o sin separadores)
    r'\b(cedula|cc|nit|pasaporte|documento|iban|swift|cuenta\s+(bancaria|de\s+ahorros|corriente))\b[^\d\n]{0,20}\d{3,}',
)]


def _customer_hash(user) -> str:
    return hashlib.sha256(str(getattr(user, 'uuid', getattr(user, 'pk', ''))).encode()).hexdigest()[:10]


def audit(event: str, *, user=None, category: str = '', reason: str = '', channel: str = '', extra: str = '') -> None:
    """Evento de auditoria estructurado, sin contenido ni email."""
    logger.info('memory_event=%s customer=%s category=%s reason=%s channel=%s%s', event,
                _customer_hash(user) if user is not None else '-', category or '-', reason or '-', channel or '-',
                f' {extra}' if extra else '')


def is_strict() -> bool:
    return getattr(settings, 'AI_MEMORY_GATE_STRICT', True)


def evaluate_content(content: str) -> str | None:
    """None si el contenido es aceptable; en otro caso el `reason_code` del rechazo (nunca el contenido)."""
    text = input_guard.sanitize_text(content or '')
    if not text.strip():
        return REASON_EMPTY
    folded = _fold(text)
    if _AUTHORITY_DETECTOR_CATEGORIES & set(input_guard.detect_injection(text)):
        return REASON_AUTHORITY
    if any(p.search(folded) for p in _AUTHORITY_PATTERNS):
        return REASON_AUTHORITY
    if any(p.search(folded) for p in _SENSITIVE_PATTERNS):
        return REASON_SENSITIVE
    return None


def ttl_days(category: str) -> int:
    configured = getattr(settings, 'CUSTOMER_MEMORY_TTL_DAYS', None) or {}
    return int(configured.get(category, DEFAULT_TTL_DAYS.get(category, 180)))


def expiry_for(category: str, now=None):
    return (now or timezone.now()) + timedelta(days=ttl_days(category))
