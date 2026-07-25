from decimal import Decimal
from datetime import datetime
from django.db.models import QuerySet, Count, Sum, Value, IntegerField, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from technical_services.models import (
    TechnicalService, ServiceVariant, ServiceCategory,
    ServiceLevel, ServiceConfiguration, ServiceMaterial,
    ServicePriceHistory, WorkingSchedule, WorkingException, ServiceFAQ,
)
from .calculator import LaborCostCalculator


class ServiceCategorySelector:
    @staticmethod
    def list_all() -> QuerySet:
        return ServiceCategory.objects.filter(is_active=True).order_by('name')

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return ServiceCategory.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def get_by_uuid(category_uuid: str) -> ServiceCategory:
        return get_object_or_404(ServiceCategory, uuid=category_uuid)


class ServiceLevelSelector:
    @staticmethod
    def list_all() -> QuerySet:
        return ServiceLevel.objects.all().order_by('name')

    @staticmethod
    def get_by_uuid(level_uuid: str) -> ServiceLevel:
        return get_object_or_404(ServiceLevel, uuid=level_uuid)


class ServiceVariantSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return (
            ServiceVariant.objects
            .filter(service__uuid=service_uuid, is_deleted=False)
            .prefetch_related('materials__product_variant__product')
            .order_by('-is_default', 'created_at')
        )

    @staticmethod
    def get_by_uuid(variant_uuid: str) -> ServiceVariant:
        return get_object_or_404(ServiceVariant, uuid=variant_uuid, is_deleted=False)

    @staticmethod
    def get_price_history(variant: ServiceVariant) -> QuerySet:
        return (
            ServicePriceHistory.objects
            .filter(variant=variant, is_deleted=False)
            .select_related('changed_by')
            .order_by('-created_at')
        )


class ServiceMaterialSelector:
    @staticmethod
    def list_for_variant(variant_uuid: str) -> QuerySet:
        return (
            ServiceMaterial.objects
            .filter(variant__uuid=variant_uuid)
            .select_related('product_variant__product')
        )

    @staticmethod
    def get_by_uuid(material_uuid: str) -> ServiceMaterial:
        return get_object_or_404(ServiceMaterial, uuid=material_uuid)


class ServiceConfigurationSelector:
    @staticmethod
    def get_active() -> ServiceConfiguration:
        try:
            return ServiceConfiguration.objects.filter(is_active=True).latest('created_at')
        except ServiceConfiguration.DoesNotExist:
            return ServiceConfiguration(
                smlv=Decimal('1300000.00'),
                transport_subsidy=Decimal('162000.00'),
                benefit_rate=Decimal('53.10'),
                indirect_costs_rate=Decimal('15.00'),
                iva_rate=Decimal('19.00'),
            )

    @staticmethod
    def list_all() -> QuerySet:
        return ServiceConfiguration.objects.order_by('-is_active', '-created_at')

    @staticmethod
    def get_by_uuid(config_uuid: str) -> ServiceConfiguration:
        return get_object_or_404(ServiceConfiguration, uuid=config_uuid)


class ServiceSelector:
    LIST_FIELDS = ('id', 'uuid', 'name', 'slug', 'description', 'is_active', 'is_featured')

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return (
            TechnicalService.objects
            .filter(is_deleted=False)
            .select_related('category', 'level', 'marketing')
            .prefetch_related(
                'variants__materials__product_variant__product', 'images',
                Prefetch('faqs', queryset=ServiceFAQ.objects.filter(is_deleted=False)),
            )
            .order_by('name')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> TechnicalService:
        return (
            TechnicalService.objects
            .prefetch_related(
                'variants__materials__product_variant__product', 'images',
                Prefetch('faqs', queryset=ServiceFAQ.objects.filter(is_deleted=False)),
            )
            .select_related('category', 'level', 'marketing')
            .get(uuid=uuid, is_deleted=False)
        )

    @staticmethod
    def list_active_services() -> QuerySet:
        return (
            TechnicalService.objects
            .filter(is_active=True, is_deleted=False)
            .select_related('category', 'level', 'marketing')
            .prefetch_related(
                'variants__materials__product_variant__product', 'images',
                Prefetch('faqs', queryset=ServiceFAQ.objects.filter(is_deleted=False)),
            )
            .order_by('-is_featured', 'name')
        )

    @staticmethod
    def list_featured() -> QuerySet:
        """Servicios activos marcados como destacados para la Home publica, ordenados por unidades vendidas."""
        return (
            TechnicalService.objects
            .filter(is_active=True, is_featured=True, is_deleted=False)
            .select_related('category', 'level')
            .prefetch_related('variants', 'images')
            .annotate(
                total_sold=Coalesce(
                    Sum('variants__orderitem__quantity'),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('-total_sold', '-created_at')
        )

    @classmethod
    def get_variant_quotation(cls, variant: ServiceVariant, duration=None, discount_pct=None):
        if variant.pricing_strategy == 'FIXED' and variant.fixed_price is not None:
            labor_cost = variant.fixed_price
        else:
            labor_cost = LaborCostCalculator.calculate_variant_labor_cost(
                variant, duration
            )
        base_hourly_rate = LaborCostCalculator.calculate_hourly_rate()

        if duration is not None:
            duration_val = Decimal(str(duration))
        else:
            duration_val = variant.estimated_hours

        if variant.min_duration is not None and duration_val < variant.min_duration:
            duration_val = variant.min_duration
        if variant.max_duration is not None and duration_val > variant.max_duration:
            duration_val = variant.max_duration

        if variant.pricing_strategy == 'DAILY':
            labor_calculation = f"{base_hourly_rate.quantize(Decimal('0.01'))} x 8 x {duration_val} x {variant.complexity_factor}"
        elif variant.pricing_strategy == 'FIXED':
            labor_calculation = "Precio fijo"
        else:
            labor_calculation = f"{base_hourly_rate.quantize(Decimal('0.01'))} x {duration_val} x {variant.complexity_factor}"

        material_cost = Decimal('0.00')
        materials_breakdown = []

        for m in variant.materials.select_related('product_variant__product').all():
            m_price = m.product_variant.discounted_price or m.product_variant.price
            m_subtotal = m_price * m.quantity
            material_cost += m_subtotal
            materials_breakdown.append({
                'name': f"{m.product_variant.product.name} ({m.product_variant.sku})",
                'qty': float(m.quantity),
                'price': float(m_price),
                'subtotal': float(m_subtotal)
            })

        base_amount = labor_cost + material_cost

        # Apply cost rules from ServicePricingCalculator
        from technical_services.services.pricing import ServicePricingCalculator
        pricing_breakdown = ServicePricingCalculator.calculate_breakdown(variant, base_amount)
        subtotal_after_rules = pricing_breakdown['final_price']

        # Get active configuration for IVA
        config = ServiceConfigurationSelector.get_active()
        iva_rate = Decimal(str(getattr(config, 'iva_rate', Decimal('19.00'))))

        if discount_pct is not None:
            # Clamp defensivo 0..100: este mismo calculo lo usa el endpoint
            # publico quote_package (AllowAny), que no pasa por el serializer
            # con min/max_value. Ver R-01 de la auditoria.
            discount_pct_val = max(Decimal('0'), min(Decimal('100'), Decimal(str(discount_pct))))
        else:
            discount_pct_val = Decimal('0.00')

        discount_amount = subtotal_after_rules * (discount_pct_val / Decimal('100.00'))
        taxable_base = subtotal_after_rules - discount_amount
        iva_amount = taxable_base * (iva_rate / Decimal('100.00'))
        total_price = taxable_base + iva_amount

        return {
            'variant_id': variant.id,
            'sku': variant.sku,
            'service_name': variant.service.name,
            'pricing_strategy': variant.pricing_strategy,
            'labor_cost': labor_cost.quantize(Decimal('0.01')),
            'material_cost': material_cost.quantize(Decimal('0.01')),
            'base_amount': base_amount.quantize(Decimal('0.01')),
            'discount_pct': discount_pct_val.quantize(Decimal('0.01')),
            'discount_amount': discount_amount.quantize(Decimal('0.01')),
            'iva_rate': iva_rate.quantize(Decimal('0.01')),
            'iva_amount': iva_amount.quantize(Decimal('0.01')),
            'total_price': total_price.quantize(Decimal('0.01')),
            'breakdown': {
                'hours': float(duration_val),
                'base_hourly_rate': float(base_hourly_rate.quantize(Decimal('0.01'))),
                'labor_calculation': labor_calculation,
                'complexity': float(variant.complexity_factor),
                'pricing_strategy': variant.pricing_strategy,
                'duration': float(duration_val),
                'min_duration': float(variant.min_duration) if variant.min_duration is not None else None,
                'max_duration': float(variant.max_duration) if variant.max_duration is not None else None,
                'materials': materials_breakdown,
                'base_amount': float(base_amount),
                'cost_rules': [
                    {
                        'name': line['name'],
                        'context': line['context'],
                        'cost_type': line['cost_type'],
                        'value': float(line['value']),
                        'amount': float(line['amount']),
                        'impact': float(line['amount']) * (-1 if line['is_discount'] else 1),
                        'is_discount': line['is_discount'],
                    }
                    for line in pricing_breakdown['costs']
                ],
                'total_additions': float(pricing_breakdown['total_additions']),
                'total_discounts_rules': float(pricing_breakdown['total_discounts']),
                'subtotal_after_rules': float(subtotal_after_rules),
                'discount_pct': float(discount_pct_val),
                'discount_amount': float(discount_amount),
                'iva_rate': float(iva_rate),
                'iva_amount': float(iva_amount),
                'total_price': float(total_price),
            }
        }


    @staticmethod
    def check_time_availability(
        variant_id: int,
        start_time: datetime,
        end_time: datetime,
        capacity_needed: int = 1,
    ) -> bool:
        """Retorna True si hay capacidad disponible para el rango [start_time, end_time).

        Algoritmo de solapamiento: un booking existente se solapa con el rango pedido si:
            existing.start_time < end_time  AND  existing.end_time > start_time
        La capacidad ocupada = numero de bookings activos/programados que se solapan.
        """
        from technical_services.models import ServiceBooking
        try:
            variant = ServiceVariant.objects.only('simultaneous_capacity').get(id=variant_id)
        except ServiceVariant.DoesNotExist:
            return False

        total_capacity = variant.simultaneous_capacity
        if total_capacity < capacity_needed:
            return False

        result = ServiceBooking.objects.filter(
            service_variant_id=variant_id,
            status__in=[ServiceBooking.STATUS_SCHEDULED, ServiceBooking.STATUS_ACTIVE],
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).aggregate(occupied=Count('id'))

        occupied: int = result['occupied'] or 0
        return (total_capacity - occupied) >= capacity_needed


class TechnicianSelector:
    @staticmethod
    def get_all_active_technicians():
        """
        Todos los tecnicos activos, sin filtrar por especialidad/categoria ni por
        is_available. Usado por la asignacion MANUAL (el administrador decide si
        esta calificado) -- a diferencia de find_best_technician(), que si exige
        coincidencia de categoria para la asignacion automatica.
        """
        from users.models import User
        return User.objects.filter(
            is_active=True,
            is_deleted=False,
            technician_profile__isnull=False,
        ).distinct()

    @staticmethod
    def get_active_technicians_for_category(category: ServiceCategory):
        """
        Igual que get_available_for_category() pero SIN filtrar por
        technician_profile__is_available -- usado por TechnicianAvailabilityEngine
        (2026-07-14), que calcula disponibilidad real via WorkingSchedule/
        WorkingException/ServiceOperation y no debe depender de la bandera legado.
        """
        from users.models import User
        current = category
        while current is not None:
            techs = User.objects.filter(
                is_active=True,
                is_deleted=False,
                technician_profile__specialties=current,
            ).distinct()
            if techs.exists():
                return techs
            current = current.parent

        return User.objects.filter(
            is_active=True,
            is_deleted=False,
            technician_profile__specialties=category,
        ).distinct()

    @staticmethod
    def get_available_for_category(category: ServiceCategory):
        from users.models import User
        current = category
        while current is not None:
            techs = User.objects.filter(
                is_active=True,
                is_deleted=False,
                technician_profile__is_available=True,
                technician_profile__specialties=current,
            ).distinct()
            if techs.exists():
                return techs
            current = current.parent

        return User.objects.filter(
            is_active=True,
            is_deleted=False,
            technician_profile__is_available=True,
            technician_profile__specialties=category,
        ).distinct()

    @staticmethod
    def get_candidates_for_order(order):
        """
        Deriva la categoria de la orden de servicio (via el primer item con service_variant)
        y retorna el queryset de tecnicos disponibles para esa categoria. Factoriza la logica
        de derivacion de categoria compartida entre find_best_technician() (asignacion
        automatica) y el endpoint de "tecnicos disponibles" del tablero de asignacion.
        Retorna None si la orden no tiene item de servicio o el servicio no tiene categoria.
        """
        order_item = order.items.filter(service_variant__isnull=False).first()
        if not order_item or not order_item.service_variant:
            return None

        category = order_item.service_variant.service.category
        if not category:
            return None

        return TechnicianSelector.get_available_for_category(category)

    @staticmethod
    def find_best_technician(order):
        """
        Evaluates order requirements (based on the service's category)
        and returns the first matching available technician.
        """
        candidates = TechnicianSelector.get_candidates_for_order(order)
        if candidates is None:
            return None
        return candidates.first()


class WorkingScheduleSelector:
    @staticmethod
    def list_for_technician(technician_uuid: str) -> QuerySet:
        return (
            WorkingSchedule.objects
            .filter(technician__uuid=technician_uuid, is_deleted=False)
            .order_by('weekday')
        )


class WorkingExceptionSelector:
    @staticmethod
    def list_for_technician(technician_uuid: str) -> QuerySet:
        return (
            WorkingException.objects
            .filter(technician__uuid=technician_uuid, is_deleted=False)
            .order_by('-start_date')
        )
