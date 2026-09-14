"""
shared/services/content_blocks.py

Service layer para ContentBlockConfig y CatalogRelation (shared/models.py) --
construido en la Fase 3 de la reingenieria UX/UI de Shop
(ver DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md SS4) y extendido en la
reingenieria de Technical Services (2026-08-05, ver
technical_services/.AGENT/docs/UI_MODULO_SERVICES.md) para un segundo
content_type. Generico por diseno (recibe `content_type`, nunca asume Product).

Identificacion siempre por uuid, nunca por pk -- ver el docstring de
shared/models.py sobre por que no se usa GenericForeignKey aqui.
"""
from django.db import transaction
from django.shortcuts import get_object_or_404

from shared.models import ContentBlockConfig, CatalogRelation


class ContentBlockConfigSelector:
    @staticmethod
    def resolve_for(content_type, object_uuid, default_order: list = None) -> list:
        """
        Devuelve los bloques de `default_order` (default: el catalogo de Shop,
        `ContentBlockConfig.DEFAULT_ORDER`, para no romper el call site
        original) con su orden/visibilidad final, mezclando las filas
        guardadas con el orden por defecto para los bloques sin fila -- asi
        una entidad sin ninguna fila en ContentBlockConfig se comporta igual
        que si estuviera completamente configurada (compatibilidad, SS7 del
        diseno). Cada content_type (Product, TechnicalService, ...) pasa su
        propia lista -- no hay un unico "orden por defecto" valido para todos.
        """
        order = default_order if default_order is not None else ContentBlockConfig.DEFAULT_ORDER
        saved = {
            row.block_type: row
            for row in ContentBlockConfig.objects.filter(
                content_type=content_type, object_uuid=object_uuid, is_deleted=False,
            )
        }
        blocks = []
        for index, block_type in enumerate(order):
            row = saved.get(block_type)
            blocks.append({
                'block_type': block_type,
                'display_order': row.display_order if row else index,
                'is_visible': row.is_visible if row else True,
            })
        blocks.sort(key=lambda block: block['display_order'])
        return blocks


class ContentBlockConfigCommands:
    @staticmethod
    @transaction.atomic
    def set_order(content_type, object_uuid, ordered_block_types: list) -> None:
        # Valida contra el catalogo COMPLETO de tipos de bloque (union de todos
        # los content_types que usan ContentBlockConfig), no solo los de Shop --
        # cada content_type ya filtra su propia lista antes de llamar aca.
        valid_types = {choice[0] for choice in ContentBlockConfig.BLOCK_TYPE_CHOICES}
        for position, block_type in enumerate(ordered_block_types):
            if block_type not in valid_types:
                continue
            ContentBlockConfig.objects.update_or_create(
                content_type=content_type, object_uuid=object_uuid, block_type=block_type,
                defaults={'display_order': position, 'is_deleted': False},
            )

    @staticmethod
    @transaction.atomic
    def set_visibility(content_type, object_uuid, block_type: str, is_visible: bool,
                        default_order: list = None) -> ContentBlockConfig:
        order = default_order if default_order is not None else ContentBlockConfig.DEFAULT_ORDER
        default_index = order.index(block_type) if block_type in order else 0
        instance, created = ContentBlockConfig.objects.get_or_create(
            content_type=content_type, object_uuid=object_uuid, block_type=block_type,
            defaults={'display_order': default_index, 'is_visible': is_visible},
        )
        if not created:
            instance.is_visible = is_visible
            instance.is_deleted = False
            instance.save(update_fields=['is_visible', 'is_deleted', 'updated_at'])
        return instance


class CatalogRelationSelector:
    @staticmethod
    def list_for(content_type, object_uuid, relation_type: str = None):
        qs = CatalogRelation.objects.filter(
            content_type=content_type, object_uuid=object_uuid, is_deleted=False,
        )
        if relation_type:
            qs = qs.filter(relation_type=relation_type)
        return qs.order_by('display_order')

    @staticmethod
    def get_by_uuid(uuid) -> CatalogRelation:
        return get_object_or_404(CatalogRelation, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_related_objects(content_type, object_uuid, relation_type: str) -> list:
        """
        Resuelve las entidades destino de las relaciones activas, en orden. Query
        por relacion (no bulk) -- listas de relaciones de producto son chicas
        (decenas, no miles), no amerita la complejidad de agrupar por modelo.
        """
        relations = CatalogRelationSelector.list_for(content_type, object_uuid, relation_type)
        resolved = []
        for relation in relations:
            model_class = relation.related_content_type.model_class()
            obj = model_class.objects.filter(uuid=relation.related_object_uuid, is_deleted=False).first()
            if obj is not None:
                resolved.append(obj)
        return resolved


class CatalogRelationCommands:
    @staticmethod
    @transaction.atomic
    def add(content_type, object_uuid, related_content_type, related_object_uuid,
            relation_type: str, display_order: int = 0) -> CatalogRelation:
        instance, created = CatalogRelation.objects.get_or_create(
            content_type=content_type, object_uuid=object_uuid,
            related_content_type=related_content_type, related_object_uuid=related_object_uuid,
            relation_type=relation_type,
            defaults={'display_order': display_order},
        )
        if not created and instance.is_deleted:
            instance.is_deleted = False
            instance.display_order = display_order
            instance.save(update_fields=['is_deleted', 'display_order', 'updated_at'])
        return instance

    @staticmethod
    def remove(instance: CatalogRelation) -> None:
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])

    @staticmethod
    @transaction.atomic
    def reorder(content_type, object_uuid, relation_type: str, ordered_uuids: list) -> None:
        items = {
            str(item.uuid): item
            for item in CatalogRelation.objects.filter(
                content_type=content_type, object_uuid=object_uuid,
                relation_type=relation_type, is_deleted=False,
            )
        }
        for position, item_uuid in enumerate(ordered_uuids):
            item = items.get(str(item_uuid))
            if item is not None and item.display_order != position:
                item.display_order = position
                item.save(update_fields=['display_order', 'updated_at'])
