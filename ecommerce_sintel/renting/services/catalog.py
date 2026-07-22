"""
renting/services/catalog.py

Service layer para el catalogo enriquecido de Equipment (2026-07-16):
RentalIncludedItem, RentalExcludedItem, RentalFeature, RentalSpecificationGroup,
RentalSpecification, RentalRequirement, RentalServiceIncluded,
RentalOptionalService, RentalFAQ, RentalVideo, RentalDocument.

Todos comparten el mismo shape operativo (fila hija de Equipment, con
position/is_active/is_deleted), asi que reorder/toggle_active/duplicate se
factorizan en helpers de modulo -- cada modelo sigue teniendo su propio
Selector y su propio Commands (un servicio por modelo, sin CRUD generico
expuesto), solo el cuerpo interno se comparte para no repetir la misma
logica 11 veces.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet

from renting.models import (
    Equipment, EquipmentImage,
    RentalIncludedItem, RentalExcludedItem, RentalFeature,
    RentalSpecificationGroup, RentalSpecification, RentalRequirement,
    RentalServiceIncluded, RentalOptionalService, RentalFAQ,
    RentalVideo, RentalDocument,
)


def _reorder(model, ordered_uuids: list, **scope) -> None:
    """Reasigna `position` (0..n) segun el orden de `ordered_uuids` (drag&drop)."""
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


# ── EquipmentImage (galeria avanzada) ─────────────────────────────────────────

class EquipmentImageSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return EquipmentImage.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> EquipmentImage:
        return get_object_or_404(EquipmentImage, uuid=uuid, is_deleted=False)


class EquipmentImageCommands:
    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, image, image_type: str = EquipmentImage.TYPE_GALLERY,
               alt_text: str = '', is_primary: bool = False, position: int = 0) -> EquipmentImage:
        if is_primary:
            EquipmentImage.objects.filter(equipment=equipment, is_deleted=False).update(is_primary=False)
        return EquipmentImage.objects.create(
            equipment=equipment, image=image, image_type=image_type,
            alt_text=alt_text, is_primary=is_primary, position=position,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: EquipmentImage, **fields) -> EquipmentImage:
        allowed = ('alt_text', 'image_type', 'position')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def set_primary(instance: EquipmentImage) -> EquipmentImage:
        EquipmentImage.objects.filter(equipment=instance.equipment, is_deleted=False).update(is_primary=False)
        instance.is_primary = True
        instance.save(update_fields=['is_primary', 'updated_at'])
        return instance

    @staticmethod
    def delete(instance: EquipmentImage) -> None:
        _soft_delete(instance)

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(EquipmentImage, ordered_uuids, equipment_id=equipment_id)


# ── RentalIncludedItem ────────────────────────────────────────────────────────

class RentalIncludedItemSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalIncludedItem.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalIncludedItem:
        return get_object_or_404(RentalIncludedItem, uuid=uuid, is_deleted=False)


class RentalIncludedItemCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalIncludedItem:
        return RentalIncludedItem.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalIncludedItem, **fields) -> RentalIncludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalIncludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalIncludedItem) -> RentalIncludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalIncludedItem) -> RentalIncludedItem:
        return _duplicate(instance, RentalIncludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalIncludedItem, ordered_uuids, equipment_id=equipment_id)


# ── RentalExcludedItem ────────────────────────────────────────────────────────

class RentalExcludedItemSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalExcludedItem.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalExcludedItem:
        return get_object_or_404(RentalExcludedItem, uuid=uuid, is_deleted=False)


class RentalExcludedItemCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalExcludedItem:
        return RentalExcludedItem.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalExcludedItem, **fields) -> RentalExcludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalExcludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalExcludedItem) -> RentalExcludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalExcludedItem) -> RentalExcludedItem:
        return _duplicate(instance, RentalExcludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalExcludedItem, ordered_uuids, equipment_id=equipment_id)


# ── RentalFeature ──────────────────────────────────────────────────────────────

class RentalFeatureSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalFeature.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalFeature:
        return get_object_or_404(RentalFeature, uuid=uuid, is_deleted=False)


class RentalFeatureCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'value', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalFeature:
        return RentalFeature.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalFeature, **fields) -> RentalFeature:
        allowed = ('title', 'value', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalFeature) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalFeature) -> RentalFeature:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalFeature) -> RentalFeature:
        return _duplicate(instance, RentalFeatureCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalFeature, ordered_uuids, equipment_id=equipment_id)


# ── RentalSpecificationGroup / RentalSpecification ────────────────────────────

class RentalSpecificationGroupSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return (
            RentalSpecificationGroup.objects
            .filter(equipment__uuid=equipment_uuid, is_deleted=False)
            .prefetch_related('specifications')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalSpecificationGroup:
        return get_object_or_404(RentalSpecificationGroup, uuid=uuid, is_deleted=False)


class RentalSpecificationGroupCommands:
    _COPY_FIELDS = ['equipment_id', 'name', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalSpecificationGroup:
        return RentalSpecificationGroup.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalSpecificationGroup, **fields) -> RentalSpecificationGroup:
        allowed = ('name', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def delete(instance: RentalSpecificationGroup) -> None:
        _soft_delete(instance)
        RentalSpecification.objects.filter(group=instance, is_deleted=False).update(is_deleted=True)

    @staticmethod
    def toggle_active(instance: RentalSpecificationGroup) -> RentalSpecificationGroup:
        return _toggle_active(instance)

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalSpecificationGroup, ordered_uuids, equipment_id=equipment_id)


class RentalSpecificationSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalSpecification.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def list_for_group(group_uuid: str) -> QuerySet:
        return RentalSpecification.objects.filter(group__uuid=group_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalSpecification:
        return get_object_or_404(RentalSpecification, uuid=uuid, is_deleted=False)


class RentalSpecificationCommands:
    _COPY_FIELDS = ['equipment_id', 'group_id', 'name', 'value', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, group: RentalSpecificationGroup, **fields) -> RentalSpecification:
        if group.equipment_id != equipment.id:
            raise ValueError('El grupo de especificaciones no pertenece a este equipo.')
        return RentalSpecification.objects.create(equipment=equipment, group=group, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalSpecification, **fields) -> RentalSpecification:
        allowed = ('name', 'value', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalSpecification) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalSpecification) -> RentalSpecification:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalSpecification) -> RentalSpecification:
        return _duplicate(instance, RentalSpecificationCommands._COPY_FIELDS, {'name': f'{instance.name} (copia)'})

    @staticmethod
    def reorder(group_id: int, ordered_uuids: list) -> None:
        _reorder(RentalSpecification, ordered_uuids, group_id=group_id)


# ── RentalRequirement ──────────────────────────────────────────────────────────

class RentalRequirementSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalRequirement.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalRequirement:
        return get_object_or_404(RentalRequirement, uuid=uuid, is_deleted=False)


class RentalRequirementCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'description', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalRequirement:
        return RentalRequirement.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalRequirement, **fields) -> RentalRequirement:
        allowed = ('title', 'description', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalRequirement) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalRequirement) -> RentalRequirement:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalRequirement) -> RentalRequirement:
        return _duplicate(instance, RentalRequirementCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalRequirement, ordered_uuids, equipment_id=equipment_id)


# ── RentalServiceIncluded ──────────────────────────────────────────────────────

class RentalServiceIncludedSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalServiceIncluded.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalServiceIncluded:
        return get_object_or_404(RentalServiceIncluded, uuid=uuid, is_deleted=False)


class RentalServiceIncludedCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalServiceIncluded:
        return RentalServiceIncluded.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalServiceIncluded, **fields) -> RentalServiceIncluded:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalServiceIncluded) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalServiceIncluded) -> RentalServiceIncluded:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalServiceIncluded) -> RentalServiceIncluded:
        return _duplicate(instance, RentalServiceIncludedCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalServiceIncluded, ordered_uuids, equipment_id=equipment_id)


# ── RentalOptionalService ──────────────────────────────────────────────────────

class RentalOptionalServiceSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalOptionalService.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalOptionalService:
        return get_object_or_404(RentalOptionalService, uuid=uuid, is_deleted=False)


class RentalOptionalServiceCommands:
    _COPY_FIELDS = ['equipment_id', 'title', 'description', 'price', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalOptionalService:
        return RentalOptionalService.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalOptionalService, **fields) -> RentalOptionalService:
        allowed = ('title', 'description', 'price', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalOptionalService) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalOptionalService) -> RentalOptionalService:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalOptionalService) -> RentalOptionalService:
        return _duplicate(instance, RentalOptionalServiceCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalOptionalService, ordered_uuids, equipment_id=equipment_id)


# ── RentalFAQ ───────────────────────────────────────────────────────────────────

class RentalFAQSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalFAQ.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalFAQ:
        return get_object_or_404(RentalFAQ, uuid=uuid, is_deleted=False)


class RentalFAQCommands:
    _COPY_FIELDS = ['equipment_id', 'question', 'answer', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, **fields) -> RentalFAQ:
        return RentalFAQ.objects.create(equipment=equipment, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: RentalFAQ, **fields) -> RentalFAQ:
        allowed = ('question', 'answer', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalFAQ) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalFAQ) -> RentalFAQ:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: RentalFAQ) -> RentalFAQ:
        return _duplicate(instance, RentalFAQCommands._COPY_FIELDS, {'question': f'{instance.question} (copia)'})

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalFAQ, ordered_uuids, equipment_id=equipment_id)


# ── RentalVideo ─────────────────────────────────────────────────────────────────

class RentalVideoSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str) -> QuerySet:
        return RentalVideo.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalVideo:
        return get_object_or_404(RentalVideo, uuid=uuid, is_deleted=False)


class RentalVideoCommands:
    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, source_type: str, title='', video_url='', video_file=None,
               thumbnail=None, position=0, is_active=True) -> RentalVideo:
        if source_type == RentalVideo.SOURCE_MP4 and not video_file:
            raise ValueError('Debe adjuntar un archivo MP4 para este tipo de video.')
        if source_type in (RentalVideo.SOURCE_YOUTUBE, RentalVideo.SOURCE_VIMEO) and not video_url:
            raise ValueError('Debe indicar la URL del video de YouTube/Vimeo.')
        return RentalVideo.objects.create(
            equipment=equipment, source_type=source_type, title=title,
            video_url=video_url, video_file=video_file, thumbnail=thumbnail,
            position=position, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: RentalVideo, **fields) -> RentalVideo:
        allowed = ('title', 'source_type', 'video_url', 'video_file', 'thumbnail', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: RentalVideo) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalVideo) -> RentalVideo:
        return _toggle_active(instance)

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalVideo, ordered_uuids, equipment_id=equipment_id)


# ── RentalDocument ──────────────────────────────────────────────────────────────

class RentalDocumentSelector:
    @staticmethod
    def list_for_equipment(equipment_uuid: str, public_only: bool = False) -> QuerySet:
        qs = RentalDocument.objects.filter(equipment__uuid=equipment_uuid, is_deleted=False)
        if public_only:
            qs = qs.filter(is_public=True, is_active=True)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> RentalDocument:
        return get_object_or_404(RentalDocument, uuid=uuid, is_deleted=False)


class RentalDocumentCommands:
    @staticmethod
    @transaction.atomic
    def create(equipment: Equipment, file, title: str, document_type: str, description='',
               version='', language='es', cover_image=None, position=0, is_public=True,
               is_active=True) -> RentalDocument:
        from accounts.services.commands import validate_file

        validate_file(
            file, max_size_mb=50,
            allowed_extensions=['.pdf', '.docx', '.zip', '.dwg', '.dxf', '.xlsx', '.pptx'],
            magic_bytes_check=True,
        )
        return RentalDocument.objects.create(
            equipment=equipment, file=file, title=title, document_type=document_type,
            description=description, version=version, language=language,
            cover_image=cover_image, position=position, is_public=is_public, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: RentalDocument, **fields) -> RentalDocument:
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
    def delete(instance: RentalDocument) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: RentalDocument) -> RentalDocument:
        return _toggle_active(instance)

    @staticmethod
    @transaction.atomic
    def register_download(instance: RentalDocument) -> RentalDocument:
        instance.downloads = instance.downloads + 1
        instance.save(update_fields=['downloads', 'updated_at'])
        return instance

    @staticmethod
    def reorder(equipment_id: int, ordered_uuids: list) -> None:
        _reorder(RentalDocument, ordered_uuids, equipment_id=equipment_id)
