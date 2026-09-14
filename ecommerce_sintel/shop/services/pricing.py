from decimal import Decimal
from django.db import transaction
from shop.models import ProductCostRule, ProductCostAssignment


class ProductCostRuleSelector:
    @staticmethod
    def list_all_for_admin():
        return ProductCostRule.objects.filter(is_deleted=False).order_by('context', 'name')

    @staticmethod
    def list_active():
        return ProductCostRule.objects.filter(is_deleted=False, is_active=True)

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(ProductCostRule, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_rules_for_variant(variant):
        """Retorna reglas globales + reglas asignadas a esta variante especifica."""
        global_rules = ProductCostRule.objects.filter(
            is_deleted=False, is_active=True, applies_globally=True
        )
        variant_rule_ids = ProductCostAssignment.objects.filter(
            variant=variant, is_deleted=False
        ).values_list('rule_id', flat=True)
        variant_rules = ProductCostRule.objects.filter(
            id__in=variant_rule_ids, is_deleted=False, is_active=True
        )
        seen = set()
        rules = []
        for rule in list(global_rules) + list(variant_rules):
            if rule.pk not in seen:
                seen.add(rule.pk)
                rules.append(rule)
        return rules


class ProductCostRuleCommands:
    @staticmethod
    @transaction.atomic
    def create_rule(name, cost_type, context, value, description='', applies_globally=False, is_active=True):
        return ProductCostRule.objects.create(
            name=name,
            cost_type=cost_type,
            context=context,
            value=Decimal(str(value)),
            description=description,
            applies_globally=applies_globally,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_rule(rule, data):
        allowed = ('name', 'cost_type', 'context', 'value', 'description', 'applies_globally', 'is_active')
        for field in allowed:
            if field in data:
                val = data[field]
                if field == 'value':
                    val = Decimal(str(val))
                setattr(rule, field, val)
        rule.save()
        return rule

    @staticmethod
    @transaction.atomic
    def deactivate_rule(rule):
        rule.is_active = False
        rule.save(update_fields=['is_active'])
        return rule

    @staticmethod
    @transaction.atomic
    def delete_rule(rule):
        """Soft-delete una regla y todas sus asignaciones dejan de aplicar."""
        rule.is_active = False
        rule.is_deleted = True
        rule.save(update_fields=['is_active', 'is_deleted'])
        ProductCostAssignment.objects.filter(rule=rule, is_deleted=False).update(is_deleted=True)

    @staticmethod
    @transaction.atomic
    def assign_to_variant(rule, variant):
        obj, _ = ProductCostAssignment.objects.get_or_create(
            rule=rule, variant=variant, defaults={'is_deleted': False}
        )
        if obj.is_deleted:
            obj.is_deleted = False
            obj.save(update_fields=['is_deleted'])
        return obj

    @staticmethod
    @transaction.atomic
    def remove_from_variant(rule, variant):
        ProductCostAssignment.objects.filter(rule=rule, variant=variant).update(is_deleted=True)


class ShopPricingCalculator:
    """Motor de calculo de precios autonomo para la app shop."""

    @staticmethod
    def calculate_breakdown(variant, quantity=1):
        """
        Retorna un dict con el desglose completo de precio aplicando las
        reglas de costo configuradas para esta variante.

        Structure:
        {
            'base_price': Decimal,
            'base_subtotal': Decimal,
            'costs': [{'name', 'context', 'cost_type', 'value', 'amount', 'is_discount'}],
            'total_additions': Decimal,
            'total_discounts': Decimal,
            'final_price': Decimal,
        }
        """
        from shop.services.pricing_service import PricingService
        quantity = max(1, int(quantity))
        base_price = PricingService.calculate_variant_price(variant)
        base_subtotal = base_price * quantity

        rules = ProductCostRuleSelector.get_rules_for_variant(variant)

        cost_lines = []
        total_additions = Decimal('0')
        total_discounts = Decimal('0')

        for rule in rules:
            if rule.cost_type == ProductCostRule.TYPE_PERCENTAGE:
                amount = (base_subtotal * rule.value / Decimal('100')).quantize(Decimal('0.01'))
            else:
                amount = rule.value.quantize(Decimal('0.01'))

            is_discount = rule.context == ProductCostRule.CTX_DISCOUNT
            cost_lines.append({
                'name': rule.name,
                'context': rule.context,
                'cost_type': rule.cost_type,
                'value': rule.value,
                'amount': amount,
                'is_discount': is_discount,
            })
            if is_discount:
                total_discounts += amount
            else:
                total_additions += amount

        final_price = base_subtotal + total_additions - total_discounts
        if final_price < Decimal('0'):
            final_price = Decimal('0')

        return {
            'base_price': base_price,
            'base_subtotal': base_subtotal,
            'costs': cost_lines,
            'total_additions': total_additions,
            'total_discounts': total_discounts,
            'final_price': final_price,
        }

    @staticmethod
    def get_tax_rate(variant):
        """Retorna la tasa de impuesto activa (primera regla TAX global o de variante)."""
        rules = ProductCostRuleSelector.get_rules_for_variant(variant)
        for rule in rules:
            if rule.context == ProductCostRule.CTX_TAX and rule.cost_type == ProductCostRule.TYPE_PERCENTAGE:
                return rule.value / Decimal('100')
        return Decimal('0')
