from decimal import Decimal
from django.db import transaction
from renting.models import RentalCostRule, RentalCostAssignment


class RentalCostRuleSelector:
    @staticmethod
    def list_for_equipment(equipment):
        """
        Unica forma valida de listar reglas de costo: solo las asignadas a una
        variante de ESTE equipo especifico. Nunca reglas de otro Equipment, y
        nunca un catalogo "global" -- ver docstring de RentalCostRule.
        """
        rule_ids = RentalCostAssignment.objects.filter(
            variant__equipment=equipment, is_deleted=False
        ).values_list('rule_id', flat=True)
        return RentalCostRule.objects.filter(
            id__in=rule_ids, is_deleted=False
        ).order_by('context', 'name')

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(RentalCostRule, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_rules_for_variant(variant):
        """Reglas asignadas explicitamente a esta variante -- nada mas."""
        rule_ids = RentalCostAssignment.objects.filter(
            variant=variant, is_deleted=False
        ).values_list('rule_id', flat=True)
        return list(RentalCostRule.objects.filter(
            id__in=rule_ids, is_deleted=False, is_active=True
        ))


class RentalCostRuleCommands:
    @staticmethod
    @transaction.atomic
    def create_rule(name, cost_type, context, value, description='', is_active=True):
        return RentalCostRule.objects.create(
            name=name,
            cost_type=cost_type,
            context=context,
            value=Decimal(str(value)),
            description=description,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def create_rule_for_equipment(equipment, name, cost_type, context, value, description='', is_active=True):
        """
        Unico punto de creacion usado por el panel: crea la regla Y la asigna de
        inmediato a la variante principal (la primera) de este equipo, para que
        nazca ya perteneciendo exclusivamente a el -- sin paso manual de
        "asignar" ni ventana donde la regla exista "suelta" y sin dueno.
        """
        rule = RentalCostRuleCommands.create_rule(
            name=name, cost_type=cost_type, context=context, value=value,
            description=description, is_active=is_active,
        )
        variant = equipment.variants.filter(is_deleted=False).order_by('id').first()
        if variant is not None:
            RentalCostRuleCommands.assign_to_variant(rule, variant)
        return rule

    @staticmethod
    @transaction.atomic
    def update_rule(rule, data):
        allowed = ('name', 'cost_type', 'context', 'value', 'description', 'is_active')
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
    def delete_rule(rule) -> None:
        """
        Soft-delete (is_deleted=True), mismo patron que el resto del catalogo
        de renting (ver renting/services/catalog.py:_soft_delete). No hace
        falta limpiar sus RentalCostAssignment: get_rules_for_variant() ya
        filtra is_deleted=False del lado de la regla, asi que quedan huerfanas
        pero inertes -- igual que al desactivar.
        """
        rule.is_deleted = True
        rule.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def assign_to_variant(rule, variant):
        obj, _ = RentalCostAssignment.objects.get_or_create(
            rule=rule, variant=variant, defaults={'is_deleted': False}
        )
        if obj.is_deleted:
            obj.is_deleted = False
            obj.save(update_fields=['is_deleted'])
        return obj

    @staticmethod
    @transaction.atomic
    def remove_from_variant(rule, variant):
        RentalCostAssignment.objects.filter(rule=rule, variant=variant).update(is_deleted=True)


class RentalPricingCalculator:
    """Motor de calculo de precios autonomo para la app renting.

    La tasa de IVA se lee de las RentalCostRule asignadas a ESTA variante
    (RentalCostAssignment) -- nunca de otra variante ni de un catalogo global.
    Si esta variante no tiene ninguna regla TAX propia, se cae al fallback del
    19% (constante de codigo, no un dato tomado de otro equipo).
    """
    FALLBACK_TAX_RATE = Decimal('0.19')

    @staticmethod
    def get_tax_rate(variant):
        """Retorna la tasa de IVA aplicable como Decimal (ej. 0.19 para 19%).

        Busca una regla TAX asignada a esta variante. Fallback: 19% si la
        variante no tiene ninguna regla TAX propia configurada.
        """
        rules = RentalCostRuleSelector.get_rules_for_variant(variant)
        for rule in rules:
            if rule.context == RentalCostRule.CTX_TAX and rule.cost_type == RentalCostRule.TYPE_PERCENTAGE:
                return rule.value / Decimal('100')
        return RentalPricingCalculator.FALLBACK_TAX_RATE

    @staticmethod
    def calculate_breakdown(variant, subtotal):
        """
        Aplica las reglas de costo de alquiler sobre el subtotal ya calculado
        (base_cost + labor + transport + setup).

        Retorna:
        {
            'subtotal': Decimal,
            'costs': [{'name', 'context', 'cost_type', 'value', 'amount', 'is_discount'}],
            'total_additions': Decimal,
            'total_discounts': Decimal,
            'grand_total': Decimal,
        }
        """
        subtotal = Decimal(str(subtotal))
        rules = RentalCostRuleSelector.get_rules_for_variant(variant)

        cost_lines = []
        total_additions = Decimal('0')
        total_discounts = Decimal('0')

        for rule in rules:
            if rule.cost_type == RentalCostRule.TYPE_PERCENTAGE:
                amount = (subtotal * rule.value / Decimal('100')).quantize(Decimal('0.01'))
            else:
                amount = rule.value.quantize(Decimal('0.01'))

            is_discount = rule.context == RentalCostRule.CTX_DISCOUNT
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

        grand_total = subtotal + total_additions - total_discounts
        if grand_total < Decimal('0'):
            grand_total = Decimal('0')

        return {
            'subtotal': subtotal,
            'costs': cost_lines,
            'total_additions': total_additions,
            'total_discounts': total_discounts,
            'grand_total': grand_total,
        }
