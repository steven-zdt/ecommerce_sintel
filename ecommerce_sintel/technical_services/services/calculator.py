from decimal import Decimal
from django.core.cache import cache
from ..models import ServiceConfiguration

class LaborCostCalculator:
    """Calculates Colombian labor costs based on SMLV."""

    # get_active_config() se llama una vez POR VARIANTE al serializar listados (ver
    # get_variant_quotation/calculate_variant_labor_cost) aunque el valor es el mismo
    # para toda la peticion -- sin cache, listar servicios generaba una query redundante
    # por variante (medido 2026-07-03: 26 queries para listar 2 servicios con 1 variante
    # cada uno, solo por esto). TTL corto (igual criterio que el cache de home-feed en
    # core/ y el de balance de stock en inventory/) porque el SMLV cambia con muy poca
    # frecuencia (una vez al año).
    CACHE_KEY = 'technical_services:active_service_configuration'
    CACHE_TTL = 300

    @staticmethod
    def get_active_config():
        config = cache.get(LaborCostCalculator.CACHE_KEY)
        if config is not None:
            return config
        try:
            config = ServiceConfiguration.objects.filter(is_active=True).latest('created_at')
        except ServiceConfiguration.DoesNotExist:
            # Fallback to default values if no config in DB
            config = ServiceConfiguration(
                smlv=Decimal('1300000.00'),
                transport_subsidy=Decimal('162000.00'),
                benefit_rate=Decimal('53.10'),
                indirect_costs_rate=Decimal('15.00')
            )
        cache.set(LaborCostCalculator.CACHE_KEY, config, LaborCostCalculator.CACHE_TTL)
        return config

    @staticmethod
    def invalidate_config_cache():
        cache.delete(LaborCostCalculator.CACHE_KEY)

    @staticmethod
    def calculate_hourly_rate(config=None):
        if not config:
            config = LaborCostCalculator.get_active_config()
        
        # Formula: ((SMLV * (1 + Benefits%)) + Transport) / 240 hours
        benefits_multiplier = 1 + (config.benefit_rate / 100)
        total_monthly_cost = (config.smlv * benefits_multiplier) + config.transport_subsidy
        
        # 240 hours is the standard legal divisor in Colombia for full-time monthly salary
        base_hourly_rate = total_monthly_cost / Decimal('240.00')
        
        # Add indirect costs (Overhead)
        overhead_multiplier = 1 + (config.indirect_costs_rate / 100)
        return base_hourly_rate * overhead_multiplier

    @classmethod
    def calculate_variant_labor_cost(cls, variant, duration=None):
        """
        Calcula el costo laboral según la estrategia de precio de la variante.

        Estrategias soportadas:
        - FIXED:  Retorna el precio fijo configurado en la variante.
        - DAILY:  Tarifa diaria (hourly_rate * 8) * duración * complejidad.
        - HOURLY: Tarifa horaria * duración * complejidad.
        """
        if variant.pricing_strategy == 'FIXED':
            return variant.fixed_price or Decimal('0.00')

        hour_rate = cls.calculate_hourly_rate()

        if duration is not None:
            duration_val = Decimal(str(duration))
        else:
            duration_val = Decimal(str(variant.estimated_hours))

        if variant.min_duration is not None and duration_val < Decimal(str(variant.min_duration)):
            duration_val = Decimal(str(variant.min_duration))
        if variant.max_duration is not None and duration_val > Decimal(str(variant.max_duration)):
            duration_val = Decimal(str(variant.max_duration))

        complexity = Decimal(str(variant.complexity_factor))
        if variant.pricing_strategy == 'DAILY':
            daily_rate = hour_rate * Decimal('8.00')
            return daily_rate * duration_val * complexity
        # Default: HOURLY
        return hour_rate * duration_val * complexity

