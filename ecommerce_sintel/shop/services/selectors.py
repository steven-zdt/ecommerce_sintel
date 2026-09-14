from django.db.models import Prefetch, QuerySet, Avg, Count, Sum, Value, IntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from shop.models import (
    Product, ProductVariant, Category, Brand, ProductReview, Tax,
    ProductFeature, ProductIncludedItem, ProductExcludedItem,
    ProductSpecificationGroup, ProductSpecification, ProductRequirement,
    ProductServiceIncluded, ProductOptionalService, ProductFAQ,
    ProductVideo, ProductDocument, ProductFunctioningStep,
)

# 'is_active' incluido para que el panel de admin pueda filtrar/mostrar estado sin redefinir campos.
PRODUCT_LIST_FIELDS = ('id', 'uuid', 'name', 'slug', 'condition', 'category_id', 'brand_id', 'is_featured', 'is_active', 'meta_title', 'meta_description')
PRODUCT_DETAIL_FIELDS = PRODUCT_LIST_FIELDS + ('description', 'created_at')
ADMIN_LIST_FIELDS = PRODUCT_LIST_FIELDS + ('created_at',)

# INVENTORY_REMOVED: from inventory.services.selectors import InventorySelector  # -> usar /api/v1/inventory/ o signal

class ProductSelector:

    @staticmethod
    def _get_detail_queryset() -> QuerySet:
        """QuerySet base para detalle de producto: anotaciones + prefetches completos.

        Incluye el catalogo enriquecido (2026-08-03, espejo de RentingSelector.get_by_uuid)
        via Prefetch filtrado (is_deleted=False) para que ProductDetailSerializer no dispare
        queries N+1 adicionales al recorrer estas relaciones. is_active se filtra en el
        serializer (el admin necesita ver filas inactivas para poder reactivarlas).
        """
        return (
            Product.objects
            .select_related('category', 'brand')
            .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
            .prefetch_related(
                'variants', 'images', 'reviews__user', 'variants__images',
                Prefetch('features', queryset=ProductFeature.objects.filter(is_deleted=False)),
                Prefetch('included_items', queryset=ProductIncludedItem.objects.filter(is_deleted=False)),
                Prefetch('excluded_items', queryset=ProductExcludedItem.objects.filter(is_deleted=False)),
                Prefetch('specification_groups', queryset=ProductSpecificationGroup.objects.filter(is_deleted=False)),
                Prefetch(
                    'specification_groups__specifications',
                    queryset=ProductSpecification.objects.filter(is_deleted=False),
                ),
                Prefetch('requirements', queryset=ProductRequirement.objects.filter(is_deleted=False)),
                Prefetch('services_included', queryset=ProductServiceIncluded.objects.filter(is_deleted=False)),
                Prefetch('optional_services', queryset=ProductOptionalService.objects.filter(is_deleted=False)),
                Prefetch('faqs', queryset=ProductFAQ.objects.filter(is_deleted=False)),
                Prefetch('videos', queryset=ProductVideo.objects.filter(is_deleted=False)),
                Prefetch('documents', queryset=ProductDocument.objects.filter(is_deleted=False)),
                Prefetch('functioning_steps', queryset=ProductFunctioningStep.objects.filter(is_deleted=False)),
            )
        )

    @staticmethod
    def list_active() -> QuerySet:
        """Listado publico de productos activos, optimizado para el catalogo."""
        return (
            Product.objects.filter(is_active=True)
            .select_related('category', 'brand')
            .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
            .prefetch_related('variants', 'images', 'variants__images')
        )

    @staticmethod
    def list_featured() -> QuerySet:
        """Productos activos marcados como destacados para la Home publica, ordenados por unidades vendidas."""
        return (
            Product.objects.filter(is_active=True, is_featured=True)
            .select_related('category', 'brand')
            .prefetch_related('variants', 'images', 'variants__images')
            .annotate(
                total_sold=Coalesce(
                    Sum('variants__orderitem__quantity'),
                    Value(0),
                    output_field=IntegerField(),
                )
            )
            .order_by('-total_sold', '-created_at')
        )

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        """Listado para el panel de administrador. Excluye productos borrados (is_deleted=True).
        Incluye activos e inactivos para que el admin pueda ver el estado completo.
        """
        return (
            Product.objects.filter(is_deleted=False)
            .select_related('category', 'brand')
            .prefetch_related('variants', 'images', 'variants__images')
            .annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews'))
            .order_by('-created_at')
        )

    @staticmethod
    def get_by_slug(slug: str) -> Product:
        """Retorna un producto detallado por su slug. Lanza Http404 si no existe o esta inactivo."""
        return get_object_or_404(ProductSelector._get_detail_queryset(), slug=slug, is_active=True)

    @staticmethod
    def get_by_uuid(product_uuid: str) -> Product:
        """Retorna un producto detallado por su UUID. No filtra por is_active (uso interno/admin)."""
        return get_object_or_404(ProductSelector._get_detail_queryset(), uuid=product_uuid)

    @staticmethod
    def get_by_id(product_id: int) -> Product:
        """Retorna un producto detallado por su ID. No filtra por is_active (uso interno/admin/panel)."""
        return get_object_or_404(ProductSelector._get_detail_queryset(), id=product_id)


class CategorySelector:
    # Campos expuestos al frontend Vue para listado y detalle
    LIST_FIELDS = ('id', 'uuid', 'name', 'slug', 'description', 'image', 'parent_id', 'is_active', 'meta_title', 'meta_description')

    @staticmethod
    def list_all() -> QuerySet:
        return (
            Category.objects.filter(is_active=True)
            .only(*CategorySelector.LIST_FIELDS)
            .select_related('parent')
        )

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        return (
            Category.objects.filter(is_deleted=False)
            .only(*CategorySelector.LIST_FIELDS)
            .select_related('parent')
        )

    @staticmethod
    def get_by_uuid(category_uuid: str) -> Category:
        return get_object_or_404(Category, uuid=category_uuid)

    @staticmethod
    def get_by_id(category_id: int) -> Category:
        return get_object_or_404(Category, id=category_id)


class BrandSelector:
    @staticmethod
    def list_all() -> QuerySet:
        """Listado publico: solo marcas activas y no eliminadas."""
        return Brand.objects.filter(is_active=True, is_deleted=False).only('id', 'uuid', 'name', 'slug', 'logo', 'is_active')

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        """Listado admin: todas las marcas no eliminadas fisicamente."""
        return Brand.objects.filter(is_deleted=False).only('id', 'uuid', 'name', 'slug', 'logo', 'is_active')

    @staticmethod
    def get_by_slug(slug: str) -> Brand:
        return get_object_or_404(Brand, slug=slug, is_deleted=False)

    @staticmethod
    def get_by_uuid(brand_uuid: str) -> Brand:
        return get_object_or_404(Brand, uuid=brand_uuid, is_deleted=False)


class ProductVariantSelector:

    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        """Variantes activas (no eliminadas) de un producto, ordenadas: default primero."""
        return (
            ProductVariant.objects
            .filter(product__uuid=product_uuid, is_deleted=False)
            .prefetch_related('images')
            .order_by('-is_default', 'created_at')
        )

    @staticmethod
    def get_by_uuid(variant_uuid: str) -> ProductVariant:
        return get_object_or_404(ProductVariant, uuid=variant_uuid, is_deleted=False)


class TaxSelector:
    @staticmethod
    def list_active() -> QuerySet:
        return Tax.objects.filter(is_active=True)

    @staticmethod
    def list_all() -> QuerySet:
        return Tax.objects.all()

    @staticmethod
    def get_by_uuid(tax_uuid: str) -> Tax:
        return get_object_or_404(Tax, uuid=tax_uuid)
