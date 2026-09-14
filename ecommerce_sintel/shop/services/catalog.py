"""
shop/services/catalog.py

Service layer para el catalogo enriquecido de Product (2026-08-03), espejo de
renting/services/catalog.py (renting.Equipment, migracion 0022_catalog_detail_models,
2026-07-16): ProductIncludedItem, ProductExcludedItem, ProductFeature,
ProductSpecificationGroup, ProductSpecification, ProductRequirement,
ProductServiceIncluded, ProductOptionalService, ProductFAQ, ProductVideo, ProductDocument.

Todos comparten el mismo shape operativo (fila hija de Product, con
position/is_active/is_deleted), asi que reorder/toggle_active/duplicate se
factorizan en helpers de modulo -- cada modelo sigue teniendo su propio
Selector y su propio Commands (un servicio por modelo, sin CRUD generico
expuesto), solo el cuerpo interno se comparte para no repetir la misma
logica 11 veces.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet

from shop.models import (
    Product, ProductImage,
    ProductIncludedItem, ProductExcludedItem, ProductFeature,
    ProductSpecificationGroup, ProductSpecification, ProductRequirement,
    ProductServiceIncluded, ProductOptionalService, ProductFAQ,
    ProductVideo, ProductDocument, ProductFunctioningStep,
)


def _reorder(model, ordered_uuids: list, field_name: str = 'position', **scope) -> None:
    """
    Reasigna el campo de orden (0..n) segun el orden de `ordered_uuids` (drag&drop).
    `field_name` es parametrizable porque `ProductImage` usa `display_order`, no
    `position` como el resto de los modelos del catalogo enriquecido.
    """
    items = {
        str(item.uuid): item
        for item in model.objects.filter(is_deleted=False, **scope)
    }
    with transaction.atomic():
        for position, item_uuid in enumerate(ordered_uuids):
            item = items.get(str(item_uuid))
            if item is not None and getattr(item, field_name) != position:
                setattr(item, field_name, position)
                item.save(update_fields=[field_name, 'updated_at'])


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


# ── ProductImage (galeria con tipo) ────────────────────────────────────────────

class ProductImageSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductImage.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductImage:
        return get_object_or_404(ProductImage, uuid=uuid, is_deleted=False)


class ProductImageCommands:
    @staticmethod
    @transaction.atomic
    def create(product: Product, image, image_type: str = ProductImage.TYPE_GALLERY,
               alt_text: str = '', is_primary: bool = False, display_order: int = 0) -> ProductImage:
        if is_primary:
            ProductImage.objects.filter(product=product, is_deleted=False).update(is_primary=False)
        return ProductImage.objects.create(
            product=product, image=image, image_type=image_type,
            alt_text=alt_text, is_primary=is_primary, display_order=display_order,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: ProductImage, **fields) -> ProductImage:
        allowed = ('alt_text', 'image_type', 'display_order')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def set_primary(instance: ProductImage) -> ProductImage:
        ProductImage.objects.filter(product=instance.product, is_deleted=False).update(is_primary=False)
        instance.is_primary = True
        instance.save(update_fields=['is_primary', 'updated_at'])
        return instance

    @staticmethod
    def delete(instance: ProductImage) -> None:
        _soft_delete(instance)

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductImage, ordered_uuids, field_name='display_order', product_id=product_id)


# ── ProductIncludedItem ────────────────────────────────────────────────────────

class ProductIncludedItemSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductIncludedItem.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductIncludedItem:
        return get_object_or_404(ProductIncludedItem, uuid=uuid, is_deleted=False)


class ProductIncludedItemCommands:
    _COPY_FIELDS = ['product_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductIncludedItem:
        return ProductIncludedItem.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductIncludedItem, **fields) -> ProductIncludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductIncludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductIncludedItem) -> ProductIncludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductIncludedItem) -> ProductIncludedItem:
        return _duplicate(instance, ProductIncludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductIncludedItem, ordered_uuids, product_id=product_id)


# ── ProductExcludedItem ────────────────────────────────────────────────────────

class ProductExcludedItemSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductExcludedItem.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductExcludedItem:
        return get_object_or_404(ProductExcludedItem, uuid=uuid, is_deleted=False)


class ProductExcludedItemCommands:
    _COPY_FIELDS = ['product_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductExcludedItem:
        return ProductExcludedItem.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductExcludedItem, **fields) -> ProductExcludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductExcludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductExcludedItem) -> ProductExcludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductExcludedItem) -> ProductExcludedItem:
        return _duplicate(instance, ProductExcludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductExcludedItem, ordered_uuids, product_id=product_id)


# ── ProductFeature ──────────────────────────────────────────────────────────────

class ProductFeatureSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductFeature.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductFeature:
        return get_object_or_404(ProductFeature, uuid=uuid, is_deleted=False)


class ProductFeatureCommands:
    _COPY_FIELDS = ['product_id', 'title', 'value', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductFeature:
        return ProductFeature.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductFeature, **fields) -> ProductFeature:
        allowed = ('title', 'value', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductFeature) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductFeature) -> ProductFeature:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductFeature) -> ProductFeature:
        return _duplicate(instance, ProductFeatureCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductFeature, ordered_uuids, product_id=product_id)


# ── ProductSpecificationGroup / ProductSpecification ──────────────────────────

class ProductSpecificationGroupSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return (
            ProductSpecificationGroup.objects
            .filter(product__uuid=product_uuid, is_deleted=False)
            .prefetch_related('specifications')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductSpecificationGroup:
        return get_object_or_404(ProductSpecificationGroup, uuid=uuid, is_deleted=False)


class ProductSpecificationGroupCommands:
    _COPY_FIELDS = ['product_id', 'name', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductSpecificationGroup:
        return ProductSpecificationGroup.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductSpecificationGroup, **fields) -> ProductSpecificationGroup:
        allowed = ('name', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def delete(instance: ProductSpecificationGroup) -> None:
        _soft_delete(instance)
        ProductSpecification.objects.filter(group=instance, is_deleted=False).update(is_deleted=True)

    @staticmethod
    def toggle_active(instance: ProductSpecificationGroup) -> ProductSpecificationGroup:
        return _toggle_active(instance)

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductSpecificationGroup, ordered_uuids, product_id=product_id)


class ProductSpecificationSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductSpecification.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def list_for_group(group_uuid: str) -> QuerySet:
        return ProductSpecification.objects.filter(group__uuid=group_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductSpecification:
        return get_object_or_404(ProductSpecification, uuid=uuid, is_deleted=False)


class ProductSpecificationCommands:
    _COPY_FIELDS = ['product_id', 'group_id', 'name', 'value', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, group: ProductSpecificationGroup, **fields) -> ProductSpecification:
        if group.product_id != product.id:
            raise ValueError('El grupo de especificaciones no pertenece a este producto.')
        return ProductSpecification.objects.create(product=product, group=group, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductSpecification, **fields) -> ProductSpecification:
        allowed = ('name', 'value', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductSpecification) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductSpecification) -> ProductSpecification:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductSpecification) -> ProductSpecification:
        return _duplicate(instance, ProductSpecificationCommands._COPY_FIELDS, {'name': f'{instance.name} (copia)'})

    @staticmethod
    def reorder(group_id: int, ordered_uuids: list) -> None:
        _reorder(ProductSpecification, ordered_uuids, group_id=group_id)


# ── ProductRequirement ──────────────────────────────────────────────────────────

class ProductRequirementSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductRequirement.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductRequirement:
        return get_object_or_404(ProductRequirement, uuid=uuid, is_deleted=False)


class ProductRequirementCommands:
    _COPY_FIELDS = ['product_id', 'title', 'description', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductRequirement:
        return ProductRequirement.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductRequirement, **fields) -> ProductRequirement:
        allowed = ('title', 'description', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductRequirement) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductRequirement) -> ProductRequirement:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductRequirement) -> ProductRequirement:
        return _duplicate(instance, ProductRequirementCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductRequirement, ordered_uuids, product_id=product_id)


# ── ProductServiceIncluded ──────────────────────────────────────────────────────

class ProductServiceIncludedSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductServiceIncluded.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductServiceIncluded:
        return get_object_or_404(ProductServiceIncluded, uuid=uuid, is_deleted=False)


class ProductServiceIncludedCommands:
    _COPY_FIELDS = ['product_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductServiceIncluded:
        return ProductServiceIncluded.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductServiceIncluded, **fields) -> ProductServiceIncluded:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductServiceIncluded) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductServiceIncluded) -> ProductServiceIncluded:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductServiceIncluded) -> ProductServiceIncluded:
        return _duplicate(instance, ProductServiceIncludedCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductServiceIncluded, ordered_uuids, product_id=product_id)


# ── ProductOptionalService ──────────────────────────────────────────────────────

class ProductOptionalServiceSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductOptionalService.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductOptionalService:
        return get_object_or_404(ProductOptionalService, uuid=uuid, is_deleted=False)


class ProductOptionalServiceCommands:
    _COPY_FIELDS = ['product_id', 'title', 'description', 'price', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductOptionalService:
        return ProductOptionalService.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductOptionalService, **fields) -> ProductOptionalService:
        allowed = ('title', 'description', 'price', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductOptionalService) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductOptionalService) -> ProductOptionalService:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductOptionalService) -> ProductOptionalService:
        return _duplicate(instance, ProductOptionalServiceCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductOptionalService, ordered_uuids, product_id=product_id)


# ── ProductFAQ ───────────────────────────────────────────────────────────────────

class ProductFAQSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductFAQ.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductFAQ:
        return get_object_or_404(ProductFAQ, uuid=uuid, is_deleted=False)


class ProductFAQCommands:
    _COPY_FIELDS = ['product_id', 'question', 'answer', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductFAQ:
        return ProductFAQ.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductFAQ, **fields) -> ProductFAQ:
        allowed = ('question', 'answer', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductFAQ) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductFAQ) -> ProductFAQ:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ProductFAQ) -> ProductFAQ:
        return _duplicate(instance, ProductFAQCommands._COPY_FIELDS, {'question': f'{instance.question} (copia)'})

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductFAQ, ordered_uuids, product_id=product_id)


# ── ProductVideo ─────────────────────────────────────────────────────────────────

class ProductVideoSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductVideo.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductVideo:
        return get_object_or_404(ProductVideo, uuid=uuid, is_deleted=False)


class ProductVideoCommands:
    @staticmethod
    @transaction.atomic
    def create(product: Product, source_type: str, title='', video_url='', video_file=None,
               thumbnail=None, position=0, is_active=True) -> ProductVideo:
        if source_type == ProductVideo.SOURCE_MP4 and not video_file:
            raise ValueError('Debe adjuntar un archivo de video.')
        if source_type in (ProductVideo.SOURCE_YOUTUBE, ProductVideo.SOURCE_VIMEO) and not video_url:
            raise ValueError('Debe indicar la URL del video de YouTube/Vimeo.')
        return ProductVideo.objects.create(
            product=product, source_type=source_type, title=title,
            video_url=video_url, video_file=video_file, thumbnail=thumbnail,
            position=position, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: ProductVideo, **fields) -> ProductVideo:
        allowed = ('title', 'source_type', 'video_url', 'video_file', 'thumbnail', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductVideo) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductVideo) -> ProductVideo:
        return _toggle_active(instance)

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductVideo, ordered_uuids, product_id=product_id)


# ── ProductDocument ──────────────────────────────────────────────────────────────

class ProductDocumentSelector:
    @staticmethod
    def list_for_product(product_uuid: str, public_only: bool = False) -> QuerySet:
        qs = ProductDocument.objects.filter(product__uuid=product_uuid, is_deleted=False)
        if public_only:
            qs = qs.filter(is_public=True, is_active=True)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductDocument:
        return get_object_or_404(ProductDocument, uuid=uuid, is_deleted=False)


class ProductDocumentCommands:
    @staticmethod
    @transaction.atomic
    def create(product: Product, file, title: str, document_type: str, description='',
               version='', language='es', cover_image=None, position=0, is_public=True,
               is_active=True) -> ProductDocument:
        from accounts.services.commands import validate_file

        validate_file(
            file, max_size_mb=50,
            allowed_extensions=['.pdf', '.docx', '.zip', '.xlsx', '.pptx'],
            magic_bytes_check=True,
        )
        return ProductDocument.objects.create(
            product=product, file=file, title=title, document_type=document_type,
            description=description, version=version, language=language,
            cover_image=cover_image, position=position, is_public=is_public, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: ProductDocument, **fields) -> ProductDocument:
        allowed = (
            'title', 'description', 'document_type', 'version', 'language',
            'cover_image', 'position', 'is_public', 'is_active',
        )
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductDocument) -> None:
        _soft_delete(instance)

    @staticmethod
    @transaction.atomic
    def register_download(instance: ProductDocument) -> ProductDocument:
        instance.downloads = instance.downloads + 1
        instance.save(update_fields=['downloads', 'updated_at'])
        return instance

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductDocument, ordered_uuids, product_id=product_id)


# ── ProductFunctioningStep ────────────────────────────────────────────────────────

class ProductFunctioningStepSelector:
    @staticmethod
    def list_for_product(product_uuid: str) -> QuerySet:
        return ProductFunctioningStep.objects.filter(product__uuid=product_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ProductFunctioningStep:
        return get_object_or_404(ProductFunctioningStep, uuid=uuid, is_deleted=False)


class ProductFunctioningStepCommands:
    @staticmethod
    @transaction.atomic
    def create(product: Product, **fields) -> ProductFunctioningStep:
        return ProductFunctioningStep.objects.create(product=product, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ProductFunctioningStep, **fields) -> ProductFunctioningStep:
        allowed = ('step_number', 'title', 'description', 'image', 'estimated_time', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ProductFunctioningStep) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ProductFunctioningStep) -> ProductFunctioningStep:
        return _toggle_active(instance)

    @staticmethod
    def reorder(product_id: int, ordered_uuids: list) -> None:
        _reorder(ProductFunctioningStep, ordered_uuids, product_id=product_id)
