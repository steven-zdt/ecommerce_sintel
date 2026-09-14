# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.conf import settings
from django.db import models
from ecommerce.base_models import SintelBaseModel

from .requests import RentalRequest

class EquipmentReturnInspection(SintelBaseModel):
    """
    Inspeccion de devolucion (2026-07-14). Registro opcional/aparte: NO gatea
    RentalRequestCommands.complete_period() (mark-returned) -- un admin la llena
    antes o despues, sin bloquear la operacion existente. Solo se permite sobre
    una RentalRequest ya en STATUS_FINISHED (el equipo ya volvio fisicamente).
    Si has_damage=True, EquipmentReturnInspectionCommands.create_inspection() crea
    automaticamente un EquipmentBlock (TYPE_DAMAGE) sobre la variante -- ver
    resulting_block.
    """

    rental_request = models.OneToOneField(
        RentalRequest,
        on_delete=models.CASCADE,
        related_name='return_inspection',
    )
    has_damage = models.BooleanField(default=False, db_index=True)
    condition_notes = models.TextField(blank=True, default='')
    missing_accessories = models.TextField(blank=True, default='')
    inspected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='equipment_return_inspections',
    )
    resulting_block = models.ForeignKey(
        'renting.EquipmentBlock', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='return_inspections',
    )

    class Meta:
        verbose_name = 'inspeccion de devolucion'
        verbose_name_plural = 'inspecciones de devolucion'
        ordering = ['-created_at']

    def __str__(self):
        return f"Inspeccion {self.rental_request.uuid} [{'con daño' if self.has_damage else 'ok'}]"

