from rest_framework import serializers

from operations.models import DispatcherProfile
from renting.models import RentalOperation, RentalOperationEvent, RentalRequest


class RentalOperationEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = RentalOperationEvent
        fields = ['uuid', 'event_type', 'description', 'actor_name', 'metadata', 'created_at']

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() or obj.actor.email if obj.actor else ''


class RentalOperationSerializer(serializers.ModelSerializer):
    request_uuid = serializers.UUIDField(source='rental_request.uuid', read_only=True)
    equipment_name = serializers.CharField(
        source='rental_request.equipment_variant.equipment.name', read_only=True
    )
    customer_name = serializers.SerializerMethodField()
    location_address = serializers.CharField(source='rental_request.location_address', read_only=True)
    dispatcher_name = serializers.SerializerMethodField()
    dispatcher_uuid = serializers.UUIDField(source='assigned_dispatcher.uuid', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    timeline = RentalOperationEventSerializer(many=True, read_only=True)
    # Computado, no almacenado -- ver renting/models.py RentalOperation (sin
    # columna propia a proposito, se lee siempre de la RentalRequest padre).
    commercial_type = serializers.CharField(source='rental_request.commercial_type', read_only=True)

    class Meta:
        model = RentalOperation
        fields = [
            'uuid', 'request_uuid', 'status', 'status_display', 'priority', 'equipment_name',
            'customer_name', 'location_address', 'dispatcher_uuid', 'commercial_type',
            'dispatcher_name', 'assigned_vehicle', 'delivery_date', 'delivery_time',
            'pickup_date', 'pickup_time', 'estimated_duration_minutes', 'route',
            'notes', 'has_incident', 'incident_notes', 'timeline', 'created_at', 'updated_at',
        ]

    def get_customer_name(self, obj):
        user = obj.rental_request.user
        return user.get_full_name() or user.email

    def get_dispatcher_name(self, obj):
        if not obj.assigned_dispatcher:
            return ''
        user = obj.assigned_dispatcher.user
        return user.get_full_name() or user.email


class RentalOperationScheduleSerializer(serializers.Serializer):
    delivery_date = serializers.DateField()
    delivery_time = serializers.TimeField()
    pickup_date = serializers.DateField()
    pickup_time = serializers.TimeField()
    estimated_duration_minutes = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    route = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=RentalRequest.PRIORITY_CHOICES, required=False)


class RentalOperationAssignSerializer(serializers.Serializer):
    dispatcher_uuid = serializers.SlugRelatedField(
        slug_field='uuid', source='dispatcher',
        queryset=DispatcherProfile.objects.filter(is_active=True, is_deleted=False),
    )
    vehicle = serializers.CharField(required=False, allow_blank=True)


class RentalOperationIncidentSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=False)
