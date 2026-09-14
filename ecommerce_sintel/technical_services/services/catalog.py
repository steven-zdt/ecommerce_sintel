"""
technical_services/services/catalog.py

Service layer para el catalogo enriquecido de TechnicalService (2026-08-05),
espejo de shop/services/catalog.py (shop.Product) y renting/services/catalog.py
(renting.Equipment): ServiceIncludedItem, ServiceExcludedItem, ServiceRequirement,
ServiceSpecificationGroup, ServiceSpecification, ServiceDocument, ServiceVideo,
ServiceProcessStep.

Todos comparten el mismo shape operativo (fila hija de TechnicalService, con
position/is_active/is_deleted), asi que reorder/toggle_active/duplicate se
factorizan en helpers de modulo -- cada modelo sigue teniendo su propio
Selector y su propio Commands (un servicio por modelo, sin CRUD generico
expuesto), solo el cuerpo interno se comparte para no repetir la misma
logica 8 veces.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet

from technical_services.models import (
    TechnicalService,
    ServiceIncludedItem, ServiceExcludedItem, ServiceRequirement,
    ServiceSpecificationGroup, ServiceSpecification,
    ServiceDocument, ServiceVideo, ServiceProcessStep,
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


# ── ServiceIncludedItem ─────────────────────────────────────────────────────────

class ServiceIncludedItemSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceIncludedItem.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceIncludedItem:
        return get_object_or_404(ServiceIncludedItem, uuid=uuid, is_deleted=False)


class ServiceIncludedItemCommands:
    _COPY_FIELDS = ['service_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceIncludedItem:
        return ServiceIncludedItem.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceIncludedItem, **fields) -> ServiceIncludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceIncludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceIncludedItem) -> ServiceIncludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServiceIncludedItem) -> ServiceIncludedItem:
        return _duplicate(instance, ServiceIncludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceIncludedItem, ordered_uuids, service_id=service_id)


# ── ServiceExcludedItem ─────────────────────────────────────────────────────────

class ServiceExcludedItemSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceExcludedItem.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceExcludedItem:
        return get_object_or_404(ServiceExcludedItem, uuid=uuid, is_deleted=False)


class ServiceExcludedItemCommands:
    _COPY_FIELDS = ['service_id', 'title', 'description', 'icon', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceExcludedItem:
        return ServiceExcludedItem.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceExcludedItem, **fields) -> ServiceExcludedItem:
        allowed = ('title', 'description', 'icon', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceExcludedItem) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceExcludedItem) -> ServiceExcludedItem:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServiceExcludedItem) -> ServiceExcludedItem:
        return _duplicate(instance, ServiceExcludedItemCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceExcludedItem, ordered_uuids, service_id=service_id)


# ── ServiceRequirement ──────────────────────────────────────────────────────────

class ServiceRequirementSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceRequirement.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceRequirement:
        return get_object_or_404(ServiceRequirement, uuid=uuid, is_deleted=False)


class ServiceRequirementCommands:
    _COPY_FIELDS = ['service_id', 'title', 'description', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceRequirement:
        return ServiceRequirement.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceRequirement, **fields) -> ServiceRequirement:
        allowed = ('title', 'description', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceRequirement) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceRequirement) -> ServiceRequirement:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServiceRequirement) -> ServiceRequirement:
        return _duplicate(instance, ServiceRequirementCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceRequirement, ordered_uuids, service_id=service_id)


# ── ServiceSpecificationGroup / ServiceSpecification ────────────────────────────

class ServiceSpecificationGroupSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return (
            ServiceSpecificationGroup.objects
            .filter(service__uuid=service_uuid, is_deleted=False)
            .prefetch_related('specifications')
        )

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceSpecificationGroup:
        return get_object_or_404(ServiceSpecificationGroup, uuid=uuid, is_deleted=False)


class ServiceSpecificationGroupCommands:
    _COPY_FIELDS = ['service_id', 'name', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceSpecificationGroup:
        return ServiceSpecificationGroup.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceSpecificationGroup, **fields) -> ServiceSpecificationGroup:
        allowed = ('name', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    @transaction.atomic
    def delete(instance: ServiceSpecificationGroup) -> None:
        _soft_delete(instance)
        ServiceSpecification.objects.filter(group=instance, is_deleted=False).update(is_deleted=True)

    @staticmethod
    def toggle_active(instance: ServiceSpecificationGroup) -> ServiceSpecificationGroup:
        return _toggle_active(instance)

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceSpecificationGroup, ordered_uuids, service_id=service_id)


class ServiceSpecificationSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceSpecification.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def list_for_group(group_uuid: str) -> QuerySet:
        return ServiceSpecification.objects.filter(group__uuid=group_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceSpecification:
        return get_object_or_404(ServiceSpecification, uuid=uuid, is_deleted=False)


class ServiceSpecificationCommands:
    _COPY_FIELDS = ['service_id', 'group_id', 'name', 'value', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, group: ServiceSpecificationGroup, **fields) -> ServiceSpecification:
        if group.service_id != service.id:
            raise ValueError('El grupo de especificaciones no pertenece a este servicio.')
        return ServiceSpecification.objects.create(service=service, group=group, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceSpecification, **fields) -> ServiceSpecification:
        allowed = ('name', 'value', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceSpecification) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceSpecification) -> ServiceSpecification:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServiceSpecification) -> ServiceSpecification:
        return _duplicate(instance, ServiceSpecificationCommands._COPY_FIELDS, {'name': f'{instance.name} (copia)'})

    @staticmethod
    def reorder(group_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceSpecification, ordered_uuids, group_id=group_id)


# ── ServiceDocument ──────────────────────────────────────────────────────────────

class ServiceDocumentSelector:
    @staticmethod
    def list_for_service(service_uuid: str, public_only: bool = False) -> QuerySet:
        qs = ServiceDocument.objects.filter(service__uuid=service_uuid, is_deleted=False)
        if public_only:
            qs = qs.filter(is_public=True, is_active=True)
        return qs

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceDocument:
        return get_object_or_404(ServiceDocument, uuid=uuid, is_deleted=False)


class ServiceDocumentCommands:
    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, file, title: str, document_type: str, description='',
               cover_image=None, position=0, is_public=True, is_active=True) -> ServiceDocument:
        from accounts.services.commands import validate_file

        validate_file(
            file, max_size_mb=50,
            allowed_extensions=['.pdf', '.docx', '.zip', '.xlsx', '.pptx'],
            magic_bytes_check=True,
        )
        return ServiceDocument.objects.create(
            service=service, file=file, title=title, document_type=document_type,
            description=description, cover_image=cover_image, position=position,
            is_public=is_public, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceDocument, **fields) -> ServiceDocument:
        allowed = ('title', 'description', 'document_type', 'cover_image', 'position', 'is_public', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceDocument) -> None:
        _soft_delete(instance)

    @staticmethod
    @transaction.atomic
    def register_download(instance: ServiceDocument) -> ServiceDocument:
        instance.downloads = instance.downloads + 1
        instance.save(update_fields=['downloads', 'updated_at'])
        return instance

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceDocument, ordered_uuids, service_id=service_id)


# ── ServiceVideo ─────────────────────────────────────────────────────────────────

class ServiceVideoSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceVideo.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceVideo:
        return get_object_or_404(ServiceVideo, uuid=uuid, is_deleted=False)


class ServiceVideoCommands:
    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, source_type: str, title='', video_url='', video_file=None,
               thumbnail=None, position=0, is_active=True) -> ServiceVideo:
        if source_type == ServiceVideo.SOURCE_MP4 and not video_file:
            raise ValueError('Debe adjuntar un archivo MP4 para este tipo de video.')
        if source_type in (ServiceVideo.SOURCE_YOUTUBE, ServiceVideo.SOURCE_VIMEO) and not video_url:
            raise ValueError('Debe indicar la URL del video de YouTube/Vimeo.')
        return ServiceVideo.objects.create(
            service=service, source_type=source_type, title=title,
            video_url=video_url, video_file=video_file, thumbnail=thumbnail,
            position=position, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceVideo, **fields) -> ServiceVideo:
        allowed = ('title', 'source_type', 'video_url', 'video_file', 'thumbnail', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceVideo) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceVideo) -> ServiceVideo:
        return _toggle_active(instance)

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceVideo, ordered_uuids, service_id=service_id)


# ── ServiceProcessStep ──────────────────────────────────────────────────────────

class ServiceProcessStepSelector:
    @staticmethod
    def list_for_service(service_uuid: str) -> QuerySet:
        return ServiceProcessStep.objects.filter(service__uuid=service_uuid, is_deleted=False)

    @staticmethod
    def get_by_uuid(uuid: str) -> ServiceProcessStep:
        return get_object_or_404(ServiceProcessStep, uuid=uuid, is_deleted=False)


class ServiceProcessStepCommands:
    _COPY_FIELDS = ['service_id', 'step_number', 'title', 'description', 'estimated_time', 'position', 'is_active']

    @staticmethod
    @transaction.atomic
    def create(service: TechnicalService, **fields) -> ServiceProcessStep:
        return ServiceProcessStep.objects.create(service=service, **fields)

    @staticmethod
    @transaction.atomic
    def update(instance: ServiceProcessStep, **fields) -> ServiceProcessStep:
        allowed = ('step_number', 'title', 'description', 'image', 'estimated_time', 'position', 'is_active')
        for key, val in fields.items():
            if key in allowed:
                setattr(instance, key, val)
        instance.save()
        return instance

    @staticmethod
    def delete(instance: ServiceProcessStep) -> None:
        _soft_delete(instance)

    @staticmethod
    def toggle_active(instance: ServiceProcessStep) -> ServiceProcessStep:
        return _toggle_active(instance)

    @staticmethod
    def duplicate(instance: ServiceProcessStep) -> ServiceProcessStep:
        return _duplicate(instance, ServiceProcessStepCommands._COPY_FIELDS, {'title': f'{instance.title} (copia)'})

    @staticmethod
    def reorder(service_id: int, ordered_uuids: list) -> None:
        _reorder(ServiceProcessStep, ordered_uuids, service_id=service_id)
