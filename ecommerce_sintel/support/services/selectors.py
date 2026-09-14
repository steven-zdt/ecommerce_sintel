from collections import Counter
from datetime import timedelta

from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from support.models import ChatRoom, ChatMessage, ChatRoomContext

_CONTEXT_PREFETCH = 'contexts__order', 'contexts__rental_request'


class ChatSelector:

    @staticmethod
    def get_active_rooms():
        return (
            ChatRoom.objects
            .filter(status=ChatRoom.STATUS_OPEN, is_deleted=False)
            .select_related('user', 'assigned_admin')
            .prefetch_related('messages__sender', *_CONTEXT_PREFETCH)
            .order_by('-updated_at')
        )

    @staticmethod
    def get_room_by_uuid(uuid):
        return get_object_or_404(
            ChatRoom.objects
            .select_related('user', 'assigned_admin')
            .prefetch_related('messages__sender', *_CONTEXT_PREFETCH),
            uuid=uuid,
            is_deleted=False,
        )

    @staticmethod
    def get_room_history(room: ChatRoom):
        return (
            ChatMessage.objects
            .filter(room=room, is_deleted=False)
            .select_related('sender')
            .order_by('created_at')
        )

    @staticmethod
    def get_contexts_for_room(room: ChatRoom):
        return (
            ChatRoomContext.objects
            .filter(room=room, is_deleted=False)
            .select_related('order', 'rental_request')
            .order_by('-created_at')
        )


class ChatAnalyticsSelector:
    """
    Fase 9 AI Core (Aprendizaje): agrega ChatMessage.ai_metrics (JSONField,
    Fase 8) para el panel de analytics del Dashboard. `duration_ms`/tokens y
    `tools` (lista) no se agregan en SQL -- se trae `ai_metrics` de los turnos
    de IA en la ventana en UNA query y todo el computo se hace en Python en una
    sola pasada (evita depender de Cast/KeyTransform de JSONField no probado
    en este proyecto para agregaciones numericas/de arreglos).
    """

    @staticmethod
    def get_summary(days: int = 30) -> dict:
        cutoff = timezone.now() - timedelta(days=days)

        total_conversations = ChatRoom.objects.filter(
            created_at__gte=cutoff, is_deleted=False,
        ).count()

        # CSAT: csat_rating es un campo numerico real (no JSONField) -- Avg()/
        # Count() de Django ORM son seguros aca directamente, sin el riesgo de
        # agregacion sobre JSON que motivo hacer todo en Python para ai_metrics.
        csat = ChatRoom.objects.filter(
            created_at__gte=cutoff, csat_rating__isnull=False, is_deleted=False,
        ).aggregate(avg=Avg('csat_rating'), count=Count('id'))

        ai_metrics_list = list(
            ChatMessage.objects
            .filter(ai_metrics__isnull=False, created_at__gte=cutoff, is_deleted=False)
            .values_list('ai_metrics', flat=True)
        )

        # C2 (auditoria enterprise, 2026-07-31): ai_metrics ahora tambien incluye
        # marcadores de degradacion (engine_unavailable=True, sin duration/tokens/intent
        # reales -- ver consumers.py::_save_ai_degraded_marker) cuando el AI Engine no
        # responde. Se cuentan aparte para no ensuciar los promedios/tasas de turnos
        # reales con filas que no tienen esos datos.
        total_ai_turns = engine_unavailable_count = 0
        duration_sum = tokens_in_sum = tokens_out_sum = 0
        fallback_count = handoff_count = 0
        intent_counter = Counter()
        tool_counter = Counter()
        fallback_intent_counter = Counter()

        for metrics in ai_metrics_list:
            if metrics.get('engine_unavailable'):
                engine_unavailable_count += 1
                continue
            total_ai_turns += 1
            intent = metrics.get('intent') or 'unknown'
            intent_counter[intent] += 1
            duration_sum += metrics.get('duration_ms') or 0
            tokens_in_sum += metrics.get('llm_tokens_in') or 0
            tokens_out_sum += metrics.get('llm_tokens_out') or 0
            for tool in metrics.get('tools') or []:
                if isinstance(tool, dict) and tool.get('tool'):
                    tool_counter[tool['tool']] += 1
            if metrics.get('fallback_used'):
                fallback_count += 1
                fallback_intent_counter[intent] += 1
            if metrics.get('handoff'):
                handoff_count += 1

        total_ai_attempts = total_ai_turns + engine_unavailable_count

        def _avg(total: int) -> float:
            return round(total / total_ai_turns, 1) if total_ai_turns else 0.0

        def _rate(count: int) -> float:
            return round(count / total_ai_turns, 4) if total_ai_turns else 0.0

        return {
            'window_days': days,
            'total_conversations': total_conversations,
            'avg_csat': round(csat['avg'], 2) if csat['avg'] is not None else None,
            'csat_responses_count': csat['count'],
            'total_ai_turns': total_ai_turns,
            'avg_duration_ms': _avg(duration_sum),
            'avg_tokens_in': _avg(tokens_in_sum),
            'avg_tokens_out': _avg(tokens_out_sum),
            'fallback_rate': _rate(fallback_count),
            'handoff_rate': _rate(handoff_count),
            # Motor de IA inalcanzable o con error (ask_ai() -> None) -- visibilidad que
            # antes no existia (C2, auditoria enterprise 2026-07-31).
            'engine_unavailable_count': engine_unavailable_count,
            'engine_unavailable_rate': (
                round(engine_unavailable_count / total_ai_attempts, 4) if total_ai_attempts else 0.0
            ),
            'intent_breakdown': [
                {'intent': intent, 'count': count}
                for intent, count in intent_counter.most_common(10)
            ],
            'top_tools': [
                {'tool': tool, 'count': count}
                for tool, count in tool_counter.most_common(10)
            ],
            'frequent_issues': [
                {'intent': intent, 'fallback_count': count}
                for intent, count in fallback_intent_counter.most_common(5)
            ],
        }
