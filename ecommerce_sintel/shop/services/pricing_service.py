from decimal import Decimal
from typing import Iterable
from django.utils import timezone
from shop.models import Tax, ProductVariant


class PricingService:
    """
    Servicio encargado de los cálculos financieros y de negocio para la aplicación Shop.
    Centraliza las reglas de valoración, descuentos e impuestos.
    """

    @staticmethod
    def calculate_tax_amount(base_price: Decimal, tax: Tax) -> Decimal:
        """Calcula el monto correspondiente a un impuesto particular sobre un precio base."""
        if tax.tax_type == Tax.TaxType.PERCENTAGE:
            return (base_price * tax.value) / Decimal('100.0')
        elif tax.tax_type == Tax.TaxType.FIXED:
            return tax.value
        return Decimal('0.0')

    @staticmethod
    def calculate_total_tax(base_price: Decimal, taxes: Iterable[Tax]) -> Decimal:
        """Suma el monto de aplicar múltiples impuestos a un precio base."""
        total_tax = Decimal('0.0')
        for tax in taxes:
            if tax.is_active:
                total_tax += PricingService.calculate_tax_amount(base_price, tax)
        return total_tax

    @staticmethod
    def calculate_final_price(
        base_price: Decimal, 
        discount: Decimal = Decimal('0.0'), 
        taxes: Iterable[Tax] = None
    ) -> Decimal:
        """
        Calcula el precio final aplicando primero los descuentos y luego sumando impuestos.
        """
        taxes = taxes or []
        price_after_discount = max(base_price - discount, Decimal('0.0'))
        
        # Opcionalmente si los impuestos se aplican sobre el precio CON descuento:
        total_taxes = PricingService.calculate_total_tax(price_after_discount, taxes)
        
        return price_after_discount + total_taxes

    @staticmethod
    def calculate_variant_price(variant: ProductVariant, include_active_taxes: bool = False, active_taxes=None) -> Decimal:
        """
        Calcula el precio operativo de una variante aplicando logica de descuento temporal.

        El discounted_price solo se aplica si la fecha actual esta dentro del rango
        [discount_start_date, discount_end_date]. Si alguno de los limites es null,
        ese extremo se considera abierto (sin restriccion).
        """
        use_discount = False
        if variant.discounted_price is not None:
            now = timezone.now()
            start_ok = variant.discount_start_date is None or now >= variant.discount_start_date
            end_ok = variant.discount_end_date is None or now <= variant.discount_end_date
            use_discount = start_ok and end_ok

        base = Decimal(str(variant.discounted_price if use_discount else variant.price))

        if include_active_taxes:
            if active_taxes is None:
                from shop.services.selectors import TaxSelector
                active_taxes = TaxSelector.list_active()
            return PricingService.calculate_final_price(base, discount=Decimal('0.0'), taxes=active_taxes)

        return base
