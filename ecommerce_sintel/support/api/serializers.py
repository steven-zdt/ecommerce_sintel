from rest_framework import serializers
from support.models import ChatRoom, ChatMessage, SupportTicket


class RateConversationInputSerializer(serializers.Serializer):
    """CSAT: mismo patron que renting.EquipmentReviewInputSerializer, salvo que
    aca el comentario es opcional -- exigirlo bajaria la tasa de respuesta de
    una calificacion rapida de 1-5."""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=2000, required=False, allow_blank=True, default='')


class CreateSupportTicketInputSerializer(serializers.Serializer):
    """Ticket abierto DIRECTAMENTE por el cliente desde su perfil (2026-09-16)
    -- segundo flujo real de creacion de SupportTicket, distinto del Human
    Handoff via IA (AiOpenSupportTicketView). subject/description son el
    minimo real para que un operador humano pueda empezar a trabajar el
    caso sin tener que pedirle al cliente que repita lo que ya escribio."""
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=4000)
    category = serializers.ChoiceField(choices=SupportTicket.CATEGORY_CHOICES, required=False, allow_blank=True, default='')


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


class SupportTicketSerializer(serializers.ModelSerializer):
    assigned_admin_email = serializers.SerializerMethodField()
    # 2026-09-16: room_uuid/customer_email -- necesarios para la vista dedicada
    # de tickets (AdminSupportTicketViewSet), que lista SupportTicket sin pasar
    # por ChatRoomSerializer -- el admin necesita el uuid de la sala para poder
    # abrir la conversacion real desde la lista. select_related('chat_room',
    # 'chat_room__user') ya viene armado en SupportTicketSelector.list_for_admin,
    # no dispara una consulta nueva por fila.
    room_uuid = serializers.CharField(source='chat_room.uuid', read_only=True)
    customer_email = serializers.EmailField(source='chat_room.user.email', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'uuid', 'ticket_number', 'subject', 'summary', 'status', 'priority', 'category',
            'assigned_admin_email', 'contact_phone', 'contact_email',
            'created_at', 'resolved_at', 'closed_at', 'room_uuid', 'customer_email',
        ]

    def get_assigned_admin_email(self, obj):
        return obj.assigned_admin.email if obj.assigned_admin else None


class ChatRoomListSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    contexts = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['uuid', 'user_email', 'status', 'created_at', 'updated_at', 'unread_count', 'last_message', 'contexts', 'ticket']

    def get_ticket(self, obj):
        # obj.ticket reusa el select_related('ticket') de ChatSelector -- nunca dispara
        # una consulta nueva por sala listada. RelatedObjectDoesNotExist para salas sin
        # ticket (todas las anteriores al 2026-09-15, o abiertas sin Human Handoff).
        ticket = getattr(obj, 'ticket', None)
        return SupportTicketSerializer(ticket).data if ticket else None

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
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'uuid', 'user_email', 'user_uuid', 'status', 'assigned_admin_email',
            'created_at', 'updated_at', 'messages', 'contexts', 'ticket',
            'csat_rating', 'csat_comment',
        ]

    def get_assigned_admin_email(self, obj):
        return obj.assigned_admin.email if obj.assigned_admin else None

    def get_contexts(self, obj):
        active = [c for c in obj.contexts.all() if not c.is_deleted]
        return ChatRoomContextSerializer(active, many=True).data

    def get_ticket(self, obj):
        ticket = getattr(obj, 'ticket', None)
        return SupportTicketSerializer(ticket).data if ticket else None
