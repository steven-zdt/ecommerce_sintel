from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.conf import settings
from ecommerce.base_models import SintelBaseModel


class ChatRoom(SintelBaseModel):
    STATUS_OPEN   = 'OPEN'
    STATUS_CLOSED = 'CLOSED'
    STATUS_CHOICES = [
        (STATUS_OPEN,   'Abierta'),
        (STATUS_CLOSED, 'Cerrada'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_rooms',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_support_rooms',
    )
    # Fase 7 AI Core: True cuando el asistente IA escalo la sala a un humano
    # (Human Handoff) -- el modo AI del consumer deja de responder aqui.
    ai_paused = models.BooleanField(default=False)
    # CSAT: calificacion del cliente tras cerrar la sala (1-5 + comentario
    # opcional). Null hasta que el cliente califique; solo permitido una vez
    # (ver ChatCommands.rate_conversation) sobre una sala ya CLOSED.
    csat_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    csat_comment = models.TextField(blank=True, default='')
    csat_rated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            # Repaso de backlog (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md, 2026-08-03):
            # notify_unattended_escalated_tickets (Fase 1) filtra por estas 4 columnas juntas en
            # cada corrida horaria -- status/updated_at/is_deleted ya tenian db_index individual,
            # pero ai_paused no tenia ninguno, y sin un indice compuesto Postgres solo puede
            # combinarlos via bitmap AND en vez de un unico index scan.
            models.Index(fields=['status', 'ai_paused', 'updated_at', 'is_deleted']),
        ]

    def __str__(self):
        return f'ChatRoom({self.user_id}, {self.status})'


class ChatMessage(SintelBaseModel):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='support_messages',
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    # Fase 8 AI Core: telemetria del turno cuando sender es el bot IA (agente,
    # intent, tools ejecutadas, tokens, duracion) -- ver ai_bridge.ask_ai() y
    # ai_engine/observability.py::TurnMetrics. Null para mensajes humanos.
    ai_metrics = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'ChatMessage({self.room_id}, {self.sender_id})'

    @property
    def is_from_agent(self) -> bool:
        """True si el mensaje debe mostrarse del lado 'agente' (admin humano o bot IA).

        Unica fuente de verdad -- antes esta regla vivia duplicada en
        ChatMessageSerializer.get_is_admin (solo staff+superuser, sin el bot IA) y en
        consumers.py::_get_room_history (staff+superuser O bot IA), asi que el historial
        REST que consume el panel admin atribuia los mensajes de la IA al cliente (bubble
        y remitente equivocados) mientras que el WebSocket los mostraba bien. El bot IA
        (ai_bridge.get_ai_bot_user) es is_active=False con password inutilizable, nunca
        is_staff/is_superuser, por eso necesita el chequeo explicito por email.
        """
        return bool(
            (self.sender.is_staff and self.sender.is_superuser)
            or self.sender.email == settings.AI_BOT_EMAIL
        )


class ChatRoomContext(SintelBaseModel):
    """
    Vinculo opcional de una sala de soporte a una entidad de negocio (Customer Experience
    Hub). FKs reales por tipo, no GenericForeignKey+object_id -- ese patron ya genero un bug
    real en inventory (object_id guardaba uuid, GenericForeignKey esperaba pk). Una sala
    puede tener multiples contextos (una fila por cada uno); support nunca posee estos
    datos, solo los referencia.
    """
    CONTEXT_ORDER = 'ORDER'
    CONTEXT_RENTAL = 'RENTAL'
    CONTEXT_CHOICES = [
        (CONTEXT_ORDER, 'Pedido'),
        (CONTEXT_RENTAL, 'Alquiler'),
    ]

    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='contexts')
    context_type = models.CharField(max_length=20, choices=CONTEXT_CHOICES)
    # CASCADE (no SET_NULL): la constraint de abajo exige exactamente un target no-nulo por
    # fila -- si el Order/RentalRequest referenciado se borra de verdad (hard delete), la fila
    # de contexto deja de tener sentido y debe desaparecer con el, no quedar con order=NULL
    # violando la constraint (bug real encontrado en pruebas: SET_NULL + esta constraint
    # generaba un IntegrityError al borrar un Order con contexto attachado).
    order = models.ForeignKey(
        'orders.Order', null=True, blank=True, on_delete=models.CASCADE,
        related_name='support_contexts',
    )
    rental_request = models.ForeignKey(
        'renting.RentalRequest', null=True, blank=True, on_delete=models.CASCADE,
        related_name='support_contexts',
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(context_type='ORDER', order__isnull=False, rental_request__isnull=True)
                    | Q(context_type='RENTAL', rental_request__isnull=False, order__isnull=True)
                ),
                name='chatroomcontext_exactly_one_target',
            ),
        ]

    def __str__(self):
        return f'ChatRoomContext({self.room_id}, {self.context_type})'

    # D1 (auditoria enterprise, 2026-07-31): unica fuente de verdad para "uuid/label de
    # la entidad referenciada" -- antes esta rama context_type->{ORDER,RENTAL} vivia
    # duplicada en consumers.py::_get_room_contexts (payload WS) y en
    # ChatRoomContextSerializer (payload REST), con riesgo real de divergir.
    @property
    def target_uuid(self) -> str | None:
        if self.context_type == self.CONTEXT_ORDER and self.order:
            return str(self.order.uuid)
        if self.context_type == self.CONTEXT_RENTAL and self.rental_request:
            return str(self.rental_request.uuid)
        return None

    @property
    def label(self) -> str:
        if self.context_type == self.CONTEXT_ORDER and self.order:
            return f'Pedido #{self.order.id}'
        if self.context_type == self.CONTEXT_RENTAL and self.rental_request:
            return f'Alquiler #{self.rental_request.id}'
        return ''
