"""customer_memory/services/commands.py -- FASE 9, Mision RAG-POST2.

Defensa en profundidad: el extractor de ai_engine_adk (FASE 10) es la
PRIMERA linea (el LLM no deberia proponer guardar un rol/credencial), pero
Django NUNCA confia ciegamente en lo que llega por HTTP interno -- esta
Command es la SEGUNDA linea, real, server-side, que se aplica sin importar
que tan bien o mal se haya comportado el extractor."""
import re

from ..models import CustomerMemoryRecord

_VALID_CATEGORIES = {choice[0] for choice in CustomerMemoryRecord.CATEGORY_CHOICES}

# Patrones que NUNCA deben persistirse como memoria, sin importar la
# categoria propuesta -- numero tipo tarjeta (13-19 digitos, con o sin
# separadores) y menciones directas de credenciales. No pretende ser un DLP
# completo -- es la barrera minima contra el caso obvio (Regla: nunca
# almacenar datos sensibles como memoria, ver FASE 8).
_CARD_LIKE_PATTERN = re.compile(r'(?:\d[ -]?){13,19}')
_CREDENTIAL_KEYWORDS = re.compile(
    r'\b(contrase[nñ]a|password|clave secreta|pin\b|cvv|numero de tarjeta)\b', re.I,
)
_MAX_CONTENT_LENGTH = 280


class MemoryRejected(Exception):
    """El contenido propuesto no cumple la politica de memoria -- nunca se
    persiste, ni siquiera desactivado."""


class CustomerMemoryCommands:
    @staticmethod
    def store_record(*, user, category: str, content: str, source_conversation_id: str = '') -> CustomerMemoryRecord:
        category = (category or '').strip()
        content = (content or '').strip()

        if category not in _VALID_CATEGORIES:
            raise MemoryRejected(f"categoria invalida: {category!r}")
        if not content:
            raise MemoryRejected("contenido vacio")
        if len(content) > _MAX_CONTENT_LENGTH:
            content = content[:_MAX_CONTENT_LENGTH]
        if _CARD_LIKE_PATTERN.search(content):
            raise MemoryRejected("contenido parece un numero de tarjeta/credencial")
        if _CREDENTIAL_KEYWORDS.search(content):
            raise MemoryRejected("contenido menciona una credencial explicitamente")

        # Dedup simple: no duplicar el mismo hecho activo para el mismo
        # cliente -- si ya existe algo identico, no crea una fila nueva.
        existing = CustomerMemoryRecord.objects.filter(
            customer=user, is_active=True, is_deleted=False, category=category, content=content,
        ).first()
        if existing:
            return existing

        return CustomerMemoryRecord.objects.create(
            customer=user, category=category, content=content,
            source_conversation_id=source_conversation_id,
        )

    @staticmethod
    def deactivate(record: CustomerMemoryRecord) -> None:
        """Revisable -- un admin puede desactivar un recuerdo incorrecto sin
        borrarlo (soft, distinto de is_deleted)."""
        record.is_active = False
        record.save(update_fields=['is_active', 'updated_at'])
