"""customer_memory/services/selectors.py -- FASE 9, Mision RAG-POST2; endurecido en HARDENING F7 (2026-09-24)."""
from django.db.models import Q
from django.utils import timezone

from ..models import CustomerMemoryRecord
from . import policy


class CustomerMemorySelector:
    @staticmethod
    def _active_qs(user):
        now = timezone.now()
        return (
            CustomerMemoryRecord.objects
            .filter(customer=user, is_active=True, is_deleted=False)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        )

    @staticmethod
    def list_active_for_customer(user, limit: int = 5) -> list[dict]:
        """Ultimos `limit` recuerdos VIGENTES del cliente -- mas recientes primero. Deliberadamente simple (sin busqueda semantica).

        HARDENING F7/C5: excluye expirados y, como defensa en profundidad, EXCLUYE Y REGISTRA cualquier recuerdo que hoy no pasaria
        la barrera de escritura (registros guardados antes de F7 con autoridad/instrucciones o datos sensibles)."""
        out: list[dict] = []
        for r in CustomerMemorySelector._active_qs(user).order_by('-created_at')[: max(limit * 3, limit)]:
            reason = policy.evaluate_content(r.content)
            if reason and policy.is_strict():
                policy.audit('excluded_on_read', user=user, category=r.category, reason=reason, channel=r.channel)
                continue
            out.append({'category': r.category, 'content': r.content, 'created_at': r.created_at.isoformat()})
            if len(out) >= limit:
                break
        return out

    @staticmethod
    def list_for_owner(user) -> list[dict]:
        """Vista del PROPIO cliente (Habeas Data): todo lo vigente que el asistente recuerda, con su identificador para poder borrarlo."""
        return [
            {'uuid': str(r.uuid), 'category': r.category, 'content': r.content, 'channel': r.channel,
             'created_at': r.created_at.isoformat(), 'expires_at': r.expires_at.isoformat() if r.expires_at else None}
            for r in CustomerMemorySelector._active_qs(user).order_by('-created_at')
        ]
