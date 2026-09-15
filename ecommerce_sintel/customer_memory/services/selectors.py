"""customer_memory/services/selectors.py -- FASE 9, Mision RAG-POST2."""
from ..models import CustomerMemoryRecord


class CustomerMemorySelector:
    @staticmethod
    def list_active_for_customer(user, limit: int = 5) -> list[dict]:
        """Ultimos `limit` recuerdos activos del cliente -- mas recientes
        primero. Deliberadamente simple (sin busqueda semantica/embeddings):
        el volumen esperado por cliente es bajo (preferencias, no un corpus),
        Regla 1 de la mision ("no sobrearquitecturar") aplica aqui tambien --
        ver AUDITORIA/RAG_POST2_MEMORY_DEFINITION.md."""
        qs = (
            CustomerMemoryRecord.objects
            .filter(customer=user, is_active=True, is_deleted=False)
            .order_by('-created_at')[:limit]
        )
        return [
            {'category': r.category, 'content': r.content, 'created_at': r.created_at.isoformat()}
            for r in qs
        ]
