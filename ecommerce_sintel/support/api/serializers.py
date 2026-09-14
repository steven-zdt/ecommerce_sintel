from rest_framework import serializers
from support.models import ChatRoom, ChatMessage


class RateConversationInputSerializer(serializers.Serializer):
    """CSAT: mismo patron que renting.EquipmentReviewInputSerializer, salvo que
    aca el comentario es opcional -- exigirlo bajaria la tasa de respuesta de
    una calificacion rapida de 1-5."""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class ChatRoomContextSerializer(serializers.Serializer):
    context_type = serializers.CharField()
    uuid = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    def get_uuid(self, obj):
        # ChatRoomContext.target_uuid -- unica fuente de verdad, reusada por
        # consumers.py::_get_room_contexts (payload WS equivalente).
        return obj.target_uuid

    def get_label(self, obj):
        return obj.label


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['uuid', 'sender_email', 'is_admin', 'message', 'is_read', 'created_at', 'ai_metrics']

    def get_is_admin(self, obj):
        # ChatMessage.is_from_agent -- unica fuente de verdad (incluye al bot IA, no solo
        # staff+superuser). Antes esto se calculaba distinto aca que en consumers.py, y el
        # historial REST del panel admin atribuia los mensajes de la IA al cliente.
        return obj.is_from_agent


class ChatRoomListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    contexts = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['uuid', 'user_email', 'status', 'created_at', 'updated_at', 'unread_count', 'last_message', 'contexts']

    def get_contexts(self, obj):
        # obj.contexts.all() reusa el prefetch_related declarado en ChatSelector -- un
        # .filter() explicito aqui dispararia una consulta nueva por sala listada.
        active = [c for c in obj.contexts.all() if not c.is_deleted]
        return ChatRoomContextSerializer(active, many=True).data

    def get_unread_count(self, obj):
        # Filtra en Python sobre .all() para reusar el cache de prefetch_related
        # ('messages__sender' en ChatSelector) -- un .filter() explicito aqui
        # dispararia una consulta nueva por sala listada.
        return sum(1 for m in obj.messages.all() if not m.is_read and m.sender_id == obj.user_id)

    def get_last_message(self, obj):
        # ChatMessage.Meta.ordering = ['created_at'] (ascendente): el ultimo
        # elemento de .all() ya es el mensaje mas reciente, sin disparar una
        # consulta nueva como haria un .order_by('-created_at').first().
        messages = list(obj.messages.all())
        return messages[-1].message[:80] if messages else None


class ChatRoomSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_uuid = serializers.CharField(source='user.uuid', read_only=True)
    assigned_admin_email = serializers.SerializerMethodField()
    messages = ChatMessageSerializer(many=True, read_only=True)
    contexts = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'uuid', 'user_email', 'user_uuid', 'status', 'assigned_admin_email',
            'created_at', 'updated_at', 'messages', 'contexts',
            'csat_rating', 'csat_comment',
        ]

    def get_assigned_admin_email(self, obj):
        return obj.assigned_admin.email if obj.assigned_admin else None

    def get_contexts(self, obj):
        active = [c for c in obj.contexts.all() if not c.is_deleted]
        return ChatRoomContextSerializer(active, many=True).data
