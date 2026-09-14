# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.db import models
from shared.models import AbstractCostRule, AbstractCostAssignment

from .equipment import EquipmentVariant

class RentalCostRule(AbstractCostRule):
    """
    Regla de costo de un equipo especifico. NO existen reglas globales/heredadas
    -- cada regla solo aplica al Equipment donde el admin la creo, via su
    asignacion explicita a una EquipmentVariant de ESE equipo (RentalCostAssignment).
    Nunca se lee ni se comparte con ningun otro Equipment (ver renting/CLAUDE.md,
    regla "cada equipo es un universo independiente").
    """
    CTX_TAX = 'TAX'
    CTX_DISCOUNT = 'DISCOUNT'
    CTX_DEPOSIT = 'DEPOSIT'
    CTX_INSURANCE = 'INSURANCE'
    CTX_SURCHARGE = 'SURCHARGE'
    CONTEXT_CHOICES = [
        (CTX_TAX, 'Impuesto (IVA)'),
        (CTX_DISCOUNT, 'Descuento'),
        (CTX_DEPOSIT, 'Deposito de garantia'),
        (CTX_INSURANCE, 'Seguro del equipo'),
        (CTX_SURCHARGE, 'Recargo adicional'),
    ]

    context = models.CharField(max_length=20, choices=CONTEXT_CHOICES, db_index=True)

    class Meta:
        verbose_name = 'regla de costo de alquiler'
        verbose_name_plural = 'reglas de costo de alquiler'

class RentalCostAssignment(AbstractCostAssignment):
    rule = models.ForeignKey(
        RentalCostRule, on_delete=models.CASCADE, related_name='assignments'
    )
    variant = models.ForeignKey(
        'renting.EquipmentVariant', on_delete=models.CASCADE, related_name='cost_assignments'
    )

    class Meta:
        verbose_name = 'asignacion de regla de costo de alquiler'
        verbose_name_plural = 'asignaciones de reglas de costo de alquiler'
        unique_together = ('rule', 'variant')
