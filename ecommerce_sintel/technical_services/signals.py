from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from technical_services.models import ServiceConfiguration
from technical_services.services.calculator import LaborCostCalculator


@receiver([post_save, post_delete], sender=ServiceConfiguration)
def invalidate_labor_cost_config_cache(sender, **kwargs):
    """
    LaborCostCalculator.get_active_config() cachea la configuracion SMLV activa
    (ver calculator.py). Cualquier escritura sobre ServiceConfiguration -- via
    ServiceConfigurationCommands o directamente desde Django Admin -- debe invalidar
    ese cache, sin importar el camino de escritura.
    """
    LaborCostCalculator.invalidate_config_cache()
