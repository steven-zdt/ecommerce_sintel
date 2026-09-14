"""
technical_services/services/quotation_resolver.py

Plan "Manual Pricing Engine" (2026-08-13) FASE 4. Unico punto que decide, para
una ServiceVariant dada, si la cotizacion sale del motor automatico
(LaborCostCalculator + ServicePricingCalculator, via ServiceSelector.
_get_automatic_quotation) o del motor manual (ManualPricingCalculator, FASE 3) --
segun `variant.pricing_source`. Ningun otro punto del codigo debe volver a hacer
este `if pricing_source == ...` -- ServiceSelector.get_variant_quotation() ya
delega aqui, y es el unico punto de entrada real usado por serializers.py,
services/commands.py (request_service), services/packages.py y api/views.py
(accion `quotation`).

Imports diferidos a proposito en ambas ramas: quotation_resolver.py <->
selectors.py se importan mutuamente de forma perezosa (dentro de metodos, no a
nivel de modulo) para evitar un ciclo de import en tiempo de carga de Django.
"""
from technical_services.models import ServiceVariant


class ServiceQuotationResolver:

    @staticmethod
    def resolve(variant: ServiceVariant, duration=None, discount_pct=None) -> dict:
        if variant.is_manual_pricing:
            from technical_services.services.manual_pricing import ManualPricingCalculator
            return ManualPricingCalculator.calculate(variant, duration=duration, discount_pct=discount_pct)

        from technical_services.services.selectors import ServiceSelector
        return ServiceSelector._get_automatic_quotation(variant, duration=duration, discount_pct=discount_pct)
