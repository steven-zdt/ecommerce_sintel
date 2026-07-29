"""
Serializers para UnifiedPublicDetailDTO

Convierte dataclasses de DTO a JSON para respuestas HTTP.
"""

from rest_framework import serializers
from shared.dtos import UnifiedPublicDetailDTO


class UnifiedPublicDetailDTOSerializer(serializers.Serializer):
    """
    Serializer para UnifiedPublicDetailDTO.

    Convierte el DTO (dataclass) a representación JSON.
    No toca BD, solo transforma datos.
    """

    uuid = serializers.CharField()
    slug = serializers.CharField()
    module_type = serializers.CharField()

    hero = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    pricing = serializers.SerializerMethodField()
    marketing = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    technical = serializers.SerializerMethodField()

    included_items = serializers.SerializerMethodField()
    excluded_items = serializers.SerializerMethodField()
    requirements = serializers.SerializerMethodField()

    faq = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()

    reviews = serializers.SerializerMethodField()
    related_items = serializers.SerializerMethodField()
    recommendations = serializers.SerializerMethodField()

    seo = serializers.SerializerMethodField()

    def _dataclass_to_dict(self, obj):
        """Convierte un dataclass a dict."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._dataclass_to_dict(item) for item in obj]
        if hasattr(obj, '__dataclass_fields__'):
            from dataclasses import asdict
            return asdict(obj)
        return obj

    def get_hero(self, obj):
        return self._dataclass_to_dict(obj.hero)

    def get_gallery(self, obj):
        return self._dataclass_to_dict(obj.gallery)

    def get_pricing(self, obj):
        return self._dataclass_to_dict(obj.pricing)

    def get_marketing(self, obj):
        return self._dataclass_to_dict(obj.marketing)

    def get_availability(self, obj):
        return self._dataclass_to_dict(obj.availability)

    def get_description(self, obj):
        return self._dataclass_to_dict(obj.description)

    def get_technical(self, obj):
        return self._dataclass_to_dict(obj.technical)

    def get_included_items(self, obj):
        return self._dataclass_to_dict(obj.included_items)

    def get_excluded_items(self, obj):
        return self._dataclass_to_dict(obj.excluded_items)

    def get_requirements(self, obj):
        return self._dataclass_to_dict(obj.requirements)

    def get_faq(self, obj):
        return self._dataclass_to_dict(obj.faq)

    def get_documents(self, obj):
        return self._dataclass_to_dict(obj.documents)

    def get_videos(self, obj):
        return self._dataclass_to_dict(obj.videos)

    def get_reviews(self, obj):
        return self._dataclass_to_dict(obj.reviews)

    def get_related_items(self, obj):
        return self._dataclass_to_dict(obj.related_items)

    def get_recommendations(self, obj):
        return self._dataclass_to_dict(obj.recommendations)

    def get_seo(self, obj):
        return self._dataclass_to_dict(obj.seo)
