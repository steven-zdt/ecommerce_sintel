# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.conf import settings
from django.db import models
from ecommerce.base_models import SintelBaseModel

from .requests import RentalRequest

class RentalOperation(SintelBaseModel):
    """Ciclo operativo exclusivo de una solicitud de renting aprobada."""

    READY_FOR_SCHEDULING = 'READY_FOR_SCHEDULING'
    SCHEDULED = 'SCHEDULED'
    TRANSPORT_ASSIGNED = 'TRANSPORT_ASSIGNED'
    READY_FOR_DELIVERY = 'READY_FOR_DELIVERY'
    DELIVERED = 'DELIVERED'
    IN_OPERATION = 'IN_OPERATION'
    READY_FOR_PICKUP = 'READY_FOR_PICKUP'
    PICKED_UP = 'PICKED_UP'
    RETURN_INSPECTION = 'RETURN_INSPECTION'
    COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (READY_FOR_SCHEDULING, 'Pendiente de programar'),
        (SCHEDULED, 'Programada'),
        (TRANSPORT_ASSIGNED, 'Transportista asignado'),
        (READY_FOR_DELIVERY, 'Lista para entrega'),
        (DELIVERED, 'Entregada'),
        (IN_OPERATION, 'En operacion'),
        (READY_FOR_PICKUP, 'Lista para recogida'),
        (PICKED_UP, 'Recogida'),
        (RETURN_INSPECTION, 'Inspeccion de devolucion'),
        (COMPLETED, 'Completada'),
    ]

    rental_request = models.OneToOneField(
        RentalRequest, on_delete=models.PROTECT, related_name='rental_operation'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default=READY_FOR_SCHEDULING, db_index=True,
    )
    assigned_dispatcher = models.ForeignKey(
        'operations.DispatcherProfile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rental_operations',
    )
    assigned_vehicle = models.CharField(max_length=120, blank=True, default='')
    delivery_date = models.DateField(null=True, blank=True, db_index=True)
    delivery_time = models.TimeField(null=True, blank=True)
    pickup_date = models.DateField(null=True, blank=True, db_index=True)
    pickup_time = models.TimeField(null=True, blank=True)
    estimated_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    route = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    priority = models.CharField(
        max_length=10, choices=RentalRequest.PRIORITY_CHOICES,
        default=RentalRequest.PRIORITY_LOW, db_index=True,
    )
    has_incident = models.BooleanField(default=False, db_index=True)
    incident_notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'delivery_date'])]

class RentalOperationEvent(SintelBaseModel):
    operation = models.ForeignKey(
        RentalOperation, on_delete=models.CASCADE, related_name='timeline'
    )
    event_type = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='rental_operation_events',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['created_at']

