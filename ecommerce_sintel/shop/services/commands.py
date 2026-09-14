import uuid as _uuid
import logging

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from inventory.models import StockRecord
from inventory.services.commands import InventoryCommands
from inventory.services.dtos import StockAdjustmentDTO
from shop.models import ProductReview, Product, ProductVariant, Category, Brand, Tax, ProductImage

logger = logging.getLogger(__name__)


def _generate_variant_sku(product: Product) -> str:
    """Genera un SKU legible y unico sin depender de entrada del usuario."""
    base = ''.join(ch for ch in product.slug.upper() if ch.isalnum())[:18] or "PROD"
    for _ in range(10):
        candidate = f"{base}-{_uuid.uuid4().hex[:6].upper()}"
        if not ProductVariant.objects.filter(sku=candidate).exists():
            return candidate
    return f"SKU-{_uuid.uuid4().hex.upper()}"


def _get_or_create_stock_record(variant: ProductVariant) -> StockRecord:
    content_type = ContentType.objects.get_for_model(ProductVariant)
    stock_record, created = StockRecord.objects.get_or_create(
        content_type=content_type,
        object_id=variant.uuid,
        defaults={
            'sku': variant.sku,
            'stock': 0,
            'is_active': True,
            'is_deleted': False,
        },
    )
    if not created and stock_record.sku != variant.sku:
        stock_record.sku = variant.sku
        stock_record.save(update_fields=['sku', 'updated_at'])
    return stock_record


def _sync_variant_stock(variant: ProductVariant, target_stock: int, reference: str) -> ProductVariant:
    target_stock = int(target_stock or 0)
    stock_record = _get_or_create_stock_record(variant)
    delta = target_stock - stock_record.stock
    if delta > 0:
        InventoryCommands.register_entry(StockAdjustmentDTO(
            stock_record_uuid=stock_record.uuid,
            quantity=delta,
            reference=reference,
        ))
    elif delta < 0:
        InventoryCommands.register_exit(StockAdjustmentDTO(
            stock_record_uuid=stock_record.uuid,
            quantity=abs(delta),
            reference=reference,
        ))
    stock_record.refresh_from_db()
    if variant.stock != stock_record.stock:
        variant.stock = stock_record.stock
        variant.save(update_fields=['stock', 'updated_at'])
    return variant


class ProductVariantCommands:

    @staticmethod
    @transaction.atomic
    def create_variant(
        product: Product,
        price,
        discounted_price=None,
        is_default: bool = False,
        stock: int = 0,
        attributes: dict = None,
        discount_start_date=None,
        discount_end_date=None,
        weight=None,
        length=None,
        width=None,
        height=None,
    ) -> ProductVariant:
        """Crea una variante adicional para un producto existente."""
        if is_default:
            product.variants.filter(is_deleted=False, is_default=True).update(is_default=False)
        variant = ProductVariant.objects.create(
            product=product,
            sku=_generate_variant_sku(product),
            price=price,
            discounted_price=discounted_price,
            is_default=is_default,
            stock=0,
            attributes=attributes or {},
            discount_start_date=discount_start_date,
            discount_end_date=discount_end_date,
            weight=weight,
            length=length,
            width=width,
            height=height,
        )
        return _sync_variant_stock(
            variant,
            stock,
            reference=f"Initial stock for variant {variant.sku}",
        )

    @staticmethod
    @transaction.atomic
    def update_variant(variant: ProductVariant, data: dict) -> ProductVariant:
        """
        Actualiza campos de una variante.
        Acepta: price, discounted_price, stock, is_default,
                attributes, discount_start_date, discount_end_date.
        """
        ALLOWED_FIELDS = {
            'price', 'discounted_price', 'is_default',
            'attributes', 'discount_start_date', 'discount_end_date',
            'weight', 'length', 'width', 'height',
        }
        target_stock = data.pop('stock', None)
        if data.get('is_default') and not variant.is_default:
            variant.product.variants.filter(is_deleted=False, is_default=True).update(is_default=False)
        for field, value in data.items():
            if field in ALLOWED_FIELDS:
                setattr(variant, field, value)
        variant.save()
        if target_stock is not None:
            variant = _sync_variant_stock(
                variant,
                target_stock,
                reference=f"Stock update for variant {variant.sku}",
            )
        return variant

    @staticmethod
    @transaction.atomic
    def delete_variant(variant: ProductVariant) -> None:
        """Soft-delete de variante via is_deleted=True."""
        variant.is_deleted = True
        variant.save(update_fields=['is_deleted', 'updated_at'])


class ProductReviewCommands:
    @staticmethod
    @transaction.atomic
    def create_review(user, product: Product, rating: int, comment: str) -> ProductReview:
        """
        Crea una resena para un producto.

        [CORREGIDO 2026-08-06] Antes cualquier usuario autenticado podia resenar
        cualquier producto, sin haberlo comprado -- unica diferencia real entre
        los 3 dominios de resenas de catalogo, encontrada en la evaluacion de
        Sprint 6 (PLAN_SPRINT6_EVALUACION_2026-08-05.md #1.2): Renting exige
        `RentalRequest.STATUS_FINISHED`, Services exige `ServiceOperation.CLOSED`,
        Shop no exigia nada. Se cierra la brecha con el mismo criterio (estado
        terminal, no solo "pagado"): el usuario debe tener una Order con este
        producto en status `STATUS_DELIVERED`. `is_verified_purchase` (campo que
        existia pero nunca se seteaba en `True` en ningun lugar del codigo) ahora
        se marca `True` siempre -- el gate de abajo lo garantiza.
        """
        from orders.models import Order

        has_delivered_order = Order.objects.filter(
            user=user,
            items__variant__product=product,
            status=Order.STATUS_DELIVERED,
        ).exists()
        if not has_delivered_order:
            raise ValueError(
                'Solo puedes resenar productos que ya hayas comprado y recibido.'
            )

        return ProductReview.objects.create(
            user=user,
            product=product,
            rating=rating,
            comment=comment,
            is_verified_purchase=True,
        )


class ProductCommands:

    PRODUCT_ALLOWED_FIELDS = {
        'name', 'short_description', 'description', 'video_url', 'scope', 'warranty',
        'condition', 'is_active', 'is_featured',
        'category', 'brand', 'meta_title', 'meta_description',
    }

    @staticmethod
    @transaction.atomic
    def create_product(
        vendor,
        category,
        name: str,
        price,
        condition: str = Product.Condition.NEW,
        short_description: str = None,
        description: str = "",
        video_url: str = None,
        scope: str = "",
        warranty: str = "",
        brand=None,
        is_active: bool = True,
        is_featured: bool = False,
        stock: int = 0,
        discounted_price=None,
        meta_title: str = "",
        meta_description: str = "",
    ) -> Product:
        """
        Crea un producto y su variante por defecto.
        Retorna el Product recien creado.
        """
        product = Product.objects.create(
            vendor=vendor,
            category=category,
            brand=brand,
            name=name,
            condition=condition,
            short_description=short_description,
            description=description,
            video_url=video_url,
            scope=scope,
            warranty=warranty,
            is_active=is_active,
            is_featured=is_featured,
            meta_title=meta_title,
            meta_description=meta_description,
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=_generate_variant_sku(product),
            price=price,
            discounted_price=discounted_price,
            is_default=True,
            stock=0,
        )
        _sync_variant_stock(
            variant,
            stock,
            reference=f"Initial stock for product {product.uuid}",
        )
        return product

    @staticmethod
    @transaction.atomic
    def update_product(product: Product, data: dict) -> Product:
        """Actualiza campos de un producto. Solo campos explicitamente permitidos."""
        variant_data = {
            field: data.pop(field)
            for field in ('price', 'discounted_price', 'stock')
            if field in data
        }
        for field, value in data.items():
            if field in ProductCommands.PRODUCT_ALLOWED_FIELDS:
                setattr(product, field, value)
        product.save()
        if variant_data:
            variant = (
                product.variants
                .filter(is_deleted=False, is_default=True)
                .first()
                or product.variants.filter(is_deleted=False).first()
            )
            if variant:
                ProductVariantCommands.update_variant(variant, variant_data)
        return product

    @staticmethod
    @transaction.atomic
    def delete_product(product: Product) -> None:
        """Soft-delete de producto: oculto de todas las vistas publicas y admin."""
        product.is_active = False
        product.is_deleted = True
        product.save(update_fields=['is_active', 'is_deleted', 'updated_at'])


class CategoryCommands:

    CATEGORY_ALLOWED_FIELDS = {
        'name', 'description', 'parent', 'is_active',
        'meta_title', 'meta_description', 'image',
    }

    @staticmethod
    @transaction.atomic
    def create_category(
        name: str,
        description: str = "",
        parent=None,
        is_active: bool = True,
        image=None,
        meta_title: str = "",
        meta_description: str = "",
    ) -> Category:
        """Crea una nueva categoria."""
        return Category.objects.create(
            name=name,
            description=description,
            parent=parent,
            is_active=is_active,
            image=image,
            meta_title=meta_title,
            meta_description=meta_description,
        )

    @staticmethod
    @transaction.atomic
    def update_category(category: Category, data: dict) -> Category:
        """Actualiza campos de una categoria."""
        for field, value in data.items():
            if field in CategoryCommands.CATEGORY_ALLOWED_FIELDS:
                setattr(category, field, value)
        category.save()
        return category

    @staticmethod
    @transaction.atomic
    def delete_category(category: Category) -> None:
        """
        Soft-delete estricto de categoria.
        Establece is_active=False e is_deleted=True. Nunca borra fisicamente.
        """
        category.is_active = False
        category.is_deleted = True
        category.save(update_fields=['is_active', 'is_deleted', 'updated_at'])


class BrandCommands:

    @staticmethod
    @transaction.atomic
    def create_brand(name: str, logo=None, is_active: bool = True) -> Brand:
        """Crea una nueva marca."""
        return Brand.objects.create(name=name, logo=logo, is_active=is_active)

    @staticmethod
    @transaction.atomic
    def update_brand(brand: Brand, data: dict) -> Brand:
        """Actualiza campos de una marca (name, logo, is_active)."""
        for field, value in data.items():
            if field in ['name', 'logo', 'is_active']:
                setattr(brand, field, value)
        brand.save()
        return brand

    @staticmethod
    @transaction.atomic
    def delete_brand(brand: Brand) -> None:
        """
        Soft-delete estricto de marca.
        Establece is_active=False e is_deleted=True. Nunca borra fisicamente.
        """
        brand.is_active = False
        brand.is_deleted = True
        brand.save(update_fields=['is_active', 'is_deleted', 'updated_at'])


class TaxCommands:

    @staticmethod
    @transaction.atomic
    def create_tax(name: str, tax_type: str, value, is_active: bool = True) -> Tax:
        return Tax.objects.create(
            name=name,
            tax_type=tax_type,
            value=value,
            is_active=is_active
        )

    @staticmethod
    @transaction.atomic
    def update_tax(tax: Tax, data: dict) -> Tax:
        for field, value in data.items():
            if field in ['name', 'tax_type', 'value', 'is_active']:
                setattr(tax, field, value)
        tax.save()
        return tax

    @staticmethod
    @transaction.atomic
    def delete_tax(tax: Tax) -> None:
        """Soft-delete de impuesto via is_active=False e is_deleted=True."""
        tax.is_active = False
        tax.is_deleted = True
        tax.save(update_fields=['is_active', 'is_deleted', 'updated_at'])


class ProductImageCommands:
    """Commands for managing product images. Extracted from dashboard/api/views.py (Sprint 3)."""

    @staticmethod
    @transaction.atomic
    def add_image(product, image_file, alt_text: str = '', is_primary: bool = False):
        """Upload and attach an image to a product. If is_primary, demotes all others first."""
        if is_primary:
            ProductImage.objects.filter(product=product).update(is_primary=False)
        img = ProductImage.objects.create(
            product=product,
            image=image_file,
            alt_text=alt_text,
            is_primary=is_primary,
        )
        return img

    @staticmethod
    @transaction.atomic
    def delete_image(product, image_uuid):
        """Delete a product image by uuid. Raises ProductImage.DoesNotExist if not found."""
        img = ProductImage.objects.get(uuid=image_uuid, product=product)
        img.delete()

    @staticmethod
    @transaction.atomic
    def set_primary_image(product, image_uuid):
        """Mark one image as primary, demoting all others. Returns the updated image."""
        img = ProductImage.objects.get(uuid=image_uuid, product=product)
        ProductImage.objects.filter(product=product).update(is_primary=False)
        img.is_primary = True
        img.save(update_fields=['is_primary'])
        return img
