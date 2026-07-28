"""
technical_services/services/packages.py

Dominio de Paquetes de Servicio (2026-07-16): capa comercial aditiva sobre
TechnicalService. Un servicio puede tener 0 o mas ServicePackage (ej. "8
camaras", "16 camaras"), cada uno con items incluidos y costos adicionales
opcionales. Este modulo NO toca LaborCostCalculator/ServiceCommands.request_service
mas alla de los parametros opcionales que este ultimo ya expone -- ver
ServiceCommands.request_service en commands.py.

Sigue el mismo patron ya usado en renting/services/catalog.py: helpers de
modulo (_reorder/_toggle_active/_soft_delete/_duplicate) para no repetir la
misma logica de posicion/activo/borrado en cada uno de los 3 modelos hijos.
"""
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet, Prefetch

from technical_services.models import (
    TechnicalService, ServicePackage, PackageIncludedItem, PackageAdditionalCost,
    ServiceRequestPackage, ServiceRequestAdditionalCost,
)


def _reorder(model, ordered_uuids: list, **scope) -> None:
    items = {
        str(item.uuid): item
        for item in model.objects.filter(is_deleted=False, **scope)
    }
    with transaction.atomic():
        for position, item_uuid in enumerate(ordered_uuids):
            item = items.get(str(item_uuid))
            if item is not None and item.position != position:
                item.position = position
                item.save(update_fields=['position', 'updated_at'])


@transaction.atomic
def _toggle_active(instance):
    instance.is_active = not instance.is_active
    instance.save(update_fields=['is_active', 'updated_at'])
    return instance


@transaction.atomic
def _soft_delete(instance) -> None:
    instance.is_deleted = True
    instance.save(update_fields=['is_deleted', 'updated_at'])


@transaction.atomic
def _duplicate(instance, copy_fields: list, overrides: dict = None):
    data = {field: getattr(instance, field) for field in copy_fields}
    data.update(overrides or {})
    return type(instance).objects.create(**data)


# ── ServicePackage ─────────────────────────────────────────────────────────────

class ServicePackageSelector:
    @staticmethod
    def list_for_service(service_uuid: str, active_only: bool = False) -> QuerySet:
        qs = (
            ServicePackage.objects
            .filter(service__uuid=service_uuid, is_deleted=False)
            .prefetch_related(
                Prefetch('included_items', queryset=PackageIncludedItem.objects.filter(is_deleted=False)),
                Prefetch('additional_costs', queryset=PackageAdditionalCost.objects.filter(is_deleted=False)),
            )
        )
        if active_only:
            qs = qs.filter(is_active=True)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> ServicePackage:
        return get_object_or_404(ServicePackage, uuid=uuid, is_deleted=False)


class ServicePackageCommands:
    _COPY_FIELDS = [
        'service_id', 'name', 'description', 'package_type', 'icon',
        'is_default', 'is_featured', 'is_active', 'position',
        'estimated_duration', 'base_price', 'notes',
    ]

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServicePackage:
        if fields.get('is_default'):
            ServicePackage.objects.filter(service=service, is_deleted=False, is_default=True).update(is_default=False)
        return ServicePackage.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServicePackage, **fields) -> ServicePackage:
        allowed = (
            'name', 'description', 'package_type', 'image', 'icon', 'is_default',
            'is_featured', 'is_active', 'position', 'estimated_duration', 'base_price', 'notes',
        )
        if fields.get('is_default') and not instance.is_default:
            ServicePackage.objects.filter(service=instance.service, is_deleted=False, is_default=True).update(is_default=False)
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServicePackage) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServicePackage) -> ServicePackage:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServicePackage) -> ServicePackage:
        return _duplicate(
            instance, ServicePackageCommands._COPY_FIELDS,
            {'name': f'{instance.name} (copia)', 'slug': '', 'is_default': False},
        )

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServicePackage, ordered_uuids, service_id=service_id)


# ── PackageIncludedItem ────────────────────────────────────────────────────────

class PackageIncludedItemSelector:
    @staticmethod
    def list_for_package(package_uuid: str) -> QuerySet:
        return PackageIncludedItem.objects.filter(package__uuid=package_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> PackageIncludedItem:
        return get_object_or_404(PackageIncludedItem, uuid=uuid, is_deleted=False)


class PackageIncludedItemCommands:
    _COPY_FIELDS = ['package_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(package: ServicePackage, **fields) -> PackageIncludedItem:
        return PackageIncludedItem.objects.create(package=package, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: PackageIncludedItem, **fields) -> PackageIncludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: PackageIncludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: PackageIncludedItem) -> PackageIncludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: PackageIncludedItem) -> PackageIncludedItem:
        return _duplicate(instance, PackageIncludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(package_id: int, ordered_uuids: list) -> None:
        _reorder(PackageIncludedItem, ordered_uuids, package_id=package_id)


# ── PackageAdditionalCost ──────────────────────────────────────────────────────

class PackageAdditionalCostSelector:
    @staticmethod
    def list_for_package(package_uuid: str) -> QuerySet:
        return PackageAdditionalCost.objects.filter(package__uuid=package_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> PackageAdditionalCost:
        return get_object_or_404(PackageAdditionalCost, uuid=uuid, is_deleted=False)


class PackageAdditionalCostCommands:
    _COPY_FIELDS = [
        'package_id', 'name', 'description', 'cost_type', 'price', 'unit',
        'is_required', 'is_default', 'position', 'is_active',
    ]

    @staticmethod
    @transaction.atomic
    def create(package: ServicePackage, **fields) -> PackageAdditionalCost:
        return PackageAdditionalCost.objects.create(package=package, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: PackageAdditionalCost, **fields) -> PackageAdditionalCost:
        allowed = (
            'name', 'description', 'cost_type', 'price', 'unit',
            'is_required', 'is_default', 'position', 'is_active',
        )
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: PackageAdditionalCost) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: PackageAdditionalCost) -> PackageAdditionalCost:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: PackageAdditionalCost) -> PackageAdditionalCost:
        return _duplicate(instance, PackageAdditionalCostCommands._COPY_FIELDS, {'name': f'{instance.name} (copia)'})

    @staticmethod
    def reorder(package_id: int, ordered_uuids: list) -> None:
        _reorder(PackageAdditionalCost, ordered_uuids, package_id=package_id)


# ── PackagePriceCalculator ─────────────────────────────────────────────────────

class PackagePriceCalculator:
    """
    Calcula el total de una solicitud con paquete: precio del paquete + costos
    adicionales seleccionados (+ opcionalmente el costo base de un ServiceVariant,
    via `extra_base`) -> subtotal -> descuento -> IVA -> total. Independiente de
    LaborCostCalculator (que sigue calculando exclusivamente la mano de obra de
    un ServiceVariant HOURLY/DAILY/FIXED) -- ServiceCommands combina ambos
    resultados, nunca se modifica la formula de LaborCostCalculator.
    """

    @staticmethod
    def calculate(
        package: ServicePackage,
        additional_cost_selections: list = None,
        extra_base: Decimal = Decimal('0'),
        discount_pct=None,
    ) -> dict:
        from technical_services.services.selectors import ServiceConfigurationSelector

        additional_cost_selections = additional_cost_selections or []
        cost_lines = []
        additional_total = Decimal('0.00')

        for selection in additional_cost_selections:
            cost: PackageAdditionalCost = selection['additional_cost']
            quantity = max(1, int(selection.get('quantity', 1)))
            line_total = (Decimal(str(cost.price)) * quantity).quantize(Decimal('0.01'))
            additional_total += line_total
            cost_lines.append({
                'additional_cost': cost,
                'name': cost.name,
                'cost_type': cost.cost_type,
                'unit': cost.unit,
                'unit_price': Decimal(str(cost.price)).quantize(Decimal('0.01')),
                'quantity': quantity,
                'subtotal': line_total,
            })

        package_price = Decimal(str(package.base_price)).quantize(Decimal('0.01'))
        extra_base = Decimal(str(extra_base)).quantize(Decimal('0.01'))
        subtotal = package_price + extra_base + additional_total

        config = ServiceConfigurationSelector.get_active()
        iva_rate = Decimal(str(getattr(config, 'iva_rate', Decimal('19.00'))))

        # R-01 (auditoria enterprise): acotado 0..100 igual que
        # ServiceSelector.get_variant_quotation(). Este calculador lo alimenta
        # el endpoint publico quote-package (AllowAny) via request.data.get(
        # 'discount_pct') sin pasar por ningun serializer -- sin este clamp,
        # un valor > 100 producia total negativo.
        if discount_pct is not None:
            discount_pct_val = max(Decimal('0'), min(Decimal('100'), Decimal(str(discount_pct))))
        else:
            discount_pct_val = Decimal('0.00')
        discount_amount = (subtotal * discount_pct_val / Decimal('100.00')).quantize(Decimal('0.01'))
        taxable_base = subtotal - discount_amount
        iva_amount = (taxable_base * iva_rate / Decimal('100.00')).quantize(Decimal('0.01'))
        total = taxable_base + iva_amount

        return {
            'package_price': package_price,
            'service_base': extra_base,
            'additional_costs': cost_lines,
            'additional_costs_total': additional_total.quantize(Decimal('0.01')),
            'subtotal': subtotal.quantize(Decimal('0.01')),
            'discount_pct': discount_pct_val,
            'discount_amount': discount_amount,
            'iva_rate': iva_rate,
            'iva_amount': iva_amount,
            'total': total.quantize(Decimal('0.01')),
        }


class ServiceRequestPackageCommands:
    """Crea el snapshot de paquete + costos adicionales elegidos en una orden."""

    @staticmethod
    @transaction.atomic
    def create_snapshot(order, package: ServicePackage, price_breakdown: dict) -> ServiceRequestPackage:
        request_package = ServiceRequestPackage.objects.create(
            order=order,
            package=package,
            package_name_snapshot=package.name,
            package_price_snapshot=price_breakdown['package_price'],
        )
        for line in price_breakdown['additional_costs']:
            ServiceRequestAdditionalCost.objects.create(
                request_package=request_package,
                additional_cost=line['additional_cost'],
                name_snapshot=line['name'],
                unit_price_snapshot=line['unit_price'],
                quantity=line['quantity'],
                subtotal_snapshot=line['subtotal'],
            )
        return request_package
