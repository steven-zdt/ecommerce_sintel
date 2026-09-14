"""
shared/serializers/content_blocks.py

Serializers admin para ContentBlockConfig/CatalogRelation (shared/models.py) --
Fase 3 de la reingenieria PDP de Shop. En esta fase, `related_product` siempre
resuelve contra shop.Product (Regla 6 del brief: generico por diseno, Shop-only
por alcance).
"""
from rest_framework import serializers

from shared.models import ContentBlockConfig, CatalogRelation
from shop.models import Product


class ContentBlockSerializer(serializers.Serializer):
    """Output de un bloque ya resuelto (ContentBlockConfigSelector.resolve_for) --
    no es un ModelSerializer porque resolve_for devuelve dicts, no instancias
    (los bloques sin fila propia no existen en BD, ver shared/models.py)."""
    block_type = serializers.ChoiceField(choices=ContentBlockConfig.BLOCK_TYPE_CHOICES)
    display_order = serializers.IntegerField()
    is_visible = serializers.BooleanField()


class ContentBlockOrderInputSerializer(serializers.Serializer):
    ordered_block_types = serializers.ListField(child=serializers.CharField(), allow_empty=False)


class ContentBlockVisibilityInputSerializer(serializers.Serializer):
    block_type = serializers.ChoiceField(choices=ContentBlockConfig.BLOCK_TYPE_CHOICES)
    is_visible = serializers.BooleanField()


class CatalogRelationInputSerializer(serializers.Serializer):
    relation_type = serializers.ChoiceField(choices=CatalogRelation.RELATION_TYPE_CHOICES)
    related_product = serializers.SlugRelatedField(
        slug_field='uuid', queryset=Product.objects.filter(is_deleted=False),
    )


class CatalogRelationReorderInputSerializer(serializers.Serializer):
    relation_type = serializers.ChoiceField(choices=CatalogRelation.RELATION_TYPE_CHOICES)
    ordered_uuids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
