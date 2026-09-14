# Extracted from the former renting.models module. Public imports remain in __init__.py.

from django.db import models
from ecommerce.base_models import SintelBaseModel

from .equipment import Equipment
from .requests import RentalRequest

class EquipmentCommercialConfig(SintelBaseModel):
    """
    Que modalidades comerciales (Renting/Comodato) admite este Equipment.
    Mismo patron que EquipmentLogisticsConfig/EquipmentMarketing: OneToOne
    por Equipment, upsert via Commands.upsert(), sin tocar Equipment/
    EquipmentVariant. Default renting_enabled=True/comodato_enabled=False
    reproduce el comportamiento de "solo Renting" que ya tenia todo equipo
    existente antes de esta config existir.
    """
    equipment = models.OneToOneField(
        Equipment,
        on_delete=models.CASCADE,
        related_name='commercial_config'
    )
    renting_enabled = models.BooleanField(default=True, verbose_name='renting habilitado')
    comodato_enabled = models.BooleanField(default=False, verbose_name='comodato habilitado')
    comodato_notes = models.TextField(blank=True, default='', verbose_name='notas de comodato')

    class Meta:
        verbose_name = 'configuracion comercial'
        verbose_name_plural = 'configuraciones comerciales'

    def __str__(self):
        return f"Config comercial -- {self.equipment.name}"

class EquipmentCommercialOption(SintelBaseModel):
    """
    Plazos configurables por Equipment para una modalidad comercial (hoy solo
    Comodato los usa; el campo modality queda generico por si Renting algun
    dia tambien quiere ofrecer plazos fijos). Es catalogo de configuracion,
    no un registro de reserva -- no duplica RentalRequest/RentalPeriod.
    """
    TERM_6 = 6
    TERM_12 = 12
    TERM_18 = 18
    TERM_24 = 24
    TERM_36 = 36
    TERM_MONTHS_CHOICES = [
        (TERM_6, '6 meses'),
        (TERM_12, '12 meses'),
        (TERM_18, '18 meses'),
        (TERM_24, '24 meses'),
        (TERM_36, '36 meses'),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name='commercial_options'
    )
    modality = models.CharField(
        max_length=10, choices=RentalRequest.COMMERCIAL_TYPE_CHOICES,
        default=RentalRequest.COMMERCIAL_COMODATO,
    )
    term_months = models.PositiveSmallIntegerField(choices=TERM_MONTHS_CHOICES)
    is_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'opcion comercial'
        verbose_name_plural = 'opciones comerciales'
        constraints = [
            models.UniqueConstraint(
                fields=['equipment', 'modality', 'term_months'],
                name='renting_commercialoption_unique_term',
            ),
        ]
        ordering = ['modality', 'term_months']

    def __str__(self):
        return f"{self.equipment.name} -- {self.get_modality_display()} {self.term_months}m"

