"""
HARDENING F6/C2 (2026-09-24) -- pipeline de ingesta de conocimiento (plan sec. 10.3).

    ingest -> validar fuente -> sanear -> clasificar (inyeccion) -> hash -> versionar -> indexar -> evaluar -> publicar

Este modulo contiene las etapas PURAS (sin BD); `AIKnowledgeDocumentCommands.upsert_document` las orquesta y
`publish_document`/`approve_document` implementan las acciones humanas explicitas. Reglas de fondo:

- El contenido ingerido es DATO no confiable: se sanea (Unicode invisible, `<script>`/`<style>`, atributos `on*`, `javascript:`).
- Si el clasificador encuentra banderas de inyeccion (`override_instructions`, `fake_system_message`, `delimiter_forgery`,
  `system_prompt_extraction`, `tool_escalation`, `confirmation_bypass`) el documento queda `needs_review`, NO publicable y forzado a
  `visibility=internal` hasta que una persona lo apruebe explicitamente.
- Fuentes permitidas: 'manual'/vacio, rutas relativas del repositorio (sin `..`, sin esquema) y URLs https de dominios de
  `settings.AI_KNOWLEDGE_ALLOWED_SOURCE_HOSTS`. Cualquier otra se rechaza.

El clasificador es el de F5 (`ai_engine_adk/input_guard.py`, solo biblioteca estandar); se importa directamente porque vive en el mismo
repositorio y la imagen de Django copia todo `ecommerce_sintel/`.
"""
import hashlib
import re
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError

from ai_engine_adk import input_guard

# Categorias de F5 que hacen NO publicable un documento (las demas, p. ej. `role_impersonation`/`secret_request`, son
# ambiguas en contenido legitimo -- "soy el administrador del sistema" puede aparecer en un manual -- y solo se registran).
BLOCKING_CATEGORIES = {
    'override_instructions', 'fake_system_message', 'delimiter_forgery',
    'system_prompt_extraction', 'tool_escalation', 'confirmation_bypass',
}

_SCRIPT_RE = re.compile(r'<\s*(script|style|iframe|object|embed)\b.*?<\s*/\s*\1\s*>', re.I | re.S)
_STRAY_TAG_RE = re.compile(r'<\s*/?\s*(script|style|iframe|object|embed)\b[^>]*>', re.I)
_ON_ATTR_RE = re.compile(r'\son\w+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)', re.I)
_JS_URL_RE = re.compile(r'javascript\s*:', re.I)


def allowed_source_hosts() -> list[str]:
    return [h.lower() for h in getattr(settings, 'AI_KNOWLEDGE_ALLOWED_SOURCE_HOSTS', ['sintel.net.co', 'panel.sintel.net.co'])]


def validate_source(source: str) -> str:
    source = (source or '').strip()
    if source in ('', 'manual'):
        return source
    if '\x00' in source:
        raise ValidationError('Fuente invalida.')
    parsed = urlparse(source)
    if parsed.scheme:
        if parsed.scheme != 'https':
            raise ValidationError('Fuente rechazada: solo se permiten URLs https.')
        host = (parsed.hostname or '').lower()
        if host not in allowed_source_hosts():
            raise ValidationError('Fuente rechazada: dominio no permitido.')
        return source
    # ruta relativa del repositorio
    normalized = source.replace('\\', '/')
    if normalized.startswith('/') or re.match(r'^[A-Za-z]:', normalized) or '..' in normalized.split('/'):
        raise ValidationError('Fuente rechazada: ruta absoluta o con `..`.')
    return source


def sanitize_content(content: str) -> str:
    text = input_guard.sanitize_text(content or '')
    text = _SCRIPT_RE.sub('', text)
    text = _STRAY_TAG_RE.sub('', text)
    text = _ON_ATTR_RE.sub('', text)
    return _JS_URL_RE.sub('', text)


def content_hash(content: str) -> str:
    return hashlib.sha256((content or '').encode('utf-8')).hexdigest()


def classify(content: str) -> dict:
    """{'flags': [categorias halladas], 'blocking': [las que impiden publicar]} -- nunca devuelve el texto."""
    flags = input_guard.detect_injection(content)
    return {'flags': flags, 'blocking': sorted(set(flags) & BLOCKING_CATEGORIES)}
