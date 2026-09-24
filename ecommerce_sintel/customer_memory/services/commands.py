"""customer_memory/services/commands.py -- FASE 9, Mision RAG-POST2; endurecido en HARDENING F7 (2026-09-24).

Defensa en profundidad: el extractor de ai_engine_adk (FASE 10) es la PRIMERA linea (el LLM no deberia proponer guardar un
rol/credencial), pero Django NUNCA confia ciegamente en lo que llega por HTTP interno -- esta Command es la SEGUNDA linea, real,
server-side, que se aplica sin importar que tan bien o mal se haya comportado el extractor.

F7: la barrera (autoridad/instrucciones, datos sensibles), el TTL, la atribucion (canal/origen) y la auditoria viven en `policy.py`."""
import re
from datetime import timedelta

from django.utils import timezone

from ..models import CustomerMemoryRecord
from . import policy

_VALID_CATEGORIES = {choice[0] for choice in CustomerMemoryRecord.CATEGORY_CHOICES}
_VALID_CHANNELS = {choice[0] for choice in CustomerMemoryRecord.CHANNEL_CHOICES}

# Patrones que NUNCA deben persistirse como memoria, sin importar la categoria propuesta -- numero tipo tarjeta (13-19 digitos, con o sin
# separadores) y menciones directas de credenciales. Se conservan (los cubre tambien policy._SENSITIVE_PATTERNS) como red de seguridad
# explicita del contrato original (Regla: nunca almacenar datos sensibles como memoria, ver FASE 8).
_CARD_LIKE_PATTERN = re.compile(r'(?:\d[ -]?){13,19}')
_CREDENTIAL_KEYWORDS = re.compile(
    r'\b(contrase[nñ]a|password|clave secreta|pin\b|cvv|numero de tarjeta)\b', re.I,
)
_MAX_CONTENT_LENGTH = 280


class MemoryRejected(Exception):
    """El contenido propuesto no cumple la politica de memoria -- nunca se persiste, ni siquiera desactivado.
    `code` es un reason_code estable (policy.REASON_*); el mensaje NUNCA repite el contenido."""

    def __init__(self, message: str, code: str = ''):
        super().__init__(message)
        self.code = code


class CustomerMemoryCommands:
    @staticmethod
    def store_record(*, user, category: str, content: str, source_conversation_id: str = '',
                     channel: str = CustomerMemoryRecord.CHANNEL_UNKNOWN) -> CustomerMemoryRecord:
        category = (category or '').strip()
        content = (content or '').strip()
        channel = channel if channel in _VALID_CHANNELS else CustomerMemoryRecord.CHANNEL_UNKNOWN

        if category not in _VALID_CATEGORIES:
            policy.audit('rejected', user=user, category=category[:32], reason=policy.REASON_CATEGORY, channel=channel)
            raise MemoryRejected("categoria invalida", policy.REASON_CATEGORY)
        if not content:
            policy.audit('rejected', user=user, category=category, reason=policy.REASON_EMPTY, channel=channel)
            raise MemoryRejected("contenido vacio", policy.REASON_EMPTY)
        content = content[:_MAX_CONTENT_LENGTH]
        if _CARD_LIKE_PATTERN.search(content):
            policy.audit('rejected', user=user, category=category, reason=policy.REASON_SENSITIVE, channel=channel)
            raise MemoryRejected("contenido parece un numero de tarjeta/credencial", policy.REASON_SENSITIVE)
        if _CREDENTIAL_KEYWORDS.search(content):
            policy.audit('rejected', user=user, category=category, reason=policy.REASON_SENSITIVE, channel=channel)
            raise MemoryRejected("contenido menciona una credencial explicitamente", policy.REASON_SENSITIVE)

        # HARDENING F7/C1: autoridad/instrucciones y datos sensibles ampliados (modo monitor con AI_MEMORY_GATE_STRICT=false).
        reason = policy.evaluate_content(content)
        if reason:
            policy.audit('rejected' if policy.is_strict() else 'would_reject', user=user, category=category, reason=reason,
                         channel=channel)
            if policy.is_strict():
                message = ("el recuerdo expresa autoridad o una instruccion (nunca se guarda como memoria)"
                           if reason == policy.REASON_AUTHORITY else
                           "el recuerdo contiene un dato sensible (credencial, contacto o documento)")
                raise MemoryRejected(message, reason)

        # Dedup simple: no duplicar el mismo hecho activo para el mismo cliente -- se renueva su vigencia.
        existing = CustomerMemoryRecord.objects.filter(
            customer=user, is_active=True, is_deleted=False, category=category, content=content,
        ).first()
        if existing:
            existing.expires_at = policy.expiry_for(category)
            existing.save(update_fields=['expires_at', 'updated_at'])
            policy.audit('deduped', user=user, category=category, channel=channel)
            return existing

        record = CustomerMemoryRecord.objects.create(
            customer=user, category=category, content=content,
            source_conversation_id=source_conversation_id[:128], channel=channel, origin='user_message',
            expires_at=policy.expiry_for(category),
        )
        policy.audit('stored', user=user, category=category, channel=channel)
        return record

    @staticmethod
    def deactivate(record: CustomerMemoryRecord) -> None:
        """Revisable -- un admin puede desactivar un recuerdo incorrecto sin borrarlo (soft, distinto de is_deleted)."""
        record.is_active = False
        record.save(update_fields=['is_active', 'updated_at'])

    @staticmethod
    def forget_record(user, record_uuid) -> bool:
        """Borrado fisico de UN recuerdo del propio cliente (derecho de supresion). True si existia."""
        deleted, _ = CustomerMemoryRecord.objects.filter(customer=user, uuid=record_uuid).delete()
        if deleted:
            policy.audit('forgotten', user=user, reason='single')
        return bool(deleted)

    @staticmethod
    def forget_all(user) -> int:
        """Derecho al olvido (Habeas Data): borrado FISICO de toda la memoria del cliente. Devuelve cuantos registros."""
        deleted, _ = CustomerMemoryRecord.objects.filter(customer=user).delete()
        policy.audit('forgotten', user=user, reason='all', extra=f'count={deleted}')
        return deleted

    @staticmethod
    def purge_expired(grace_days: int = 30) -> int:
        """Borrado fisico de recuerdos expirados hace mas de `grace_days` (los expirados ya no se devuelven en lecturas)."""
        cutoff = timezone.now() - timedelta(days=grace_days)
        deleted, _ = CustomerMemoryRecord.objects.filter(expires_at__isnull=False, expires_at__lt=cutoff).delete()
        policy.audit('expired', reason='purge', extra=f'count={deleted}')
        return deleted
