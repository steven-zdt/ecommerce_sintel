from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from marketing.models import (
    MarketingCampaign, CampaignBenefit, CampaignItem, CampaignMedia, FlashOffer,
    PersonalOffer, CampaignLog, AgentRun
)

class CampaignLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignLog
        fields = ['uuid', 'channel', 'recipient', 'is_sent', 'sent_at', 'error_message']


class CampaignBenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignBenefit
        fields = ['uuid', 'benefit_type', 'label', 'value']
        read_only_fields = ['uuid']


# PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 4 (2026-09-23,
# Producto) + Fase 5/6 (2026-09-23, Servicio/Renting): 3 origenes de catalogo soportados --
# (app_label, model) real de cada ContentType, mismo criterio que shared.models.CatalogRelation
# (nunca GenericForeignKey). Renting referencia EquipmentVariant (no Equipment): es la unidad con
# tarifa/modalidad real, igual que el plan pide "equipo/variante" -- el preview igual expone el
# Equipment padre completo (imagenes/descripcion), ver get_source_preview().
_SOURCE_TYPE_TO_CTYPE = {
    'product': ('shop', 'product'),
    'service': ('technical_services', 'technicalservice'),
    'renting': ('renting', 'equipmentvariant'),
}
_CTYPE_TO_SOURCE_TYPE = {v: k for k, v in _SOURCE_TYPE_TO_CTYPE.items()}


def _resolve_item_preview(source_type: str, object_uuid) -> dict | None:
    """
    Resuelve y expone los datos REALES del objeto de catalogo -- nunca copiados a la campana,
    siempre leidos en vivo del objeto real (Fase 4: "no duplicar datos innecesariamente").
    Compartido por CampaignItemSerializer (Fase 7, lista de items).
    """
    if source_type == 'product':
        from shop.models import Product
        from shop.api.serializers import ProductSerializer
        try:
            product = Product.objects.select_related('brand', 'category').prefetch_related(
                'variants', 'images',
            ).get(uuid=object_uuid)
        except Product.DoesNotExist:
            return None
        return ProductSerializer(product).data

    if source_type == 'service':
        from technical_services.models import TechnicalService
        from technical_services.api.serializers import TechnicalServiceDetailSerializer
        try:
            service = TechnicalService.objects.select_related('category', 'level').prefetch_related(
                'variants', 'images',
            ).get(uuid=object_uuid)
        except TechnicalService.DoesNotExist:
            return None
        return TechnicalServiceDetailSerializer(service).data

    if source_type == 'renting':
        # Fase 6: la campana referencia la VARIANTE (tarifa/modalidad reales), pero el
        # preview expone el Equipment padre completo (imagenes/descripcion/categoria/marca)
        # + la variante seleccionada aparte -- ninguno de los 2 serializers por si solo
        # cubre "equipo, variante, tarifa, modalidad, disponibilidad, imagenes" (Fase 6).
        from renting.models.equipment import EquipmentVariant
        from renting.api.serializers import EquipmentSerializer, EquipmentVariantSerializer
        try:
            variant = EquipmentVariant.objects.select_related(
                'equipment', 'equipment__category', 'equipment__brand',
            ).get(uuid=object_uuid)
        except EquipmentVariant.DoesNotExist:
            return None
        data = EquipmentSerializer(variant.equipment).data
        data['selected_variant'] = EquipmentVariantSerializer(variant).data
        return data

    return None


def _item_exists(source_type: str, object_uuid) -> bool:
    if source_type == 'product':
        from shop.models import Product
        return Product.objects.filter(uuid=object_uuid).exists()
    if source_type == 'service':
        from technical_services.models import TechnicalService
        return TechnicalService.objects.filter(uuid=object_uuid).exists()
    if source_type == 'renting':
        from renting.models.equipment import EquipmentVariant
        return EquipmentVariant.objects.filter(uuid=object_uuid).exists()
    return False


class CampaignItemSerializer(serializers.Serializer):
    """
    Fase 7 (campanas compuestas): contrato ergonomico de escritura/lectura para
    CampaignItem -- 'type' en vez de exigir que el cliente conozca el pk interno de
    ContentType (mismo criterio que 'source_type' ya usaba en Fase 3-6). "02 camaras" es
    UN item con quantity=2, no dos items separados (ver docstring de CampaignItem).
    """
    type = serializers.ChoiceField(choices=list(_SOURCE_TYPE_TO_CTYPE.keys()))
    uuid = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    preview = serializers.SerializerMethodField(read_only=True)

    def validate(self, attrs):
        if not _item_exists(attrs['type'], attrs['uuid']):
            raise serializers.ValidationError({'uuid': f"{attrs['type']} no encontrado."})
        return attrs

    def get_preview(self, attrs) -> dict | None:
        # attrs puede ser un dict (validated_data en escritura) o un CampaignItem real (lectura,
        # ver to_representation de MarketingCampaignSerializer).
        if isinstance(attrs, CampaignItem):
            key = (attrs.content_type.app_label, attrs.content_type.model)
            source_type = _CTYPE_TO_SOURCE_TYPE.get(key)
            return _resolve_item_preview(source_type, attrs.object_uuid)
        return _resolve_item_preview(attrs.get('type'), attrs.get('uuid'))

    def to_representation(self, instance):
        if isinstance(instance, CampaignItem):
            key = (instance.content_type.app_label, instance.content_type.model)
            return {
                'type': _CTYPE_TO_SOURCE_TYPE.get(key),
                'uuid': str(instance.object_uuid),
                'quantity': instance.quantity,
                'preview': self.get_preview(instance),
            }
        return super().to_representation(instance)


class CampaignMediaSerializer(serializers.ModelSerializer):
    """
    Fase 11-14 (2026-09-23): solo lectura -- la galeria se gestiona via las acciones dedicadas
    de MarketingCampaignViewSet (upload_media/delete_media/reorder_media/toggle_media), NUNCA
    como lista anidada writable del serializer principal. Esto es lo que garantiza "no perder
    medios existentes al editar otros campos" (Fase 14): un PATCH de texto normal ni siquiera
    toca esta relacion, a diferencia de benefits/items que si son full-replace-on-provide.
    """
    class Meta:
        model = CampaignMedia
        fields = [
            'uuid', 'media_type', 'file', 'mime_type', 'size', 'width', 'height',
            'duration', 'sort_order', 'is_active',
        ]
        read_only_fields = fields


class MarketingCampaignSerializer(serializers.ModelSerializer):
    logs = CampaignLogSerializer(many=True, read_only=True)
    benefits = CampaignBenefitSerializer(many=True, required=False)
    items = CampaignItemSerializer(many=True, required=False)
    media = CampaignMediaSerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = MarketingCampaign
        fields = [
            'id', 'uuid', 'title', 'content', 'channels',
            'scheduled_at', 'sent_at', 'is_completed', 'logs', 'created_at',
            'benefits', 'items', 'media', 'status',
            # Fase 9+10 (2026-09-23): description/subheadline/cta_label/cta_url/terms nuevos;
            # target_audience ya existia en el modelo pero nunca se expuso aqui.
            'description', 'subheadline', 'cta_label', 'cta_url', 'terms',
            'valid_from', 'valid_until', 'target_audience',
        ]

    def validate_channels(self, value):
        # Fase 24 (2026-09-23): antes un slug inventado en `channels` (ej. "sms") se guardaba sin
        # error y solo se filtraba en silencio al enviar/previsualizar (`AVAILABLE_CHANNELS`,
        # views.py) -- inconsistente con el resto del contrato (items/uuid invalido SI rechaza con
        # 400 desde Fase 4). Mismo criterio aplicado aqui: validar en escritura, no solo en lectura.
        from marketing.channels.registry import AVAILABLE_CHANNELS
        invalid = [c for c in (value or []) if c not in AVAILABLE_CHANNELS]
        if invalid:
            raise serializers.ValidationError(
                f"Canal(es) invalido(s): {invalid}. Disponibles: {AVAILABLE_CHANNELS}."
            )
        return value

    def get_status(self, obj):
        """
        Fase 17 (2026-09-23): estado DERIVADO, no un campo de BD nuevo -- is_completed/
        scheduled_at/sent_at/logs ya bastan para representar DRAFT/SCHEDULED/RUNNING/COMPLETED
        sin otra migracion ni un enum paralelo que se pueda desincronizar del resto de campos.
        RUNNING = ya se disparo al menos un intento de envio (existe CampaignLog) pero no todos
        estan completos aun.
        """
        if obj.is_completed:
            return 'COMPLETED'
        if obj.logs.exists():
            return 'RUNNING'
        from django.utils import timezone
        if obj.scheduled_at and obj.scheduled_at > timezone.now():
            return 'SCHEDULED'
        return 'DRAFT'

    def validate(self, attrs):
        valid_from = attrs.get('valid_from', getattr(self.instance, 'valid_from', None))
        valid_until = attrs.get('valid_until', getattr(self.instance, 'valid_until', None))
        if valid_from and valid_until and valid_until < valid_from:
            raise serializers.ValidationError(
                {'valid_until': 'No puede ser anterior a valid_from.'}
            )
        return attrs

    def _create_items(self, campaign, items_data):
        for item in items_data:
            app_label, model_name = _SOURCE_TYPE_TO_CTYPE[item['type']]
            content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            CampaignItem.objects.create(
                campaign=campaign, content_type=content_type,
                object_uuid=item['uuid'], quantity=item.get('quantity', 1),
            )

    def create(self, validated_data):
        benefits_data = validated_data.pop('benefits', [])
        items_data = validated_data.pop('items', [])
        campaign = MarketingCampaign.objects.create(**validated_data)
        for benefit in benefits_data:
            CampaignBenefit.objects.create(campaign=campaign, **benefit)
        self._create_items(campaign, items_data)
        return campaign

    def update(self, instance, validated_data):
        benefits_data = validated_data.pop('benefits', None)
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if benefits_data is not None:
            instance.benefits.all().delete()
            for benefit in benefits_data:
                CampaignBenefit.objects.create(campaign=instance, **benefit)
        if items_data is not None:
            instance.items.all().delete()
            self._create_items(instance, items_data)
        return instance


class FlashOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashOffer
        fields = [
            'id', 'uuid', 'name', 'description', 'discount_percentage',
            'start_time', 'end_time', 'is_active', 'created_at'
        ]

class AgentRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRun
        fields = [
            'id', 'uuid', 'triggered_by', 'status', 'llm_provider',
            'llm_decision', 'campaign', 'created_at'
        ]

class ConsolidatedDashboardSerializer(serializers.Serializer):
    platform_overview = serializers.DictField()
    shop = serializers.DictField()
    renting = serializers.DictField()
    technical_services = serializers.DictField()
