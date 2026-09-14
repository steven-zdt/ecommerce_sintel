from decimal import Decimal

from rest_framework import serializers

from orders.models import Order
from technical_services.models import ServiceOperation, ServiceOperationEvent
from technical_services.api.serializers import TechnicianCandidateSerializer, ServiceAttachmentSerializer


class ServiceOperationEventSerializer(serializers.ModelSerializer):
    milestone = serializers.CharField(source='event_type')
    actor_email = serializers.ReadOnlyField(source='actor.email')

    class Meta:
        model = ServiceOperationEvent
        fields = ['uuid', 'milestone', 'description', 'actor_email', 'created_at']


class ServiceOperationOrderSummarySerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    is_paid = serializers.SerializerMethodField()
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.SerializerMethodField()
    service_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    contact_person = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    quotation = serializers.SerializerMethodField()

    def get_is_paid(self, obj):
        return obj.status in (Order.STATUS_PAID, Order.STATUS_DELIVERED, Order.STATUS_COMPLETED)

    def get_user_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_service_name(self, obj):
        item = obj.items.filter(service_variant__isnull=False).first()
        return item.item_name if item else ''

    def get_address(self, obj):
        detail = getattr(obj, 'service_detail', None)
        return detail.address if detail else ''

    def get_priority(self, obj):
        detail = getattr(obj, 'service_detail', None)
        return detail.priority if detail else None

    def get_contact_person(self, obj):
        detail = getattr(obj, 'service_detail', None)
        return detail.contact_person if detail else None

    def get_attachments(self, obj):
        return ServiceAttachmentSerializer(obj.attachments.all(), many=True, context=self.context).data

    def get_quotation(self, obj):
        detail = getattr(obj, 'service_detail', None)
        if not detail:
            return None
        return {
            'rate_type': detail.applied_rate_type,
            'rate_amount': str(detail.applied_rate_amount) if detail.applied_rate_amount is not None else None,
            'discount_amount': str(obj.discount_amount),
            'total_amount': str(obj.total_amount),
            # Plan "Manual Pricing Engine" FASE 16/18 -- bloque "PRECIO COMERCIAL"
            # del panel de operaciones. price_status/confirmed_total son el estado
            # editable (ver OrderPricingCommands); el resto es el snapshot
            # congelado al momento de la orden (FASE 2), nunca reconstruido desde
            # la ServiceVariant actual (que puede haber cambiado desde entonces).
            'pricing_source_snapshot': detail.pricing_source_snapshot,
            'pricing_mode_snapshot': detail.pricing_mode_snapshot,
            'unit_price_snapshot': str(detail.unit_price_snapshot) if detail.unit_price_snapshot is not None else None,
            'project_price_snapshot': str(detail.project_price_snapshot) if detail.project_price_snapshot is not None else None,
            'price_status': detail.price_status,
            'price_status_display': detail.get_price_status_display(),
            'confirmed_total': str(detail.confirmed_total) if detail.confirmed_total is not None else None,
        }


class ServiceOperationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    technician_email = serializers.ReadOnlyField(source='technician.email')
    technician_name = serializers.SerializerMethodField()
    technician_profile_uuid = serializers.SerializerMethodField()
    order = ServiceOperationOrderSummarySerializer(read_only=True)
    timeline = ServiceOperationEventSerializer(many=True, read_only=True)

    class Meta:
        model = ServiceOperation
        fields = [
            'uuid', 'status', 'status_display', 'scheduled_date', 'scheduled_time',
            'estimated_duration_minutes', 'technician_email', 'technician_name',
            'technician_profile_uuid', 'vehicle', 'route', 'notes', 'arrived_at',
            'started_at', 'completed_at', 'closure_status', 'has_incident',
            'incident_notes', 'priority', 'order', 'timeline', 'created_at',
        ]
        read_only_fields = fields

    def get_technician_name(self, obj):
        if not obj.technician:
            return None
        return obj.technician.get_full_name() or obj.technician.email

    def get_technician_profile_uuid(self, obj):
        if not obj.technician:
            return None
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj.technician)
        return str(profile.uuid) if profile else None


class ServiceOperationPlanSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    estimated_duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True, default='')


class ServiceOperationAssignSerializer(serializers.Serializer):
    technician_uuid = serializers.UUIDField()

    def validate_technician_uuid(self, value):
        from users.models import User
        try:
            return User.objects.get(uuid=value, is_active=True, is_deleted=False)
        except User.DoesNotExist:
            raise serializers.ValidationError('Tecnico no encontrado.')


class ServiceOperationRescheduleSerializer(serializers.Serializer):
    scheduled_date = serializers.DateField()
    scheduled_time = serializers.TimeField()
    estimated_duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ServiceOperationCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ServiceOperationIncidentSerializer(serializers.Serializer):
    notes = serializers.CharField()


class ServiceOperationCloseSerializer(serializers.Serializer):
    closure_status = serializers.ChoiceField(
        choices=ServiceOperation.CLOSURE_CHOICES, required=False,
    )


class ServiceOperationPriceOverrideSerializer(serializers.Serializer):
    """Plan 'Manual Pricing Engine' FASE 19 -- payload de .../override-price/.
    `reason` es obligatorio aqui Y en OrderPricingCommands.override_price()
    (doble capa, mismo criterio que discount_pct en ServiceRequestInputSerializer)."""
    new_total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0'))
    reason = serializers.CharField()


class ServiceOperationTechnicianCandidateSerializer(TechnicianCandidateSerializer):
    city = serializers.SerializerMethodField()
    specialties = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    experience_count = serializers.SerializerMethodField()

    def get_city(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj)
        return profile.city if profile else None

    def get_experience_count(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj)
        return profile.professional_experiences.count() if profile else 0

    def get_specialties(self, obj):
        from accounts.services import ProfileResolver
        tech_profile = ProfileResolver.get_technician_profile(obj)
        if not tech_profile:
            return []
        return list(tech_profile.specialties.values_list('name', flat=True))

    def get_status_label(self, obj):
        from accounts.services import ProfileResolver
        tech_profile = ProfileResolver.get_technician_profile(obj)
        return 'available' if tech_profile and tech_profile.is_available else 'busy'
