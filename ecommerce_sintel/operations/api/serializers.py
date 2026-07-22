from rest_framework import serializers
from operations.models import (
    OperationTicket, TrackingEvent, OperationDocument,
    OperationAssignment, OperationReview, DispatcherProfile,
)
from orders.api.serializers import OrderSerializer


class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model  = TrackingEvent
        fields = ['uuid', 'milestone', 'description', 'created_at', 'metadata']


class OperationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OperationDocument
        fields = ['uuid', 'doc_type', 'status', 'rejection_reason', 'created_at']


class OperationAssignmentSerializer(serializers.ModelSerializer):
    assignee_email = serializers.EmailField(source='assignee.email', read_only=True)
    assignee_name  = serializers.SerializerMethodField()

    class Meta:
        model  = OperationAssignment
        fields = ['uuid', 'role', 'assignee_email', 'assignee_name', 'status', 'created_at']

    def get_assignee_name(self, obj):
        return getattr(obj.assignee, 'get_full_name', lambda: obj.assignee.email)()


class OperationReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model  = OperationReview
        fields = [
            'uuid', 'rating', 'quality_rating', 'punctuality_rating',
            'condition_rating', 'comment', 'created_at',
        ]


class OperationTicketListSerializer(serializers.ModelSerializer):
    # [2026-07-12] CORE v4 Fase 5 Paso 2 -- estado derivado del satelite especifico cuando
    # existe (ver OperationTicket.get_effective_status()). Aditivo: `status` (el campo real)
    # sigue igual, sin romper OperationTicketSelector.list_all(status=...). El frontend sigue
    # leyendo `status` hasta que se conecte a `effective_status` en Fase 6.
    effective_status = serializers.CharField(source='get_effective_status', read_only=True)

    class Meta:
        model  = OperationTicket
        fields = [
            'uuid', 'ticket_number', 'operation_type', 'status', 'effective_status',
            'priority', 'scheduled_date', 'created_at',
        ]


class OperationTicketDetailSerializer(serializers.ModelSerializer):
    tracking_events   = TrackingEventSerializer(many=True, read_only=True)
    documents         = OperationDocumentSerializer(many=True, read_only=True)
    assignments       = OperationAssignmentSerializer(many=True, read_only=True)
    review            = OperationReviewSerializer(read_only=True)
    source_order      = OrderSerializer(read_only=True)
    effective_status  = serializers.CharField(source='get_effective_status', read_only=True)

    class Meta:
        model  = OperationTicket
        fields = [
            'uuid', 'ticket_number', 'operation_type', 'status', 'effective_status', 'priority',
            'source_order',
            'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
            'location_address', 'location_city', 'location_department',
            'tracking_events', 'documents', 'assignments', 'review',
            'created_at', 'updated_at',
        ]


class DocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=OperationDocument.DOC_TYPE_CHOICES)
    file     = serializers.FileField()


class ReviewSubmitSerializer(serializers.Serializer):
    rating             = serializers.IntegerField(min_value=1, max_value=5)
    quality_rating     = serializers.IntegerField(min_value=1, max_value=5, default=5)
    punctuality_rating = serializers.IntegerField(min_value=1, max_value=5, default=5)
    condition_rating   = serializers.IntegerField(min_value=1, max_value=5, default=5)
    comment            = serializers.CharField(required=False, allow_blank=True, default='')


# ── Admin / Dashboard serializers ─────────────────────────────────────────────

class DispatcherProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model  = DispatcherProfile
        fields = [
            'uuid', 'email', 'dispatcher_type', 'vehicle_plate',
            'vehicle_type', 'coverage_cities', 'is_available', 'is_active',
            'created_at',
        ]


class AdminTicketBoardSerializer(serializers.ModelSerializer):
    """
    [2026-07-12, Fase 8] Este es el serializer REAL que alimenta el tablero admin unificado
    (dashboard/operations/ -> AdminOperationViewSet -> frontend/OperationBoard.vue) -- NO
    OperationTicketListSerializer/OperationTicketDetailSerializer (esos sirven el endpoint
    del cliente en /api/v1/operations/my/). effective_status se agrego aqui, no ahi -- bug
    real encontrado en la regresion de Fase 8: el campo ya se habia conectado en el frontend
    pero no en el serializer correcto, hubiera mostrado "undefined" en el tablero.
    """
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    assignees      = serializers.SerializerMethodField()
    effective_status = serializers.CharField(source='get_effective_status', read_only=True)

    class Meta:
        model  = OperationTicket
        fields = [
            'uuid', 'ticket_number', 'operation_type', 'status', 'effective_status', 'priority',
            'customer_email', 'scheduled_date', 'location_city', 'assignees',
            'created_at',
        ]

    def get_assignees(self, obj):
        return [
            {'email': a.assignee.email, 'role': a.role}
            for a in obj.assignments.all()
            if a.status == 'ACTIVE'
        ]


class AdminAssignSerializer(serializers.Serializer):
    assignee_id = serializers.IntegerField()
    role        = serializers.ChoiceField(choices=OperationAssignment.ROLE_CHOICES)


class AdminScheduleSerializer(serializers.Serializer):
    scheduled_date       = serializers.DateField()
    scheduled_time_start = serializers.TimeField()
    scheduled_time_end   = serializers.TimeField()

    def validate(self, attrs):
        from django.utils import timezone
        if attrs['scheduled_date'] < timezone.localdate():
            raise serializers.ValidationError('La fecha programada no puede estar en el pasado.')
        if attrs['scheduled_time_start'] >= attrs['scheduled_time_end']:
            raise serializers.ValidationError('La hora final debe ser posterior a la hora inicial.')
        return attrs


class AdminTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=OperationTicket.STATUS_CHOICES)
    note   = serializers.CharField(required=False, allow_blank=True, default='')


class AdminDocReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    reason   = serializers.CharField(required=False, allow_blank=True, default='')
