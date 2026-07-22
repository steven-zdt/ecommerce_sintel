from rest_framework import serializers
from users.models import User
from technical_services.models import WorkingSchedule, WorkingException


# ---- WorkingSchedule --------------------------------------------------------

class WorkingScheduleSerializer(serializers.ModelSerializer):
    technician_uuid = serializers.UUIDField(source='technician.uuid', read_only=True)
    technician_name = serializers.SerializerMethodField()
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = WorkingSchedule
        fields = [
            'uuid', 'technician_uuid', 'technician_name',
            'weekday', 'weekday_display', 'start_time', 'end_time', 'is_active',
        ]
        read_only_fields = fields

    def get_technician_name(self, obj):
        return obj.technician.get_short_name()


class WorkingScheduleInputSerializer(serializers.Serializer):
    technician = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=User.objects.filter(is_deleted=False),
    )
    weekday = serializers.ChoiceField(choices=WorkingSchedule.WEEKDAY_CHOICES)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    is_active = serializers.BooleanField(default=True)


# ---- WorkingException --------------------------------------------------------

class WorkingExceptionSerializer(serializers.ModelSerializer):
    technician_uuid = serializers.UUIDField(source='technician.uuid', read_only=True)
    technician_name = serializers.SerializerMethodField()
    exception_type_display = serializers.CharField(source='get_exception_type_display', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, allow_null=True)

    class Meta:
        model = WorkingException
        fields = [
            'uuid', 'technician_uuid', 'technician_name',
            'exception_type', 'exception_type_display',
            'start_date', 'end_date', 'start_time', 'end_time',
            'reason', 'created_by_email', 'created_at',
        ]
        read_only_fields = fields

    def get_technician_name(self, obj):
        return obj.technician.get_short_name()


class WorkingExceptionInputSerializer(serializers.Serializer):
    technician = serializers.SlugRelatedField(
        slug_field='uuid',
        queryset=User.objects.filter(is_deleted=False),
    )
    exception_type = serializers.ChoiceField(choices=WorkingException.TYPE_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_time = serializers.TimeField(required=False, allow_null=True, default=None)
    end_time = serializers.TimeField(required=False, allow_null=True, default=None)
    reason = serializers.CharField(required=False, allow_blank=True, default='')


# ---- TechnicianAvailabilityEngine (solo lectura, formas calculadas) ---------

class AvailableTechnicianSerializer(serializers.Serializer):
    technician_id = serializers.IntegerField()
    technician_uuid = serializers.UUIDField()
    technician_name = serializers.CharField()
    free_windows = serializers.ListField(
        child=serializers.ListField(child=serializers.TimeField(), min_length=2, max_length=2)
    )


class CapacitySummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    technicians_total = serializers.IntegerField()
    technicians_available = serializers.IntegerField()
    technicians_busy = serializers.IntegerField()
    capacity_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    free_hours = serializers.DecimalField(max_digits=8, decimal_places=2)
    occupied_hours = serializers.DecimalField(max_digits=8, decimal_places=2)


class CapacitySummaryTotalsSerializer(serializers.Serializer):
    capacity_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    free_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    occupied_hours = serializers.DecimalField(max_digits=10, decimal_places=2)


class CapacitySummaryRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = CapacitySummarySerializer(many=True)
    totals = CapacitySummaryTotalsSerializer()


# ---- Calendario (Fase 4) -----------------------------------------------------

class CalendarWorkingWindowSerializer(serializers.Serializer):
    start = serializers.TimeField()
    end = serializers.TimeField()


class CalendarExceptionSerializer(serializers.Serializer):
    exception_type = serializers.CharField()
    exception_type_display = serializers.CharField()
    start_time = serializers.TimeField(allow_null=True)
    end_time = serializers.TimeField(allow_null=True)
    reason = serializers.CharField()


class CalendarOperationSerializer(serializers.Serializer):
    uuid = serializers.UUIDField()
    start_time = serializers.TimeField(allow_null=True)
    end_time = serializers.TimeField(allow_null=True)
    estimated_duration_minutes = serializers.IntegerField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    order_uuid = serializers.UUIDField()
    customer_name = serializers.CharField()
    priority = serializers.CharField()


class CalendarDaySerializer(serializers.Serializer):
    date = serializers.DateField()
    working_window = CalendarWorkingWindowSerializer(allow_null=True)
    exceptions = CalendarExceptionSerializer(many=True)
    operations = CalendarOperationSerializer(many=True)


class CalendarTechnicianSerializer(serializers.Serializer):
    technician_id = serializers.IntegerField()
    technician_uuid = serializers.UUIDField()
    technician_name = serializers.CharField()
    days = CalendarDaySerializer(many=True)


class CalendarFeedSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    technicians = CalendarTechnicianSerializer(many=True)
