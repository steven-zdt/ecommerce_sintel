# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.db import models
from ecommerce.base_models import SintelBaseModel

from .equipment import Equipment

class EquipmentLogisticsConfig(SintelBaseModel):
    """Costos de logistica y puesta en marcha configurados por el admin para un equipo.
    Todos los campos son opcionales — no todos los equipos requieren estos costos."""

    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='logistics_config'
    )
    delivery_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de entrega'
    )
    pickup_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de recogida'
    )
    installation_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de instalacion'
    )
    calibration_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de calibracion'
    )
    training_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de capacitacion'
    )
    startup_cost = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        verbose_name='costo de puesta en marcha'
    )
    notes = models.TextField(blank=True, default='', verbose_name='notas adicionales')

    class Meta:
        verbose_name = 'configuracion de logistica'
        verbose_name_plural = 'configuraciones de logistica'

    def __str__(self):
        return f"Logistica -- {self.equipment.name}"

