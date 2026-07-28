from django.db.models import QuerySet, Sum, Value, IntegerField, Prefetch
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from renting.models import (
    Equipment, EquipmentVariant, RentalLabor,
    RentingCategory, RentingBrand, RentalRequest, EquipmentBlock,
    EquipmentReturnInspection, EquipmentReview,
    RentalIncludedItem, RentalExcludedItem, RentalFeature,
    RentalSpecificationGroup, RentalSpecification, RentalRequirement,
    RentalServiceIncluded, RentalOptionalService, RentalFAQ,
    RentalVideo, RentalDocument, EquipmentCommercialOption,
)


class RentingSelector:
    LIST_FIELDS = ('id', 'uuid', 'name', 'slug', 'description', 'is_active', 'is_featured')

    @staticmethod
    def list_all_for_admin(search='', category_slug='', brand_slug='') -> QuerySet:
        qs = (
            Equipment.objects.filter(is_deleted=False)
            .select_related('category', 'brand', 'logistics_config', 'marketing')
            .prefetch_related('variants', 'images')
            .order_by('name')
        )
        if search:
            qs = qs.filter(name__icontains=search)
        if category_slug:
            qs = qs.filter(category__slug=category_slug)
        if brand_slug:
            qs = qs.filter(brand__slug=brand_slug)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> Equipment:
        """
        Detalle de equipo. Trae TODAS las secciones del catalogo enriquecido
        (2026-07-16) en un solo roundtrip via prefetch_related con Prefetch
        filtrado (is_deleted=False, orden por position) -- EquipmentDetailSerializer
        no dispara ninguna query adicional al recorrer estas relaciones.
        is_active se filtra en el serializer (el admin necesita ver las filas
        inactivas para poder reactivarlas; el publico no).
        """
        return get_object_or_404(
            Equipment.objects
            .select_related('logistics_config', 'marketing')
            .prefetch_related(
                'variants', 'images',
                Prefetch(
                    'reviews',
                    queryset=EquipmentReview.objects.filter(is_deleted=False).select_related('user'),
                ),
                Prefetch('included_items', queryset=RentalIncludedItem.objects.filter(is_deleted=False)),
                Prefetch('excluded_items', queryset=RentalExcludedItem.objects.filter(is_deleted=False)),
                Prefetch('features', queryset=RentalFeature.objects.filter(is_deleted=False)),
                Prefetch(
                    'specification_groups',
                    queryset=RentalSpecificationGroup.objects.filter(is_deleted=False),
                ),
                Prefetch(
                    'specification_groups__specifications',
                    queryset=RentalSpecification.objects.filter(is_deleted=False),
                ),
                Prefetch('requirements', queryset=RentalRequirement.objects.filter(is_deleted=False)),
                Prefetch('services_included', queryset=RentalServiceIncluded.objects.filter(is_deleted=False)),
                Prefetch('optional_services', queryset=RentalOptionalService.objects.filter(is_deleted=False)),
                Prefetch('faqs', queryset=RentalFAQ.objects.filter(is_deleted=False)),
                Prefetch('videos', queryset=RentalVideo.objects.filter(is_deleted=False)),
                Prefetch('documents', queryset=RentalDocument.objects.filter(is_deleted=False)),
            ),
            uuid=uuid, is_deleted=False,
        )

    @staticmethod
    def list_categories() -> QuerySet:
        return RentingCategory.objects.filter(is_active=True, is_deleted=False)

    @staticmethod
    def list_categories_for_admin() -> QuerySet:
        return RentingCategory.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def list_brands() -> QuerySet:
        return RentingBrand.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def list_available_equipment() -> QuerySet:
        """
        Equipos activos que tienen al menos una variante con stock fisico > 0.
        La disponibilidad real por fechas se comprueba con check_availability().
        """
        return (
            Equipment.objects
            .filter(
                is_active=True,
                is_deleted=False,
                variants__stock__gt=0,
                variants__is_active=True,
                variants__is_deleted=False,
            )
            .distinct()
            .select_related('logistics_config', 'marketing')
            .prefetch_related('variants', 'images')
        )

    @staticmethod
    def list_featured() -> QuerySet:
        """Equipos activos marcados como destacados para la Home publica, ordenados por solicitudes de renta."""
        return (
            Equipment.objects.filter(is_active=True, is_featured=True, is_deleted=False)
            .select_related('category', 'brand')
            .prefetch_related('variants', 'images')
            .annotate(
                total_rented=Coalesce(
                    Sum('variants__orderitem__quantity'),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('-total_rented', '-created_at')
        )

    @staticmethod
    def get_equipment_variant_by_uuid(uuid: str) -> EquipmentVariant:
        return get_object_or_404(EquipmentVariant, uuid=uuid, is_deleted=False)

    @staticmethod
    def list_rental_labor() -> QuerySet:
        return RentalLabor.objects.filter(is_active=True, is_deleted=False)

    @staticmethod
    def list_rental_labor_for_admin() -> QuerySet:
        return RentalLabor.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def check_availability(
        variant_id: int,
        start_date,
        end_date,
        quantity: int = 1,
    ) -> bool:
        """
        Verifica si hay suficientes unidades libres de `variant_id` para el rango
        [start_date, end_date) con la cantidad pedida (modo dias).

        Wrapper delgado sobre AvailabilityEngine.is_available() -- se mantiene por
        compatibilidad con los llamadores existentes (RentalRequestInputSerializer,
        RentalRequestCommands.create_request, RentingCommands.process_rental_order),
        que solo necesitan el booleano en modo dias.
        """
        from renting.services.availability import AvailabilityEngine

        return AvailabilityEngine.is_available(variant_id, start_date, end_date, quantity)


class EquipmentVariantSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return (
            EquipmentVariant.objects
            .filter(equipment__uuid=equipment_uuid, is_deleted=False)
            .order_by('-is_active', 'created_at')
        )

    @staticmethod
    def get_by_uuid(variant_uuid: str) -> EquipmentVariant:
        return get_object_or_404(EquipmentVariant, uuid=variant_uuid, is_deleted=False)


class EquipmentCommercialOptionSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return (
            EquipmentCommercialOption.objects
            .filter(equipment__uuid=equipment_uuid, is_deleted=False)
            .order_by('modality', 'term_months')
        )

    @staticmethod
    def get_by_uuid(option_uuid: str) -> EquipmentCommercialOption:
        return get_object_or_404(EquipmentCommercialOption, uuid=option_uuid, is_deleted=False)


class EquipmentBlockSelector:
    @staticmethod
    def list_for_variant(variant_uuid: str, active_only: bool = False) -> QuerySet:
        qs = (
            EquipmentBlock.objects
            .filter(equipment_variant__uuid=variant_uuid, is_deleted=False)
            .select_related('created_by', 'released_by')
            .order_by('-created_at')
        )
        if active_only:
            qs = qs.filter(status=EquipmentBlock.STATUS_ACTIVE)
        return qs

    @staticmethod
    def list_for_equipment(equipment_uuid: str, active_only: bool = False) -> QuerySet:
        qs = (
            EquipmentBlock.objects
            .filter(equipment_variant__equipment__uuid=equipment_uuid, is_deleted=False)
            .select_related('equipment_variant', 'created_by', 'released_by')
            .order_by('-created_at')
        )
        if active_only:
            qs = qs.filter(status=EquipmentBlock.STATUS_ACTIVE)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> EquipmentBlock:
        return get_object_or_404(EquipmentBlock, uuid=uuid, is_deleted=False)


class EquipmentReturnInspectionSelector:
    @staticmethod
    def get_for_request(rental_request_uuid: str) -> EquipmentReturnInspection | None:
        return (
            EquipmentReturnInspection.objects
            .filter(rental_request__uuid=rental_request_uuid, is_deleted=False)
            .select_related('inspected_by', 'resulting_block')
            .first()
        )


class EquipmentReviewSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return (
            EquipmentReview.objects
            .filter(equipment__uuid=equipment_uuid, is_deleted=False)
            .select_related('user')
            .order_by('-created_at')
        )


class RentalRequestSelector:
    @staticmethod
    def list_for_user(user) -> QuerySet:
        return (
            RentalRequest.objects
            .filter(user=user, is_deleted=False)
            .select_related(
                'equipment_variant__equipment__category',
                'equipment_variant__equipment__brand',
            )
            .prefetch_related('equipment_variant__equipment__images')
            .order_by('-created_at')
        )

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return (
            RentalRequest.objects
            .filter(is_deleted=False)
            .select_related(
                'user',
                'equipment_variant__equipment__category',
                'equipment_variant__equipment__brand',
            )
            .prefetch_related('equipment_variant__equipment__images')
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_uuid_for_user(uuid: str, user) -> RentalRequest:
        return get_object_or_404(
            RentalRequest.objects
            .select_related(
                'equipment_variant__equipment__category',
                'equipment_variant__equipment__brand',
            )
            .prefetch_related('equipment_variant__equipment__images'),
            uuid=uuid, user=user, is_deleted=False,
        )

    @staticmethod
    def get_by_uuid_for_admin(uuid: str) -> RentalRequest:
        return get_object_or_404(
            RentalRequest.objects
            .select_related(
                'user',
                'equipment_variant__equipment__category',
                'equipment_variant__equipment__brand',
            )
            .prefetch_related('equipment_variant__equipment__images'),
            uuid=uuid, is_deleted=False,
        )
