from decimal import Decimal
from django.db import transaction
from django.db.models import Count, F, OuterRef, Q, Subquery, Sum
from django.shortcuts import get_object_or_404
from django.http import Http404

# Import selectors and commands from other applications
from users.models import User


class _GenericCatalogChildOrchestrator:
    """
    Base compartida de los 4 orquestadores admin de catalogo hijo (Shop/Renting/
    Services/Packages) -- Sprint 4, 2026-08-05, auditoria transversal. Las 4
    delegaciones (list/get/create/update/delete/toggle_active/duplicate/reorder)
    eran identicas salvo el registro (REGISTRY) y el nombre del padre
    (PARENT_KWARG: 'product'/'equipment'/'service'/'package'). El nombre del
    metodo del Selector (`list_for_<PARENT_KWARG>`) no se unifico -- cada
    catalog.py de cada app sigue definiendo su propio `list_for_product()`/
    `list_for_equipment()`/etc, fuera del alcance de este sprint (solo se toca
    la capa de orquestacion admin) -- se resuelve dinamicamente via getattr.
    """
    REGISTRY: dict = {}
    PARENT_KWARG: str = 'parent'

    @classmethod
    def list_for_parent(cls, resource, parent_uuid):
        selector, _ = cls.REGISTRY[resource]
        return getattr(selector, f'list_for_{cls.PARENT_KWARG}')(parent_uuid)

    @classmethod
    def get(cls, resource, uuid):
        selector, _ = cls.REGISTRY[resource]
        return selector.get_by_uuid(uuid)

    @classmethod
    def create(cls, resource, parent, data):
        _, commands = cls.REGISTRY[resource]
        return commands.create(**{cls.PARENT_KWARG: parent}, **data)

    @classmethod
    def update(cls, resource, instance, data):
        _, commands = cls.REGISTRY[resource]
        return commands.update(instance, **data)

    @classmethod
    def delete(cls, resource, instance):
        _, commands = cls.REGISTRY[resource]
        commands.delete(instance)

    @classmethod
    def toggle_active(cls, resource, instance):
        _, commands = cls.REGISTRY[resource]
        return commands.toggle_active(instance)

    @classmethod
    def duplicate(cls, resource, instance):
        _, commands = cls.REGISTRY[resource]
        if not hasattr(commands, 'duplicate'):
            raise ValueError('Este recurso no admite duplicar.')
        return commands.duplicate(instance)

    @classmethod
    def reorder(cls, resource, parent_id, ordered_uuids):
        _, commands = cls.REGISTRY[resource]
        commands.reorder(parent_id, ordered_uuids)

from shop.services.selectors import (
    ProductSelector, CategorySelector, BrandSelector, TaxSelector, ProductVariantSelector
)
from shop.services.commands import (
    ProductCommands, CategoryCommands, BrandCommands, TaxCommands, ProductVariantCommands
)
from shop.services.catalog import (
    ProductImageSelector, ProductImageCommands,
    ProductIncludedItemSelector, ProductIncludedItemCommands,
    ProductExcludedItemSelector, ProductExcludedItemCommands,
    ProductFeatureSelector, ProductFeatureCommands,
    ProductSpecificationGroupSelector, ProductSpecificationGroupCommands,
    ProductSpecificationSelector, ProductSpecificationCommands,
    ProductRequirementSelector, ProductRequirementCommands,
    ProductServiceIncludedSelector, ProductServiceIncludedCommands,
    ProductOptionalServiceSelector, ProductOptionalServiceCommands,
    ProductFAQSelector, ProductFAQCommands,
    ProductVideoSelector, ProductVideoCommands,
    ProductDocumentSelector, ProductDocumentCommands,
    ProductFunctioningStepSelector, ProductFunctioningStepCommands,
)

# Recursos hijos de Product con shape identico (fila con position/is_active, FK directa a
# product): mismo patron ya usado en RentingCatalogChildOrchestrator/ServicePackageChildOrchestrator
# (2026-08-03, catalogo enriquecido de shop, espejo de renting.Equipment). ProductSpecification
# queda fuera (cuelga de ProductSpecificationGroup, no directo de Product) y ProductDocument
# tiene ademas su propio create() con archivo -- ver metodos dedicados en ShopAdminOrchestrator.
_SHOP_CATALOG_CHILD_REGISTRY = {
    'images': (ProductImageSelector, ProductImageCommands),
    'included-items': (ProductIncludedItemSelector, ProductIncludedItemCommands),
    'excluded-items': (ProductExcludedItemSelector, ProductExcludedItemCommands),
    'features': (ProductFeatureSelector, ProductFeatureCommands),
    'specification-groups': (ProductSpecificationGroupSelector, ProductSpecificationGroupCommands),
    'requirements': (ProductRequirementSelector, ProductRequirementCommands),
    'services-included': (ProductServiceIncludedSelector, ProductServiceIncludedCommands),
    'optional-services': (ProductOptionalServiceSelector, ProductOptionalServiceCommands),
    'faqs': (ProductFAQSelector, ProductFAQCommands),
    'videos': (ProductVideoSelector, ProductVideoCommands),
    'documents': (ProductDocumentSelector, ProductDocumentCommands),
    'functioning-steps': (ProductFunctioningStepSelector, ProductFunctioningStepCommands),
}


class ProductCatalogChildOrchestrator(_GenericCatalogChildOrchestrator):
    """Delegacion generica para los recursos de `_SHOP_CATALOG_CHILD_REGISTRY`."""
    REGISTRY = _SHOP_CATALOG_CHILD_REGISTRY
    PARENT_KWARG = 'product'

from technical_services.services import (
    ServiceSelector, ServiceCategorySelector, ServiceLevelSelector, ServiceVariantSelector,
    ServiceMaterialSelector, ServiceConfigurationSelector, TechnicalServiceCommands,
    ServiceCategoryCommands, ServiceLevelCommands, ServiceVariantCommands, ServicePricingCommands,
    ServiceMaterialCommands, ServiceConfigurationCommands,
    ServicePackageSelector, ServicePackageCommands,
    PackageIncludedItemSelector, PackageIncludedItemCommands,
    PackageAdditionalCostSelector, PackageAdditionalCostCommands,
)
from technical_services.services.commands import ServiceImageCommands
from technical_services.models import ServiceImage

# Recursos hijos de ServicePackage con shape identico (fila con position/is_active,
# FK directa a package): mismo patron ya usado en RentingCatalogChildOrchestrator.
_PACKAGE_CHILD_REGISTRY = {
    'included-items': (PackageIncludedItemSelector, PackageIncludedItemCommands),
    'additional-costs': (PackageAdditionalCostSelector, PackageAdditionalCostCommands),
}


class ServicePackageChildOrchestrator(_GenericCatalogChildOrchestrator):
    """Delegacion generica para los recursos de `_PACKAGE_CHILD_REGISTRY`."""
    REGISTRY = _PACKAGE_CHILD_REGISTRY
    PARENT_KWARG = 'package'

from technical_services.services.catalog import (
    ServiceIncludedItemSelector, ServiceIncludedItemCommands,
    ServiceExcludedItemSelector, ServiceExcludedItemCommands,
    ServiceRequirementSelector, ServiceRequirementCommands,
    ServiceSpecificationGroupSelector, ServiceSpecificationGroupCommands,
    ServiceSpecificationSelector, ServiceSpecificationCommands,
    ServiceDocumentSelector, ServiceDocumentCommands,
    ServiceVideoSelector, ServiceVideoCommands,
    ServiceProcessStepSelector, ServiceProcessStepCommands,
)

# Recursos hijos de TechnicalService con shape identico (fila con position/
# is_active, FK directa a service): mismo patron ya usado en
# ProductCatalogChildOrchestrator/RentingCatalogChildOrchestrator.
# ServiceSpecification queda fuera (cuelga de ServiceSpecificationGroup, no
# directo de TechnicalService) y ServiceDocument tiene ademas su propio
# create() con archivo -- ver metodos dedicados en ServiceAdminOrchestrator.
_SERVICE_CATALOG_CHILD_REGISTRY = {
    'included-items': (ServiceIncludedItemSelector, ServiceIncludedItemCommands),
    'excluded-items': (ServiceExcludedItemSelector, ServiceExcludedItemCommands),
    'requirements': (ServiceRequirementSelector, ServiceRequirementCommands),
    'specification-groups': (ServiceSpecificationGroupSelector, ServiceSpecificationGroupCommands),
    'documents': (ServiceDocumentSelector, ServiceDocumentCommands),
    'videos': (ServiceVideoSelector, ServiceVideoCommands),
    'process-steps': (ServiceProcessStepSelector, ServiceProcessStepCommands),
}


class ServiceCatalogChildOrchestrator(_GenericCatalogChildOrchestrator):
    """Delegacion generica para los recursos de `_SERVICE_CATALOG_CHILD_REGISTRY`."""
    REGISTRY = _SERVICE_CATALOG_CHILD_REGISTRY
    PARENT_KWARG = 'service'


from renting.services import (
    RentingSelector, EquipmentVariantSelector, EquipmentCommands, EquipmentVariantCommands,
    RentingCategoryCommands, RentingBrandCommands, RentalLaborCommands,
    EquipmentLogisticsConfigCommands,
    EquipmentCommercialConfigCommands, EquipmentCommercialOptionCommands,
    EquipmentCommercialOptionSelector,
    EquipmentImageSelector, EquipmentImageCommands,
    RentalIncludedItemSelector, RentalIncludedItemCommands,
    RentalExcludedItemSelector, RentalExcludedItemCommands,
    RentalFeatureSelector, RentalFeatureCommands,
    RentalSpecificationGroupSelector, RentalSpecificationGroupCommands,
    RentalSpecificationSelector, RentalSpecificationCommands,
    RentalRequirementSelector, RentalRequirementCommands,
    RentalServiceIncludedSelector, RentalServiceIncludedCommands,
    RentalOptionalServiceSelector, RentalOptionalServiceCommands,
    RentalFAQSelector, RentalFAQCommands,
    RentalVideoSelector, RentalVideoCommands,
    RentalDocumentSelector, RentalDocumentCommands,
)

# Recursos hijos de Equipment con shape identico (fila con position/is_active,
# FK directa a equipment): list/create/update/delete/toggle/reorder se
# factorizan en RentingCatalogChildOrchestrator para no repetir la misma
# delegacion 11 veces. RentalSpecification queda fuera (cuelga de
# RentalSpecificationGroup, no directo de Equipment) y RentalDocument tiene
# ademas su propio create() con archivo -- ver metodos dedicados abajo.
_CATALOG_CHILD_REGISTRY = {
    'images': (EquipmentImageSelector, EquipmentImageCommands),
    'included-items': (RentalIncludedItemSelector, RentalIncludedItemCommands),
    'excluded-items': (RentalExcludedItemSelector, RentalExcludedItemCommands),
    'features': (RentalFeatureSelector, RentalFeatureCommands),
    'specification-groups': (RentalSpecificationGroupSelector, RentalSpecificationGroupCommands),
    'requirements': (RentalRequirementSelector, RentalRequirementCommands),
    'services-included': (RentalServiceIncludedSelector, RentalServiceIncludedCommands),
    'optional-services': (RentalOptionalServiceSelector, RentalOptionalServiceCommands),
    'faqs': (RentalFAQSelector, RentalFAQCommands),
    'videos': (RentalVideoSelector, RentalVideoCommands),
    'documents': (RentalDocumentSelector, RentalDocumentCommands),
}


class RentingCatalogChildOrchestrator(_GenericCatalogChildOrchestrator):
    """Delegacion generica para los recursos de `_CATALOG_CHILD_REGISTRY`."""
    REGISTRY = _CATALOG_CHILD_REGISTRY
    PARENT_KWARG = 'equipment'
from renting.models import RentingCategory, RentingBrand, RentalLabor

from quotes.services import (
    QuotationSelector, QuotationCommands, QuotationReviewCommands,
    QuoteTemplateCategorySelector, QuoteTemplateSubcategorySelector, QuoteTemplateSelector,
    QuoteTemplateAttributeSelector, QuoteEquipmentTypeSelector, QuoteTemplateModuleSelector,
    QuoteQuestionSelector, QuoteQuestionOptionSelector,
    QuoteTemplateCategoryCommands, QuoteTemplateSubcategoryCommands, QuoteTemplateCommands,
    QuoteTemplateAttributeCommands, QuoteEquipmentTypeCommands, QuoteTemplateModuleCommands,
    QuoteQuestionCommands, QuoteQuestionOptionCommands,
)
from orders.services.selectors import OrderSelector
from orders.models import Order
from shop.models import Product

from marketing.services import MarketingSelector
from marketing.models import MarketingCampaign, FlashOffer, AgentRun


# Nota: la administracion de usuarios vive exclusivamente en users.api.views.UserViewSet
# (/api/v1/users/) -- UserAdminOrchestrator existio aca y fue eliminado (2026-07-05): duplicaba
# ese ViewSet sin que el frontend lo llamara nunca, y ya habia divergido (update_user ignoraba
# is_active/is_verified).


class ShopAdminOrchestrator:
    # Products
    @staticmethod
    def list_products():
        return ProductSelector.list_all_for_admin()

    @staticmethod
    def get_product(uuid):
        return ProductSelector.get_by_uuid(uuid)

    @staticmethod
    @transaction.atomic
    def create_product(vendor, data):
        return ProductCommands.create_product(vendor=vendor, **data)

    @staticmethod
    @transaction.atomic
    def update_product(product, data):
        return ProductCommands.update_product(product, data)

    @staticmethod
    @transaction.atomic
    def delete_product(product):
        return ProductCommands.delete_product(product)

    # Categories
    @staticmethod
    def list_categories():
        return CategorySelector.list_all_for_admin()

    @staticmethod
    def get_category(uuid):
        return CategorySelector.get_by_uuid(uuid)

    @staticmethod
    @transaction.atomic
    def create_category(data):
        return CategoryCommands.create_category(**data)

    @staticmethod
    @transaction.atomic
    def update_category(category, data):
        return CategoryCommands.update_category(category, data)

    @staticmethod
    @transaction.atomic
    def delete_category(category):
        return CategoryCommands.delete_category(category)

    # Brands
    @staticmethod
    def list_brands():
        return BrandSelector.list_all_for_admin()

    @staticmethod
    def get_brand(uuid):
        return BrandSelector.get_by_uuid(uuid)

    @staticmethod
    @transaction.atomic
    def create_brand(data):
        return BrandCommands.create_brand(**data)

    @staticmethod
    @transaction.atomic
    def update_brand(brand, data):
        return BrandCommands.update_brand(brand, data)

    @staticmethod
    @transaction.atomic
    def delete_brand(brand):
        return BrandCommands.delete_brand(brand)

    # Taxes
    @staticmethod
    def list_taxes():
        return TaxSelector.list_all()

    @staticmethod
    def get_tax(uuid):
        return TaxSelector.get_by_uuid(uuid)

    @staticmethod
    @transaction.atomic
    def create_tax(data):
        return TaxCommands.create_tax(**data)

    @staticmethod
    @transaction.atomic
    def update_tax(tax, data):
        return TaxCommands.update_tax(tax, data)

    @staticmethod
    @transaction.atomic
    def delete_tax(tax):
        return TaxCommands.delete_tax(tax)

    # Variants
    @staticmethod
    def list_variants(product_uuid):
        return ProductVariantSelector.list_for_product(product_uuid)

    @staticmethod
    def get_variant(uuid):
        return ProductVariantSelector.get_by_uuid(uuid)

    @staticmethod
    @transaction.atomic
    def create_variant(product, data):
        return ProductVariantCommands.create_variant(product=product, **data)

    @staticmethod
    @transaction.atomic
    def update_variant(variant, data):
        return ProductVariantCommands.update_variant(variant, data)

    @staticmethod
    @transaction.atomic
    def delete_variant(variant):
        return ProductVariantCommands.delete_variant(variant)

    # Catalogo enriquecido (2026-08-03) -- Specifications (fila, cuelga de un
    # ProductSpecificationGroup ademas de product) y Documents (create() valida el archivo)
    # quedan fuera del registro generico de ProductCatalogChildOrchestrator, mismo criterio
    # que RentalSpecification/RentalDocument en RentingAdminOrchestrator.
    @staticmethod
    def list_specifications(product_uuid=None, group_uuid=None):
        if group_uuid:
            return ProductSpecificationSelector.list_for_group(group_uuid)
        return ProductSpecificationSelector.list_for_product(product_uuid)

    @staticmethod
    def get_specification(uuid):
        return ProductSpecificationSelector.get_by_uuid(uuid)

    @staticmethod
    def create_specification(product, data):
        group = data.pop('group')
        return ProductSpecificationCommands.create(product=product, group=group, **data)

    @staticmethod
    def update_specification(instance, data):
        return ProductSpecificationCommands.update(instance, **data)

    @staticmethod
    def delete_specification(instance):
        ProductSpecificationCommands.delete(instance)

    @staticmethod
    def toggle_specification(instance):
        return ProductSpecificationCommands.toggle_active(instance)

    @staticmethod
    def duplicate_specification(instance):
        return ProductSpecificationCommands.duplicate(instance)

    @staticmethod
    def reorder_specifications(group_id, ordered_uuids):
        ProductSpecificationCommands.reorder(group_id, ordered_uuids)

    @staticmethod
    def create_document(product, data):
        return ProductDocumentCommands.create(product=product, **data)


class ServiceAdminOrchestrator:
    # Services
    @staticmethod
    def list_services():
        return ServiceSelector.list_all_for_admin()

    @staticmethod
    def get_service(uuid):
        return ServiceSelector.get_by_uuid(uuid)

    @staticmethod
    def create_service(vendor, data):
        return TechnicalServiceCommands.create_service(vendor=vendor, **data)

    @staticmethod
    def create_service_with_default_variant(vendor, service_data, variant_data=None):
        return TechnicalServiceCommands.create_service_with_default_variant(
            service_data=service_data,
            variant_data=variant_data,
            vendor=vendor,
        )

    @staticmethod
    def update_service(service, data):
        return TechnicalServiceCommands.update_service(service, data)

    @staticmethod
    def delete_service(service):
        return TechnicalServiceCommands.delete_service(service)

    # Categories
    @staticmethod
    def list_categories():
        return ServiceCategorySelector.list_all_for_admin()

    @staticmethod
    def get_category(uuid):
        return ServiceCategorySelector.get_by_uuid(uuid)

    @staticmethod
    def create_category(data):
        return ServiceCategoryCommands.create_category(**data)

    @staticmethod
    def update_category(category, data):
        return ServiceCategoryCommands.update_category(category, data)

    @staticmethod
    def delete_category(category):
        return ServiceCategoryCommands.delete_category(category)

    # Levels
    @staticmethod
    def list_levels():
        return ServiceLevelSelector.list_all()

    @staticmethod
    def get_level(uuid):
        return ServiceLevelSelector.get_by_uuid(uuid)

    @staticmethod
    def create_level(data):
        return ServiceLevelCommands.create_level(**data)

    @staticmethod
    def update_level(level, data):
        return ServiceLevelCommands.update_level(level, data)

    @staticmethod
    def delete_level(level):
        return ServiceLevelCommands.delete_level(level)

    # Variants
    @staticmethod
    def list_variants(service_uuid):
        return ServiceVariantSelector.list_for_service(service_uuid)

    @staticmethod
    def get_variant(uuid):
        return ServiceVariantSelector.get_by_uuid(uuid)

    @staticmethod
    def create_variant(service, data):
        return ServiceVariantCommands.create_variant(service=service, **data)

    @staticmethod
    def update_variant(variant, data, updated_by=None):
        return ServiceVariantCommands.update_variant(variant, data, updated_by=updated_by)

    @staticmethod
    def get_variant_price_history(variant):
        return ServiceVariantSelector.get_price_history(variant)

    @staticmethod
    def delete_variant(variant):
        return ServiceVariantCommands.delete_variant(variant)

    @staticmethod
    def set_variant_pricing(variant, pricing_source, unit_price=None, project_price=None, changed_by=None, reason=''):
        """Plan 'Manual Pricing Engine' FASE 8 -- unica via BFF para cambiar
        pricing_source de una variante, ver SetVariantPricingInputSerializer."""
        return ServicePricingCommands.set_manual_pricing(
            variant, pricing_source, unit_price=unit_price, project_price=project_price,
            changed_by=changed_by, reason=reason,
        )

    # Packages (paquetes de servicio, 2026-07-16)
    @staticmethod
    def list_packages(service_uuid):
        return ServicePackageSelector.list_for_service(service_uuid)

    @staticmethod
    def get_package(uuid):
        return ServicePackageSelector.get_by_uuid(uuid)

    @staticmethod
    def create_package(service, data):
        return ServicePackageCommands.create(service, **data)

    @staticmethod
    def update_package(package, data):
        return ServicePackageCommands.update(package, **data)

    @staticmethod
    def delete_package(package):
        return ServicePackageCommands.delete(package)

    @staticmethod
    def toggle_package(package):
        return ServicePackageCommands.toggle_active(package)

    @staticmethod
    def duplicate_package(package):
        return ServicePackageCommands.duplicate(package)

    @staticmethod
    def reorder_packages(service_id, ordered_uuids):
        ServicePackageCommands.reorder(service_id, ordered_uuids)

    # Materials
    @staticmethod
    def list_materials(variant_uuid):
        return ServiceMaterialSelector.list_for_variant(variant_uuid)

    @staticmethod
    def get_material(uuid):
        return ServiceMaterialSelector.get_by_uuid(uuid)

    @staticmethod
    def add_material(variant, product_variant, quantity):
        return ServiceMaterialCommands.add_material(
            variant=variant,
            product_variant=product_variant,
            quantity=quantity
        )

    @staticmethod
    def remove_material(material):
        return ServiceMaterialCommands.remove_material(material)

    # Images
    @staticmethod
    def add_image(service, image_file, alt_text='', is_primary=False, caption='', description=''):
        return ServiceImageCommands.add_image(
            service, image_file, alt_text=alt_text, is_primary=is_primary,
            caption=caption, description=description,
        )

    @staticmethod
    def get_image(uuid):
        return get_object_or_404(ServiceImage, uuid=uuid)

    @staticmethod
    def delete_image(image):
        return ServiceImageCommands.delete_image(image)

    @staticmethod
    def set_primary_image(image):
        return ServiceImageCommands.set_primary(image)

    @staticmethod
    def update_image_metadata(image, **fields):
        return ServiceImageCommands.update_metadata(image, **fields)

    @staticmethod
    def replace_image_file(image, image_file):
        return ServiceImageCommands.replace_file(image, image_file)

    @staticmethod
    def reorder_images(service, ordered_uuids):
        return ServiceImageCommands.reorder(service, ordered_uuids)

    # Catalogo enriquecido (2026-08-05) -- especificaciones (cuelgan de
    # ServiceSpecificationGroup) y documentos (create() propio con archivo),
    # mismo patron que ShopAdminOrchestrator/RentingAdminOrchestrator.
    @staticmethod
    def list_specifications(service_uuid=None, group_uuid=None):
        if group_uuid:
            return ServiceSpecificationSelector.list_for_group(group_uuid)
        return ServiceSpecificationSelector.list_for_service(service_uuid)

    @staticmethod
    def get_specification(uuid):
        return ServiceSpecificationSelector.get_by_uuid(uuid)

    @staticmethod
    def create_specification(service, data):
        group = data.pop('group')
        return ServiceSpecificationCommands.create(service=service, group=group, **data)

    @staticmethod
    def update_specification(instance, data):
        return ServiceSpecificationCommands.update(instance, **data)

    @staticmethod
    def delete_specification(instance):
        ServiceSpecificationCommands.delete(instance)

    @staticmethod
    def toggle_specification(instance):
        return ServiceSpecificationCommands.toggle_active(instance)

    @staticmethod
    def duplicate_specification(instance):
        return ServiceSpecificationCommands.duplicate(instance)

    @staticmethod
    def reorder_specifications(group_id, ordered_uuids):
        ServiceSpecificationCommands.reorder(group_id, ordered_uuids)

    @staticmethod
    def create_document(service, data):
        return ServiceDocumentCommands.create(service=service, **data)


class ServiceAdminRequestSelector:
    """
    Fachada de LECTURA para /panel/servicios > Solicitudes (Plan "Fachada
    Administrativa Unificada", 2026-08-14). Combina Order + OrderServiceDetail
    + ServiceOperation + tecnico en una sola consulta optimizada -- NUNCA
    escribe. Ownership sin cambios: ver
    technical_services/.AGENT/SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md.

    `current_status` reusa el mismo patron Subquery/OuterRef que
    AdminMetricsOrchestrator._get_marketplace_metrics() (OrderServiceTimeline
    es un log append-only, no un campo vivo en Order).
    """

    @staticmethod
    def base_queryset():
        from django.db.models import Prefetch
        from technical_services.models import OrderServiceTimeline, ServiceOperationEvent

        latest_status_sq = (
            OrderServiceTimeline.objects
            .filter(order=OuterRef('pk'))
            .order_by('-created_at')
            .values('status')[:1]
        )
        return (
            Order.objects
            .filter(service_detail__isnull=False)
            .select_related(
                'user',
                'user__profile',
                'service_detail',
                'service_detail__technician',
                'service_detail__technician__profile',
                'service_detail__technician__technician_profile',
                'service_operation',
                'service_operation__technician',
                'service_operation__technician__profile',
                'service_operation__technician__technician_profile',
            )
            .prefetch_related(
                'items__service_variant__service__category',
                Prefetch(
                    'service_operation__timeline',
                    queryset=ServiceOperationEvent.objects.select_related('actor', 'actor__profile').order_by('created_at'),
                ),
                Prefetch(
                    'timeline',
                    queryset=OrderServiceTimeline.objects.select_related('created_by', 'created_by__profile').order_by('created_at'),
                ),
            )
            .annotate(current_status=Subquery(latest_status_sq))
            .order_by('-created_at')
        )

    @staticmethod
    def list_for_admin(status=None, priority=None, technician_id=None, has_technician=None, search=''):
        qs = ServiceAdminRequestSelector.base_queryset()
        if status:
            qs = qs.filter(service_operation__status=status)
        if priority:
            qs = qs.filter(service_detail__priority=priority)
        if technician_id:
            qs = qs.filter(service_operation__technician_id=technician_id)
        if has_technician == 'false':
            qs = qs.filter(service_operation__technician__isnull=True)
        elif has_technician == 'true':
            qs = qs.filter(service_operation__technician__isnull=False)
        if search:
            qs = qs.filter(
                Q(tracking_number__icontains=search)
                | Q(user__email__icontains=search)
                | Q(items__service_variant__service__name__icontains=search)
            ).distinct()
        return qs

    @staticmethod
    def get_by_uuid(uuid):
        return get_object_or_404(ServiceAdminRequestSelector.base_queryset(), uuid=uuid)


class ServiceAdminRequestOrchestrator:
    """
    Fachada de ESCRITURA para /panel/servicios > Solicitudes. Cada metodo es
    una delegacion de una linea al comando real -- nunca reimplementa una
    transicion ni hace Model.objects.update() directo (regla vinculante de
    SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md).

    No existe `approve_request()`: no hay ningun estado tipo
    `pending_validation` en el backend de servicios (a diferencia de
    Renting) -- ServiceOperation nace ya en READY_FOR_PLANNING dentro de
    ServiceCommands.request_service(). Inventar un "aprobar" que no dispara
    ninguna transicion real violaria la regla de no crear FSM paralela
    (ver hallazgo H2 del baseline).
    """

    @staticmethod
    def list_requests(**filters):
        return ServiceAdminRequestSelector.list_for_admin(**filters)

    @staticmethod
    def get_request(uuid):
        return ServiceAdminRequestSelector.get_by_uuid(uuid)

    @staticmethod
    def plan_request(order, *, scheduled_date, scheduled_time, estimated_duration_minutes=None, notes='', actor=None):
        from technical_services.services.operations import ServiceOperationCommands
        return ServiceOperationCommands.plan(
            order.service_operation,
            scheduled_date=scheduled_date, scheduled_time=scheduled_time,
            estimated_duration_minutes=estimated_duration_minutes, notes=notes, actor=actor,
        )

    @staticmethod
    def assign_technician(order, *, technician, actor=None):
        from technical_services.services.operations import ServiceOperationCommands
        return ServiceOperationCommands.assign_technician(order.service_operation, technician=technician, actor=actor)

    @staticmethod
    def schedule_request(order, *, scheduled_date, scheduled_time, estimated_duration_minutes=None, actor=None):
        from technical_services.services.operations import ServiceOperationCommands
        return ServiceOperationCommands.reschedule(
            order.service_operation,
            scheduled_date=scheduled_date, scheduled_time=scheduled_time,
            estimated_duration_minutes=estimated_duration_minutes, actor=actor,
        )

    @staticmethod
    def notify_customer(order, actor=None):
        from technical_services.services.operations import ServiceOperationCommands
        return ServiceOperationCommands.notify_client(order.service_operation, actor=actor)

    @staticmethod
    def cancel_request(order, *, reason='', actor=None):
        from technical_services.services.operations import ServiceOperationCommands
        return ServiceOperationCommands.cancel(order.service_operation, reason=reason, actor=actor)


class RentingAdminOrchestrator:
    # Equipment
    @staticmethod
    def list_equipment(search='', category_slug='', brand_slug=''):
        return RentingSelector.list_all_for_admin(
            search=search, category_slug=category_slug, brand_slug=brand_slug
        )

    @staticmethod
    def get_equipment(uuid):
        return RentingSelector.get_by_uuid(uuid)

    @staticmethod
    def create_equipment(user, data):
        return EquipmentCommands.create_equipment(user=user, **data)

    @staticmethod
    def update_equipment(equipment, data):
        return EquipmentCommands.update_equipment(equipment, **data)

    @staticmethod
    def delete_equipment(equipment):
        return EquipmentCommands.delete_equipment(equipment)

    # Variants
    @staticmethod
    def list_variants(equipment_uuid):
        return EquipmentVariantSelector.list_for_equipment(equipment_uuid)

    @staticmethod
    def get_variant(uuid):
        return EquipmentVariantSelector.get_by_uuid(uuid)

    @staticmethod
    def create_variant(data):
        return EquipmentVariantCommands.create_variant(
            equipment=data['equipment'],
            sku=data['sku'],
            rental_price_per_day=data.get('rental_price_per_day'),
            rental_price_per_hour=data.get('rental_price_per_hour'),
            stock=data.get('stock', 0),
            is_active=data.get('is_active', True),
        )

    @staticmethod
    def update_variant(variant, data):
        data.pop('equipment', None)
        return EquipmentVariantCommands.update_variant(variant, **data)

    @staticmethod
    def delete_variant(variant):
        return EquipmentVariantCommands.delete_variant(variant)

    # Categories
    @staticmethod
    def list_categories():
        return RentingSelector.list_categories_for_admin()

    @staticmethod
    def get_category(uuid):
        return get_object_or_404(RentingCategory, uuid=uuid, is_deleted=False)

    @staticmethod
    def create_category(data):
        return RentingCategoryCommands.create_category(**data)

    @staticmethod
    def update_category(category, data):
        return RentingCategoryCommands.update_category(category, **data)

    @staticmethod
    def delete_category(category):
        return RentingCategoryCommands.delete_category(category)

    # Brands
    @staticmethod
    def list_brands():
        return RentingSelector.list_brands()

    @staticmethod
    def get_brand(uuid):
        return get_object_or_404(RentingBrand, uuid=uuid, is_deleted=False)

    @staticmethod
    def create_brand(name):
        return RentingBrandCommands.create_brand(name=name)

    @staticmethod
    def update_brand(brand, name):
        return RentingBrandCommands.update_brand(brand, name=name)

    @staticmethod
    def delete_brand(brand):
        return RentingBrandCommands.delete_brand(brand)

    # Labor
    @staticmethod
    def list_labor():
        return RentingSelector.list_rental_labor_for_admin()

    @staticmethod
    def get_labor(uuid):
        return get_object_or_404(RentalLabor, uuid=uuid, is_deleted=False)

    @staticmethod
    def create_labor(data):
        return RentalLaborCommands.create_labor(**data)

    @staticmethod
    def update_labor(labor, data):
        return RentalLaborCommands.update_labor(labor, **data)

    @staticmethod
    def delete_labor(labor):
        return RentalLaborCommands.delete_labor(labor)

    # Logistics Config
    @staticmethod
    def upsert_logistics_config(equipment, data):
        return EquipmentLogisticsConfigCommands.upsert(equipment, **data)

    @staticmethod
    def delete_logistics_config(equipment):
        return EquipmentLogisticsConfigCommands.delete(equipment)

    # Commercial Config (2026-07-22 -- Comodato)
    @staticmethod
    def upsert_commercial_config(equipment, data):
        return EquipmentCommercialConfigCommands.upsert(equipment, **data)

    @staticmethod
    def delete_commercial_config(equipment):
        return EquipmentCommercialConfigCommands.delete(equipment)

    # Commercial Options -- plazos por equipo/modalidad
    @staticmethod
    def list_commercial_options(equipment_uuid):
        return EquipmentCommercialOptionSelector.list_for_equipment(equipment_uuid)

    @staticmethod
    def get_commercial_option(uuid):
        return EquipmentCommercialOptionSelector.get_by_uuid(uuid)

    @staticmethod
    def upsert_commercial_option(equipment, data):
        return EquipmentCommercialOptionCommands.upsert(equipment, **data)

    @staticmethod
    def delete_commercial_option(option_uuid):
        return EquipmentCommercialOptionCommands.delete(option_uuid)

    # Specifications (fila, cuelga de un RentalSpecificationGroup ademas de equipment)
    @staticmethod
    def list_specifications(equipment_uuid=None, group_uuid=None):
        if group_uuid:
            return RentalSpecificationSelector.list_for_group(group_uuid)
        return RentalSpecificationSelector.list_for_equipment(equipment_uuid)

    @staticmethod
    def get_specification(uuid):
        return RentalSpecificationSelector.get_by_uuid(uuid)

    @staticmethod
    def create_specification(equipment, data):
        group = data.pop('group')
        return RentalSpecificationCommands.create(equipment=equipment, group=group, **data)

    @staticmethod
    def update_specification(instance, data):
        return RentalSpecificationCommands.update(instance, **data)

    @staticmethod
    def delete_specification(instance):
        RentalSpecificationCommands.delete(instance)

    @staticmethod
    def toggle_specification(instance):
        return RentalSpecificationCommands.toggle_active(instance)

    @staticmethod
    def duplicate_specification(instance):
        return RentalSpecificationCommands.duplicate(instance)

    @staticmethod
    def reorder_specifications(group_id, ordered_uuids):
        RentalSpecificationCommands.reorder(group_id, ordered_uuids)

    # Documents (create() valida el archivo -- distinto del resto del registro generico)
    @staticmethod
    def create_document(equipment, data):
        return RentalDocumentCommands.create(equipment=equipment, **data)


class QuotationAdminOrchestrator:
    @staticmethod
    def list_quotations():
        return QuotationSelector.list_all_for_admin()

    @staticmethod
    def get_quotation(uuid):
        return QuotationSelector.get_by_uuid(uuid)

    @staticmethod
    def create_quotation(data, user):
        client_data = {
            'client_name': data['client_name'],
            'client_email': data['client_email'],
            'valid_until': data['valid_until'],
            'notes': data.get('notes', ''),
            'user': user if user.is_authenticated else None
        }
        return QuotationCommands.create_quotation(
            client_data=client_data,
            product_items=data.get('product_items'),
            service_items=data.get('service_items')
        )

    @staticmethod
    def partial_update(quotation, data: dict):
        return QuotationCommands.partial_update(quotation, data)

    @staticmethod
    def change_status(quotation, new_status, notes, changed_by):
        return QuotationReviewCommands.change_status(quotation, new_status, notes, changed_by)

    @staticmethod
    def add_item(quotation, item_data):
        return QuotationReviewCommands.add_product_item(quotation, item_data)

    @staticmethod
    def add_service(quotation, service_data):
        return QuotationReviewCommands.add_service_item(quotation, service_data)


class QuoteTemplateAdminOrchestrator:
    """Constructor de Cuestionarios Tecnicos: dominio de definicion de
    plantillas (categorias, subcategorias, plantillas, tipos de equipo,
    modulos de Equipos/Materiales/Mano de Obra, preguntas, opciones)."""

    # Categories
    @staticmethod
    def list_categories():
        return QuoteTemplateCategorySelector.list_all()

    @staticmethod
    def get_category(uuid):
        return QuoteTemplateCategorySelector.get_by_uuid(uuid)

    @staticmethod
    def create_category(data):
        return QuoteTemplateCategoryCommands.create_category(**data)

    @staticmethod
    def update_category(category, data):
        return QuoteTemplateCategoryCommands.update_category(category, data)

    @staticmethod
    def delete_category(category):
        return QuoteTemplateCategoryCommands.delete_category(category)

    # Subcategories
    @staticmethod
    def list_subcategories(category_uuid=None):
        if category_uuid:
            return QuoteTemplateSubcategorySelector.list_for_category(category_uuid)
        return QuoteTemplateSubcategorySelector.list_all()

    @staticmethod
    def get_subcategory(uuid):
        return QuoteTemplateSubcategorySelector.get_by_uuid(uuid)

    @staticmethod
    def create_subcategory(data):
        return QuoteTemplateSubcategoryCommands.create_subcategory(**data)

    @staticmethod
    def update_subcategory(subcategory, data):
        return QuoteTemplateSubcategoryCommands.update_subcategory(subcategory, data)

    @staticmethod
    def delete_subcategory(subcategory):
        return QuoteTemplateSubcategoryCommands.delete_subcategory(subcategory)

    # Templates
    @staticmethod
    def list_templates():
        return QuoteTemplateSelector.list_all_for_admin()

    @staticmethod
    def get_template(uuid):
        return QuoteTemplateSelector.get_by_uuid(uuid)

    @staticmethod
    def create_template(data):
        return QuoteTemplateCommands.create_template(**data)

    @staticmethod
    def update_template(template, data):
        return QuoteTemplateCommands.update_template(template, data)

    @staticmethod
    def delete_template(template):
        return QuoteTemplateCommands.delete_template(template)

    @staticmethod
    def clone_template(template):
        return QuoteTemplateCommands.clone_template(template)

    # Atributos de plantilla (Tipo de Servicio / Instalacion / Sistema — mismo modelo, kind distinto)
    @staticmethod
    def list_attributes(kind=None, subcategory=None):
        return QuoteTemplateAttributeSelector.list_all(kind, subcategory)

    @staticmethod
    def get_attribute(uuid):
        return QuoteTemplateAttributeSelector.get_by_uuid(uuid)

    @staticmethod
    def create_attribute(data):
        return QuoteTemplateAttributeCommands.create_attribute(**data)

    @staticmethod
    def update_attribute(attribute, data):
        return QuoteTemplateAttributeCommands.update_attribute(attribute, data)

    @staticmethod
    def delete_attribute(attribute):
        return QuoteTemplateAttributeCommands.delete_attribute(attribute)

    # Equipment types (catalogo reutilizable)
    @staticmethod
    def list_equipment_types():
        return QuoteEquipmentTypeSelector.list_all()

    @staticmethod
    def get_equipment_type(uuid):
        return QuoteEquipmentTypeSelector.get_by_uuid(uuid)

    @staticmethod
    def create_equipment_type(data):
        return QuoteEquipmentTypeCommands.create_equipment_type(**data)

    @staticmethod
    def update_equipment_type(equipment_type, data):
        return QuoteEquipmentTypeCommands.update_equipment_type(equipment_type, data)

    @staticmethod
    def delete_equipment_type(equipment_type):
        return QuoteEquipmentTypeCommands.delete_equipment_type(equipment_type)

    # Modulos (Equipos / Materiales / Mano de Obra — mismo modelo, module_type distinto)
    @staticmethod
    def list_modules(template_uuid, module_type=None):
        return QuoteTemplateModuleSelector.list_for_template(template_uuid, module_type)

    @staticmethod
    def get_module(uuid):
        return QuoteTemplateModuleSelector.get_by_uuid(uuid)

    @staticmethod
    def create_module(template, data):
        return QuoteTemplateModuleCommands.create_module(template=template, **data)

    @staticmethod
    def update_module(module, data):
        return QuoteTemplateModuleCommands.update_module(module, data)

    @staticmethod
    def delete_module(module):
        return QuoteTemplateModuleCommands.delete_module(module)

    @staticmethod
    def duplicate_module(module):
        return QuoteTemplateModuleCommands.duplicate_module(module)

    @staticmethod
    def reorder_module(module, direction):
        return QuoteTemplateModuleCommands.reorder_module(module, direction)

    # Questions
    @staticmethod
    def list_questions(module_uuid):
        return QuoteQuestionSelector.list_for_module(module_uuid)

    @staticmethod
    def get_question(uuid):
        return QuoteQuestionSelector.get_by_uuid(uuid)

    @staticmethod
    def create_question(module, data):
        return QuoteQuestionCommands.create_question(module=module, **data)

    @staticmethod
    def update_question(question, data):
        return QuoteQuestionCommands.update_question(question, data)

    @staticmethod
    def delete_question(question):
        return QuoteQuestionCommands.delete_question(question)

    @staticmethod
    def duplicate_question_to_module(question, target_module):
        return QuoteQuestionCommands.duplicate_to_module(question, target_module)

    # Question options
    @staticmethod
    def list_options(question_uuid):
        return QuoteQuestionOptionSelector.list_for_question(question_uuid)

    @staticmethod
    def get_option(uuid):
        return QuoteQuestionOptionSelector.get_by_uuid(uuid)

    @staticmethod
    def create_option(question, data):
        return QuoteQuestionOptionCommands.create_option(question=question, **data)

    @staticmethod
    def update_option(option, data):
        return QuoteQuestionOptionCommands.update_option(option, data)

    @staticmethod
    def delete_option(option):
        return QuoteQuestionOptionCommands.delete_option(option)


class OrderAdminOrchestrator:
    @staticmethod
    def list_orders():
        return OrderSelector.list_all_for_admin()

    @staticmethod
    def get_order(uuid):
        return OrderSelector.get_by_uuid(uuid)


class MarketingAdminOrchestrator:
    @staticmethod
    def list_campaigns():
        return MarketingSelector.list_campaigns_for_admin()

    @staticmethod
    def list_flash_offers():
        return MarketingSelector.list_flash_offers()

    @staticmethod
    def list_agent_runs():
        return MarketingSelector.list_agent_runs()

    @staticmethod
    def get_consolidated_dashboard():
        return MarketingSelector.get_consolidated_dashboard()


class AdminMetricsOrchestrator:
    """Metricas principales del panel. Unico punto de agregacion para el dashboard."""

    @staticmethod
    def get_metrics() -> dict:
        from users.services.selectors import UserSelector

        all_orders_qs = OrderSelector.list_all_for_admin()
        total_sales = (
            all_orders_qs
            .filter(status__in=['paid', 'delivered'])
            .aggregate(s=Sum('total_amount'))['s'] or Decimal('0.00')
        )
        recent_orders = list(
            all_orders_qs
            .values('id', 'uuid', 'status', 'total_amount', 'created_at')[:5]
        )
        for o in recent_orders:
            o['uuid']         = str(o['uuid'])
            o['created_at']   = o['created_at'].isoformat()
            o['total_amount'] = str(o['total_amount'])

        return {
            'total_sales':     str(total_sales),
            'orders_count':    all_orders_qs.count(),
            'customers_count': UserSelector.list_all(is_active='true').filter(is_staff=False).count(),
            'products_count':  ProductSelector.list_active().count(),
            'recent_orders':   recent_orders,
            'marketplace':     AdminMetricsOrchestrator._get_marketplace_metrics(),
        }

    @staticmethod
    def _get_marketplace_metrics() -> dict:
        """
        Metricas del marketplace de contratistas + asignacion de tecnicos, mostradas en las
        tarjetas KPI nuevas del dashboard global. professionals_count/technicians disponibles-
        ocupados reusan ContractorAdminSelector.get_metrics() (ya calculado para /panel/profesionales,
        no se duplica la logica). service_status_counts requiere el "ultimo evento por orden" via
        Subquery porque OrderServiceTimeline es un log append-only, no un campo vivo en la orden.
        """
        from accounts.services.selectors import ContractorAdminSelector
        from technical_services.models import OrderServiceTimeline

        professional_metrics = ContractorAdminSelector.get_metrics()

        latest_status_sq = (
            OrderServiceTimeline.objects
            .filter(order=OuterRef('pk'))
            .order_by('-created_at')
            .values('status')[:1]
        )
        service_orders = (
            Order.objects
            .filter(service_detail__isnull=False)
            .annotate(current_status=Subquery(latest_status_sq))
        )
        service_status_counts = dict(
            service_orders.values('current_status')
            .annotate(count=Count('id'))
            .values_list('current_status', 'count')
        )

        top_categories = list(
            service_orders.filter(current_status='completed')
            .exclude(items__service_variant__isnull=True)
            .values(name=F('items__service_variant__service__category__name'))
            .annotate(count=Count('id', distinct=True))
            .order_by('-count')[:5]
        )

        from accounts.models import UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        top_professionals = list(
            UserProfile.objects.filter(
                is_deleted=False, user_type__in=SERVICE_PROVIDER_TYPES,
            )
            .annotate(
                completed_count=Count(
                    'user__assigned_services',
                    filter=Q(user__assigned_services__order__status=Order.STATUS_COMPLETED),
                    distinct=True,
                )
            )
            .filter(completed_count__gt=0)
            .order_by('-completed_count')[:5]
            .values('uuid', 'first_name', 'last_name', 'user__email', 'completed_count')
        )
        for p in top_professionals:
            p['uuid'] = str(p['uuid'])

        return {
            'professionals_count': professional_metrics['total'],
            'professionals_by_type': professional_metrics['by_type'],
            'technicians_available': professional_metrics['available_count'],
            'technicians_busy': professional_metrics['unavailable_count'],
            'average_rating': professional_metrics['average_rating'],
            'service_status_counts': service_status_counts,
            'top_categories': top_categories,
            'top_professionals': top_professionals,
        }


class SupportAdminOrchestrator:

    @staticmethod
    def list_active_rooms():
        from support.services.selectors import ChatSelector
        return ChatSelector.get_active_rooms()

    @staticmethod
    def list_tickets(*, status=None, priority=None, assigned_to_me=None, request_user=None):
        """2026-09-16: vista dedicada de tickets -- SupportTicketSelector.
        list_for_admin() ya existia (con tests reales desde la mision del
        modelo SupportTicket) pero nunca estuvo conectado a ningun endpoint.
        `assigned_to_me` traduce a assigned_admin_id=request_user.id -- el
        selector real no conoce el concepto de "usuario actual", eso es
        responsabilidad de esta capa (orquestador), no de la de datos."""
        from support.services.selectors import SupportTicketSelector
        assigned_admin_id = request_user.id if assigned_to_me and request_user else None
        return SupportTicketSelector.list_for_admin(
            status=status, priority=priority, assigned_admin_id=assigned_admin_id,
        )

    @staticmethod
    def get_room(uuid):
        from support.services.selectors import ChatSelector
        return ChatSelector.get_room_by_uuid(uuid)

    @staticmethod
    def get_room_history(room):
        from support.services.selectors import ChatSelector
        return ChatSelector.get_room_history(room)

    @staticmethod
    def close_room(room):
        from support.services.commands import ChatCommands, SupportTicketCommands
        from support.models import SupportTicket
        from support.services.selectors import SupportTicketSelector
        room = ChatCommands.close_room(room)
        # El ticket (objeto de trabajo) se cierra junto con la conversacion -- v1 no
        # separa ambos ciclos de vida; si mas adelante se necesita reabrir la
        # conversacion sin reabrir el ticket (o viceversa), eso es una decision de
        # producto nueva, no algo que se anticipe aca.
        ticket = SupportTicketSelector.get_by_chat_room(room)
        if ticket and ticket.status not in (SupportTicket.STATUS_CLOSED, SupportTicket.STATUS_CANCELLED):
            SupportTicketCommands.change_status(ticket, SupportTicket.STATUS_CLOSED)
        return room

    @staticmethod
    def assign_admin(room, admin):
        from support.services.commands import ChatCommands, SupportTicketCommands
        from support.services.selectors import SupportTicketSelector
        room = ChatCommands.assign_admin(room, admin)
        ticket = SupportTicketSelector.get_by_chat_room(room)
        if ticket:
            SupportTicketCommands.assign_ticket(ticket, admin)
        return room

    @staticmethod
    def set_ticket_status(room, status: str):
        from support.services.commands import SupportTicketCommands
        from support.services.selectors import SupportTicketSelector
        ticket = SupportTicketSelector.get_by_chat_room(room)
        if ticket is None:
            return None
        return SupportTicketCommands.change_status(ticket, status)

    @staticmethod
    def set_ticket_priority(room, priority: str):
        from support.services.commands import SupportTicketCommands
        from support.services.selectors import SupportTicketSelector
        ticket = SupportTicketSelector.get_by_chat_room(room)
        if ticket is None:
            return None
        return SupportTicketCommands.set_priority(ticket, priority)

    @staticmethod
    def mark_read(room, reader):
        from support.services.commands import ChatCommands
        ChatCommands.mark_messages_read(room, reader)

    @staticmethod
    def attach_context(room, context_type, order_uuid=None, rental_uuid=None, added_by=None):
        from support.models import ChatRoomContext
        from support.services.commands import ChatCommands
        order = None
        rental_request = None
        if context_type == ChatRoomContext.CONTEXT_ORDER and order_uuid:
            from orders.models import Order
            order = Order.objects.filter(uuid=order_uuid, is_deleted=False).first()
        elif context_type == ChatRoomContext.CONTEXT_RENTAL and rental_uuid:
            from renting.models import RentalRequest
            rental_request = RentalRequest.objects.filter(uuid=rental_uuid, is_deleted=False).first()
        return ChatCommands.attach_context(room, context_type, order=order, rental_request=rental_request, added_by=added_by)

    @staticmethod
    def customer_360(user_uuid):
        from django.shortcuts import get_object_or_404
        from users.models import User
        from support.services.customer360 import Customer360Selector
        user = get_object_or_404(User, uuid=user_uuid, is_deleted=False)
        return Customer360Selector.build(user)

    @staticmethod
    def get_analytics_summary(days: int = 30) -> dict:
        # Fase 9 AI Core (Aprendizaje): resumen de conversaciones/telemetria IA
        # para el panel de analytics del Dashboard.
        from support.services.selectors import ChatAnalyticsSelector
        return ChatAnalyticsSelector.get_summary(days=days)


class SecurityAdminOrchestrator:

    @staticmethod
    def list_events(event_type=None, severity=None, user_uuid=None):
        from security.services.selectors import SecuritySelector
        return SecuritySelector.list_events(event_type=event_type, severity=severity, user_uuid=user_uuid)

    @staticmethod
    def get_health():
        from security.services.selectors import SecuritySelector
        return SecuritySelector.get_health_snapshot()


class NotificationAdminOrchestrator:

    @staticmethod
    def list_templates():
        from notifications.services.selectors import NotificationSelector
        return NotificationSelector.list_templates()

    @staticmethod
    def update_template(template_uuid, data):
        from notifications.services.selectors import NotificationSelector
        from notifications.services.commands import NotificationTemplateCommands
        template = NotificationSelector.get_template_by_uuid(template_uuid)
        if template is None:
            return None
        return NotificationTemplateCommands.update_template(template, data)

    @staticmethod
    def list_logs(status=None, channel=None, template_slug=None, user_uuid=None):
        from notifications.services.selectors import NotificationSelector
        return NotificationSelector.list_logs(
            status=status, channel=channel, template_slug=template_slug, user_uuid=user_uuid,
        )


class PaymentAdminOrchestrator:

    @staticmethod
    def list_wompi_transactions(status=None):
        from payment.services.selectors import PaymentAdminSelector
        return PaymentAdminSelector.list_wompi_transactions(status=status)

    @staticmethod
    def list_nequi_transactions(status=None):
        from payment.services.selectors import PaymentAdminSelector
        return PaymentAdminSelector.list_nequi_transactions(status=status)

    @staticmethod
    def list_cod_transactions(status=None):
        from payment.services.selectors import PaymentAdminSelector
        return PaymentAdminSelector.list_cod_transactions(status=status)

    @staticmethod
    def resync_wompi_transaction(transaction_uuid):
        """ADR-001 Fase 7: boton "Reconciliar ahora" del panel admin. Reusa
        _sync_wompi_status (mismo camino que /payment/result y la tarea
        periodica de Fase 6) -- no-op si la transaccion no tiene wompi_id,
        el caller (vista) decide como comunicar eso."""
        from payment.services.selectors import PaymentAdminSelector
        from payment.online.api.views import _sync_wompi_status
        tx = PaymentAdminSelector.get_wompi_transaction(transaction_uuid)
        if tx.status == 'PENDING' and tx.wompi_id:
            _sync_wompi_status(tx)
            tx.refresh_from_db()
        return tx

    @staticmethod
    def list_transaction_events(transaction_uuid):
        from payment.services.selectors import PaymentAdminSelector
        PaymentAdminSelector.get_wompi_transaction(transaction_uuid)  # 404 real si no existe la transaccion
        return PaymentAdminSelector.list_transaction_events(transaction_uuid)

    @staticmethod
    def get_feature_flags():
        from payment.models import PaymentFeatureFlags
        return PaymentFeatureFlags.get_active()

    @staticmethod
    def set_card_api_flow_enabled(enabled: bool):
        from payment.models import PaymentFeatureFlags
        return PaymentFeatureFlags.set_card_api_flow_enabled(enabled)

    @staticmethod
    def set_widget_flow_enabled(enabled: bool):
        from payment.models import PaymentFeatureFlags
        return PaymentFeatureFlags.set_widget_flow_enabled(enabled)


class AIProviderAdminOrchestrator:
    """Plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES PARA CHAT SUPPORT",
    FASE 3 (2026-08-13). /panel/soporte -> AI Providers/Models/Channel Config."""

    @staticmethod
    def list_providers():
        from ai_provider.services.selectors import AIProviderSelector
        return AIProviderSelector.list_providers()

    @staticmethod
    def get_provider(uuid):
        from ai_provider.services.selectors import AIProviderSelector
        return AIProviderSelector.get_provider(uuid)

    @staticmethod
    def create_provider(data, user=None):
        from ai_provider.services.commands import AIProviderCommands
        return AIProviderCommands.create_provider(data, user=user)

    @staticmethod
    def update_provider(uuid, data, user=None):
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return AIProviderCommands.update_provider(provider, data, user=user)

    @staticmethod
    def delete_provider(uuid, user=None):
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        AIProviderCommands.delete_provider(provider, user=user)

    @staticmethod
    def activate_provider(uuid, user=None):
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return AIProviderCommands.activate(provider, user=user)

    @staticmethod
    def deactivate_provider(uuid, user=None):
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return AIProviderCommands.deactivate(provider, user=user)

    @staticmethod
    def set_default_provider(uuid, user=None):
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return AIProviderCommands.set_default(provider, user=user)

    @staticmethod
    def test_connection(uuid, user=None):
        """Intenta una llamada real minima al proveedor (nunca una generacion completa)
        y persiste el resultado -- boton "Probar conexion" del panel. FASE 11 (plan "AI
        Provider Runtime"): delega en AIProviderConnectionTestService (adapters), con
        codigo de error categorizado (DNS/CONNECTION_REFUSED/TIMEOUT/UNAUTHORIZED/...)."""
        from ai_provider.services.commands import AIProviderCommands
        from ai_provider.services.selectors import AIProviderSelector
        from ai_provider.services.connection_test import AIProviderConnectionTestService
        provider = AIProviderSelector.get_provider(uuid)
        result = AIProviderConnectionTestService.test(provider)
        return AIProviderCommands.record_test_result(
            provider, ok=result.success, latency_ms=result.latency_ms,
            error=result.error_message_safe if not result.success else '', user=user,
        )

    @staticmethod
    def discover_models(uuid):
        """Lista de nombres de modelo disponibles en el proveedor real (Ollama: GET
        /api/tags; openai-compatible: GET /models). No los agrega automaticamente --
        el admin elige cuales agregar (accion separada `add_model`)."""
        from ai_provider.services.selectors import AIProviderSelector
        from ai_provider.services.model_discovery import discover_models
        provider = AIProviderSelector.get_provider(uuid)
        return discover_models(provider)

    @staticmethod
    def add_model(provider_uuid, model_id, display_name='', user=None):
        from ai_provider.services.commands import AIModelCommands
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(provider_uuid)
        return AIModelCommands.add_model(provider, model_id, display_name=display_name, user=user)

    @staticmethod
    def delete_model(uuid, user=None):
        from ai_provider.services.commands import AIModelCommands
        from ai_provider.services.selectors import AIModelSelector
        model = AIModelSelector.get(uuid)
        AIModelCommands.delete_model(model, user=user)

    @staticmethod
    def get_channel_config(channel='support_chat'):
        from ai_provider.services.selectors import AIChannelConfigSelector
        return AIChannelConfigSelector.get_or_create_config(channel)

    @staticmethod
    def channel_history(channel='support_chat'):
        from ai_provider.models import AIConfigRevision
        from ai_provider.services import revisions
        from ai_provider.services.selectors import AIChannelConfigSelector
        config = AIChannelConfigSelector.get_or_create_config(channel)
        return revisions.list_history(AIConfigRevision.SCOPE_CHANNEL, config.uuid)

    @staticmethod
    def rollback_channel(version, user, channel='support_chat'):
        from ai_provider.services import revisions
        from ai_provider.services.selectors import AIChannelConfigSelector
        config = AIChannelConfigSelector.get_or_create_config(channel)
        return revisions.rollback_channel(config, int(version), user=user)

    @staticmethod
    def provider_history(uuid):
        from ai_provider.models import AIConfigRevision
        from ai_provider.services import revisions
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return revisions.list_history(AIConfigRevision.SCOPE_PROVIDER, provider.uuid)

    @staticmethod
    def rollback_provider(uuid, version, user):
        from ai_provider.services import revisions
        from ai_provider.services.selectors import AIProviderSelector
        provider = AIProviderSelector.get_provider(uuid)
        return revisions.rollback_provider(provider, int(version), user=user)

    @staticmethod
    def validate_model(model_uuid):
        """Dry-run "Probar antes de activar": mismos chequeos que set_primary_model, sin persistir nada. Lanza ActivationCheckFailed."""
        from ai_provider.services.activation import validate_model_for_activation
        from ai_provider.services.selectors import AIModelSelector
        return validate_model_for_activation(AIModelSelector.get(model_uuid))

    @staticmethod
    def set_primary_model(model_uuid, user, channel='support_chat', force=False):
        """PLAN_LLMDINAMICO sec. 7: un primario nuevo se valida (proveedor activo, conectividad, modelo disponible) ANTES de persistir.
        `force=True` omite la validacion (accion explicita). Quitar el primario (model_uuid vacio) no requiere validacion."""
        from ai_provider.services.activation import validate_model_for_activation
        from ai_provider.services.commands import AIChannelConfigCommands
        from ai_provider.services.selectors import AIChannelConfigSelector, AIModelSelector
        config = AIChannelConfigSelector.get_or_create_config(channel)
        model = AIModelSelector.get(model_uuid) if model_uuid else None
        if model is not None and not force:
            validate_model_for_activation(model)
        return AIChannelConfigCommands.set_primary(config, model, user=user)

    @staticmethod
    def set_fallback_chain(model_uuids, user, channel='support_chat'):
        from ai_provider.services.commands import AIChannelConfigCommands
        from ai_provider.services.selectors import AIChannelConfigSelector, AIModelSelector
        config = AIChannelConfigSelector.get_or_create_config(channel)
        models = [AIModelSelector.get(u) for u in model_uuids]
        return AIChannelConfigCommands.set_fallback_chain(config, models, user=user)

