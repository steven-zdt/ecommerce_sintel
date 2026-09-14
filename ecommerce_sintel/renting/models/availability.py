# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.conf import settings
from django.db import models
from ecommerce.base_models import SintelBaseModel

from .equipment import EquipmentVariant
from .requests import RentalRequest

class RentalPeriod(SintelBaseModel):
    """
    Reserva de tiempo de una EquipmentVariant.
    Controla la disponibilidad por solapamiento de fechas en lugar de descontar stock fisico.
    Se crea automaticamente al confirmar una RentalRequest y se cancela si el pago falla.
    """

    STATUS_SCHEDULED = 'scheduled'
    STATUS_ACTIVE    = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Programado'),
        (STATUS_ACTIVE,    'Activo'),
        (STATUS_COMPLETED, 'Completado'),
        (STATUS_CANCELLED, 'Cancelado'),
    ]

    rental_request = models.ForeignKey(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='periods',
    )
    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.PROTECT,
        related_name='rental_periods',
    )
    start_date = models.DateField(db_index=True)
    end_date   = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time   = models.TimeField(null=True, blank=True)
    rental_mode = models.CharField(
        max_length=10, choices=RentalRequest.RENTAL_MODE_CHOICES,
        default=RentalRequest.RENTAL_MODE_DAYS, db_index=True,
    )
    quantity   = models.PositiveIntegerField(default=1)
    status     = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED, db_index=True,
    )
    # Denormalizado desde RentalRequest.commercial_type al crear el periodo
    # (_create_blocking_period()), mismo motivo que rental_mode/quantity ya
    # denormalizados aqui: AvailabilityEngine es hot-path y no debe hacer join
    # al padre solo para etiquetar un bloqueo como Renting o Comodato.
    commercial_type = models.CharField(
        max_length=10, choices=RentalRequest.COMMERCIAL_TYPE_CHOICES,
        default=RentalRequest.COMMERCIAL_RENTAL, db_index=True,
    )

    class Meta:
        verbose_name = 'periodo de alquiler'
        verbose_name_plural = 'periodos de alquiler'
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['equipment_variant', 'status']),
            models.Index(
                fields=['equipment_variant', 'start_date', 'end_date'],
                name='renting_period_var_range_idx',
            ),
        ]

    def __str__(self):
        return f"RentalPeriod {self.equipment_variant.sku} {self.start_date}>{self.end_date} [{self.status}]"

class EquipmentBlock(SintelBaseModel):
    """
    Bloqueo manual de una EquipmentVariant por mantenimiento, daño o conteo de
    inventario -- no esta atado a ninguna RentalRequest. AvailabilityEngine lo
    suma como unidades ocupadas junto con RentalPeriod (ver services/availability.py).
    Una sola fila cubre todo el ciclo de vida (creacion + liberacion) como historial
    auditable, sin necesitar una tabla de eventos aparte.
    """

    TYPE_MAINTENANCE = 'MAINTENANCE'
    TYPE_DAMAGE = 'DAMAGE'
    TYPE_INVENTORY = 'INVENTORY'
    TYPE_OTHER = 'OTHER'
    BLOCK_TYPE_CHOICES = [
        (TYPE_MAINTENANCE, 'Mantenimiento'),
        (TYPE_DAMAGE, 'Daño'),
        (TYPE_INVENTORY, 'Conteo de inventario'),
        (TYPE_OTHER, 'Otro'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_RELEASED = 'released'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Activo'),
        (STATUS_RELEASED, 'Liberado'),
    ]

    equipment_variant = models.ForeignKey(
        EquipmentVariant,
        on_delete=models.CASCADE,
        related_name='blocks',
    )
    block_type = models.CharField(
        max_length=20, choices=BLOCK_TYPE_CHOICES, default=TYPE_MAINTENANCE, db_index=True,
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True,
    )
    reason = models.TextField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_blocks_created',
    )
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_blocks_released',
    )
    released_at = models.DateTimeField(null=True, blank=True)
    release_reason = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'bloqueo de equipo'
        verbose_name_plural = 'bloqueos de equipo'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['equipment_variant', 'status']),
            models.Index(
                fields=['equipment_variant', 'start_date', 'end_date'],
                name='renting_block_var_range_idx',
            ),
        ]

    def __str__(self):
        return f"Bloqueo {self.equipment_variant.sku} {self.start_date}>{self.end_date} [{self.status}]"

