"""
technical_services/services/manual_pricing.py

Plan "Manual Pricing Engine" (2026-08-13) FASE 3. Motor de calculo para
ServiceVariant.pricing_source != AUTOMATIC -- deliberadamente separado de
LaborCostCalculator (services/calculator.py, SMLV/formula colombiana) por
instruccion explicita del usuario: "no mezclar manual dentro de
LaborCostCalculator".

Contrato de salida: el MISMO shape top-level que ServiceSelector.
get_variant_quotation() (services/selectors.py) -- labor_cost, material_cost,
base_amount, discount_pct, discount_amount, iva_rate, iva_amount, total_price,
breakdown{...}. No es el shape reducido del ejemplo original del plan
(pricing_source/base_amount/hours/unit_price/iva_rate/iva_amount/total_price) --
se amplio a proposito para que el mismo contrato sirva para AUTOMATIC y MANUAL_*
sin que el consumidor (CostCalculationPanel.vue, ServiceVariantSerializer, FASE
12 del plan) tenga que distinguir el modo. Confirma la propia regla del plan en
FASE 12: "el endpoint debe devolver exactamente el mismo contrato
independientemente del modo".

Decisiones explicitas de esta primera version (FASE 5 del plan):
- Los materiales (ServiceMaterial) NO se suman sobre un precio manual -- el
  precio que define el administrador ya es el precio final base, se asume que
  ya considero materiales/logistica al definirlo. material_cost siempre 0.00
  para MANUAL_*. Si en el futuro se necesita sumar materiales sobre un precio
  manual, es una decision de negocio nueva, no un default silencioso.
- ServiceCostRule (services/pricing.py) NO se aplica sobre un precio manual --
  reservado para AUTOMATIC (regla explicita del plan, FASE 5). 'breakdown.
  cost_rules' siempre [] aqui.
- 'labor_cost' en el dict de salida representa el precio manual base (proyecto/
  general/tarifa x horas), reutilizando la misma clave que ya usa
  get_variant_quotation() para FIXED (labor_cost = variant.fixed_price, sin
  ningun calculo SMLV) -- mismo patron ya existente en el codebase, no una
  convencion nueva.
"""
from decimal import Decimal

from technical_services.models import ServiceVariant
from technical_services.services.selectors import ServiceConfigurationSelector


class ManualPricingCalculator:

    @staticmethod
    def _clamp_discount(discount_pct) -> Decimal:
        if discount_pct is None:
            return Decimal('0.00')
        return max(Decimal('0'), min(Decimal('100'), Decimal(str(discount_pct))))

    @staticmethod
    def _finalize(variant: ServiceVariant, base_amount: Decimal, discount_pct, breakdown_extra: dict) -> dict:
        base_amount = base_amount.quantize(Decimal('0.01'))
        discount_pct_val = ManualPricingCalculator._clamp_discount(discount_pct)
        discount_amount = (base_amount * (discount_pct_val / Decimal('100.00'))).quantize(Decimal('0.01'))
        taxable_base = base_amount - discount_amount

        config = ServiceConfigurationSelector.get_active()
        iva_rate = Decimal(str(getattr(config, 'iva_rate', Decimal('19.00'))))
        iva_amount = (taxable_base * (iva_rate / Decimal('100.00'))).quantize(Decimal('0.01'))
        total_price = taxable_base + iva_amount

        return {
            'variant_id': variant.id,
            'sku': variant.sku,
            'service_name': variant.service.name,
            'pricing_strategy': variant.pricing_source,
            'pricing_source': variant.pricing_source,
            'labor_cost': base_amount,
            'material_cost': Decimal('0.00'),
            'base_amount': base_amount,
            'discount_pct': discount_pct_val.quantize(Decimal('0.01')),
            'discount_amount': discount_amount,
            'iva_rate': iva_rate.quantize(Decimal('0.01')),
            'iva_amount': iva_amount,
            'total_price': total_price.quantize(Decimal('0.01')),
            'breakdown': {
                'materials': [],
                'cost_rules': [],
                'total_additions': 0.0,
                'total_discounts_rules': 0.0,
                'subtotal_after_rules': float(base_amount),
                'base_amount': float(base_amount),
                'discount_pct': float(discount_pct_val),
                **breakdown_extra,
            },
        }

    @staticmethod
    def calculate_project_price(variant: ServiceVariant, discount_pct=None) -> dict:
        if not variant.manual_project_price or variant.manual_project_price <= Decimal('0'):
            raise ValueError(f"Variante '{variant.sku}' MANUAL_PROJECT sin manual_project_price valido.")
        return ManualPricingCalculator._finalize(
            variant, variant.manual_project_price, discount_pct,
            breakdown_extra={
                'labor_calculation': 'Precio de proyecto (manual)',
                'project_price': float(variant.manual_project_price),
                'hours': None, 'duration': None,
            },
        )

    @staticmethod
    def calculate_general_price(variant: ServiceVariant, discount_pct=None) -> dict:
        if not variant.manual_unit_price or variant.manual_unit_price <= Decimal('0'):
            raise ValueError(f"Variante '{variant.sku}' MANUAL_GENERAL sin manual_unit_price valido.")
        return ManualPricingCalculator._finalize(
            variant, variant.manual_unit_price, discount_pct,
            breakdown_extra={
                'labor_calculation': 'Precio general (manual)',
                'unit_price': float(variant.manual_unit_price),
                'hours': None, 'duration': None,
            },
        )

    @staticmethod
    def calculate_hourly_price(variant: ServiceVariant, duration=None, discount_pct=None) -> dict:
        if not variant.manual_unit_price or variant.manual_unit_price <= Decimal('0'):
            raise ValueError(f"Variante '{variant.sku}' MANUAL_HOURLY sin manual_unit_price valido.")

        duration_val = Decimal(str(duration)) if duration is not None else Decimal(str(variant.estimated_hours))
        if variant.min_duration is not None and duration_val < variant.min_duration:
            duration_val = variant.min_duration
        if variant.max_duration is not None and duration_val > variant.max_duration:
            duration_val = variant.max_duration

        base_amount = variant.manual_unit_price * duration_val
        return ManualPricingCalculator._finalize(
            variant, base_amount, discount_pct,
            breakdown_extra={
                'labor_calculation': f"{variant.manual_unit_price} x {duration_val}",
                'unit_price': float(variant.manual_unit_price),
                'hours': float(duration_val), 'duration': float(duration_val),
                'min_duration': float(variant.min_duration) if variant.min_duration is not None else None,
                'max_duration': float(variant.max_duration) if variant.max_duration is not None else None,
            },
        )

    @staticmethod
    def calculate(variant: ServiceVariant, duration=None, discount_pct=None) -> dict:
        if variant.pricing_source == ServiceVariant.SOURCE_MANUAL_PROJECT:
            return ManualPricingCalculator.calculate_project_price(variant, discount_pct)
        if variant.pricing_source == ServiceVariant.SOURCE_MANUAL_GENERAL:
            return ManualPricingCalculator.calculate_general_price(variant, discount_pct)
        if variant.pricing_source == ServiceVariant.SOURCE_MANUAL_HOURLY:
            return ManualPricingCalculator.calculate_hourly_price(variant, duration, discount_pct)
        raise ValueError(
            f"ManualPricingCalculator.calculate() llamado con pricing_source="
            f"'{variant.pricing_source}' -- no es un modo manual. Usar "
            f"LaborCostCalculator/ServiceSelector.get_variant_quotation() para AUTOMATIC."
        )
