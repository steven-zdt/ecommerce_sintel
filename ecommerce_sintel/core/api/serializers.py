from django.utils.html import strip_tags
from rest_framework import serializers
from core.models import (
    HomeBanner, HomeModuleConfig, HomeCard, HomeCardGroup, FooterLink, FooterGroup, NavbarLink, FooterCTAConfig,
    BrandSliderItem, BrandSliderConfig, AboutUsConfig, AboutUsValue,
    FeatureBannerSection, FeatureBannerBlock,
)


# Mapa curado de atajos de icono -> clase real de Bootstrap Icons. Se aplica
# antes de guardar (FooterGroup/FooterLink) para que el admin pueda escribir
# "telephone"/"camera"/"shield"/"alarm" sin conocer el nombre exacto de la
# libreria. Un simple prefijo 'bi-' no alcanza para camera/shield/alarm (el
# icono real no es un prefijo literal de la palabra).
ICON_SHORTHAND_MAP = {
    'telephone': 'bi-telephone', 'house': 'bi-house', 'facebook': 'bi-facebook',
    'instagram': 'bi-instagram', 'linkedin': 'bi-linkedin', 'shop': 'bi-shop',
    'camera': 'bi-camera-video', 'shield': 'bi-shield-check', 'alarm': 'bi-bell',
    'building': 'bi-building', 'people': 'bi-people', 'truck': 'bi-truck',
}


def normalize_icon_class(value):
    value = (value or '').strip()
    if not value:
        return ''
    if value.startswith('bi-'):
        return value
    return ICON_SHORTHAND_MAP.get(value, f'bi-{value}')


def _strip_html_fields(attrs: dict) -> dict:
    """
    Defensa en profundidad contra XSS almacenado: estos campos se sirven tal
    cual en endpoints 100% publicos y sin autenticacion (home-feed/footer/
    site-config). Ninguno esta pensado para admitir HTML enriquecido, asi que
    quitar las etiquetas es seguro y no le resta funcionalidad al Visual
    Builder.
    """
    for key, value in attrs.items():
        if isinstance(value, str):
            attrs[key] = strip_tags(value).strip()
    return attrs


# ── Home public feed serializers ──────────────────────────────────────────────

class FlashOfferCardSerializer(serializers.Serializer):
    """Serializer para FlashOffer en la Home publica."""
    uuid              = serializers.UUIDField()
    name              = serializers.CharField()
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    ends_at           = serializers.DateTimeField(source='end_time')
    seconds_remaining = serializers.SerializerMethodField()
    variant_type      = serializers.SerializerMethodField()
    item_uuid         = serializers.SerializerMethodField()
    item_name         = serializers.SerializerMethodField()
    item_url          = serializers.SerializerMethodField()
    item_thumbnail    = serializers.SerializerMethodField()

    def get_seconds_remaining(self, obj):
        from django.utils import timezone
        delta = obj.end_time - timezone.now()
        return max(0, int(delta.total_seconds()))

    def get_variant_type(self, obj):
        if obj.variant_id:
            return 'product'
        if obj.service_variant_id:
            return 'service'
        if obj.equipment_variant_id:
            return 'rental'
        return None

    def get_item_uuid(self, obj):
        if obj.variant and obj.variant.product:
            return str(obj.variant.product.uuid)
        if obj.service_variant and obj.service_variant.service:
            return str(obj.service_variant.service.uuid)
        if obj.equipment_variant and obj.equipment_variant.equipment:
            return str(obj.equipment_variant.equipment.uuid)
        return None

    def get_item_name(self, obj):
        if obj.variant and obj.variant.product:
            return obj.variant.product.name
        if obj.service_variant and obj.service_variant.service:
            return obj.service_variant.service.name
        if obj.equipment_variant and obj.equipment_variant.equipment:
            return obj.equipment_variant.equipment.name
        return obj.name

    def get_item_url(self, obj):
        if obj.variant and obj.variant.product:
            return f'/tienda/producto/{obj.variant.product.uuid}'
        if obj.service_variant and obj.service_variant.service:
            return f'/servicios/{obj.service_variant.service.uuid}'
        if obj.equipment_variant and obj.equipment_variant.equipment:
            return f'/alquiler/equipo/{obj.equipment_variant.equipment.uuid}'
        return '/'

    def get_item_thumbnail(self, obj):
        request = self.context.get('request')
        img = None
        if obj.variant and hasattr(obj.variant, 'product'):
            product = obj.variant.product
            if hasattr(product, 'images'):
                # Use prefetched images (via list_active_flash_offers prefetch_related)
                # to avoid N+1: sort in Python instead of issuing per-product queries.
                all_images = list(product.images.all())
                primary = next((i for i in all_images if i.is_primary), None)
                if not primary and all_images:
                    primary = all_images[0]
                if primary:
                    img = primary.image
        if img and request:
            return request.build_absolute_uri(img.url)
        return None


class FeaturedProductCardSerializer(serializers.Serializer):
    uuid          = serializers.UUIDField()
    name          = serializers.CharField()
    slug          = serializers.CharField()
    type          = serializers.SerializerMethodField()
    is_featured   = serializers.BooleanField()
    category_name = serializers.SerializerMethodField()
    min_price     = serializers.SerializerMethodField()
    thumbnail     = serializers.SerializerMethodField()
    item_url      = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'product'

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_min_price(self, obj):
        prices = [v.price for v in obj.variants.all() if v.price is not None]
        if prices:
            return str(min(prices))
        return None

    def get_thumbnail(self, obj):
        # obj.images.all() reutiliza el cache de prefetch_related('images') declarado en
        # list_featured(); un .filter()/.first() explicito en el manager lo ignora y dispara
        # hasta 2 queries nuevas por item (mismo patron de bug encontrado y corregido el
        # 2026-07-03 en TechnicalServiceSerializer.get_variants() -- Fase 6, auditoria de BD).
        request = self.context.get('request')
        images = list(obj.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        if primary and request:
            return request.build_absolute_uri(primary.image.url)
        return None

    def get_item_url(self, obj):
        return f'/tienda/producto/{obj.uuid}'


class FeaturedEquipmentCardSerializer(serializers.Serializer):
    uuid          = serializers.UUIDField()
    name          = serializers.CharField()
    slug          = serializers.CharField()
    type          = serializers.SerializerMethodField()
    is_featured   = serializers.BooleanField()
    category_name = serializers.SerializerMethodField()
    min_price     = serializers.SerializerMethodField()
    thumbnail     = serializers.SerializerMethodField()
    item_url      = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'rental'

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_min_price(self, obj):
        prices = [v.rental_price_per_day for v in obj.variants.all() if v.rental_price_per_day is not None]
        if prices:
            return str(min(prices))
        return None

    def get_thumbnail(self, obj):
        # obj.images.all() reutiliza el cache de prefetch_related('images') declarado en
        # list_featured(); un .filter()/.first() explicito en el manager lo ignora y dispara
        # hasta 2 queries nuevas por item (mismo patron de bug encontrado y corregido el
        # 2026-07-03 en TechnicalServiceSerializer.get_variants() -- Fase 6, auditoria de BD).
        request = self.context.get('request')
        images = list(obj.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        if primary and request:
            return request.build_absolute_uri(primary.image.url)
        return None

    def get_item_url(self, obj):
        return f'/alquiler/equipo/{obj.uuid}'


class FeaturedServiceCardSerializer(serializers.Serializer):
    uuid          = serializers.UUIDField()
    name          = serializers.CharField()
    slug          = serializers.CharField()
    type          = serializers.SerializerMethodField()
    is_featured   = serializers.BooleanField()
    category_name = serializers.SerializerMethodField()
    thumbnail     = serializers.SerializerMethodField()
    item_url      = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'service'

    def get_category_name(self, obj):
        return obj.category.name if obj.category else None

    def get_thumbnail(self, obj):
        # obj.images.all() reutiliza el cache de prefetch_related('images') declarado en
        # list_featured(); un .filter()/.first() explicito en el manager lo ignora y dispara
        # hasta 2 queries nuevas por item (mismo patron de bug encontrado y corregido el
        # 2026-07-03 en TechnicalServiceSerializer.get_variants() -- Fase 6, auditoria de BD).
        request = self.context.get('request')
        images = list(obj.images.all())
        primary = next((img for img in images if img.is_primary), None) or (images[0] if images else None)
        if primary and request:
            return request.build_absolute_uri(primary.image.url)
        return None

    def get_item_url(self, obj):
        return f'/servicios/{obj.uuid}'


# ── Admin Home Config serializers ─────────────────────────────────────────────

class HomeBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = [
            'id', 'uuid', 'title', 'subtitle', 'eyebrow',
            'image', 'video', 'background_color',
            'link_url', 'link_label',
            'cta_ghost_label', 'cta_ghost_url',
            'is_active', 'display_order', 'created_at',
        ]


class HomeBannerInputSerializer(serializers.Serializer):
    title            = serializers.CharField(max_length=255)
    subtitle         = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    eyebrow          = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    link_url         = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    link_label       = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    background_color = serializers.CharField(max_length=30,  required=False, allow_blank=True, default='')
    cta_ghost_label  = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    cta_ghost_url    = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    display_order    = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active        = serializers.BooleanField(required=False, default=True)
    image            = serializers.ImageField(required=False, allow_null=True)
    video            = serializers.FileField(required=False, allow_null=True)
    remove_image     = serializers.BooleanField(required=False, default=False)
    remove_video     = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


class HomeModuleConfigSerializer(serializers.ModelSerializer):
    module_label = serializers.SerializerMethodField()
    module_url   = serializers.SerializerMethodField()
    module_icon  = serializers.SerializerMethodField()
    module_color = serializers.SerializerMethodField()
    is_core      = serializers.SerializerMethodField()

    _CORE_KEYS = {
        HomeModuleConfig.MODULE_SHOP,
        HomeModuleConfig.MODULE_RENTING,
        HomeModuleConfig.MODULE_SERVICES,
        HomeModuleConfig.MODULE_QUOTES,
    }

    class Meta:
        model = HomeModuleConfig
        fields = [
            'id', 'uuid', 'module_key', 'module_label', 'module_url',
            'module_icon', 'module_color', 'background_image',
            'custom_label', 'custom_icon', 'custom_url', 'custom_color',
            'is_visible', 'display_order', 'featured_items_limit',
            'is_core', 'display_type', 'layout_config',
        ]

    def _meta(self, obj):
        return HomeModuleConfig.MODULE_META.get(obj.module_key, {})

    def get_is_core(self, obj):
        return obj.module_key in self._CORE_KEYS

    def get_module_label(self, obj):
        if obj.custom_label:
            return obj.custom_label
        return self._meta(obj).get('label', obj.module_key)

    def get_module_url(self, obj):
        if obj.custom_url:
            return obj.custom_url
        return self._meta(obj).get('url', '/')

    def get_module_icon(self, obj):
        if obj.custom_icon:
            return obj.custom_icon
        return self._meta(obj).get('icon', 'bi-grid')

    def get_module_color(self, obj):
        if obj.custom_color:
            return obj.custom_color
        return self._meta(obj).get('color', '#6b7280')


def _parse_layout_config(value):
    import json as _json
    if isinstance(value, str):
        try:
            return _json.loads(value)
        except (ValueError, TypeError):
            raise serializers.ValidationError("layout_config debe ser JSON valido.")
    return value if isinstance(value, dict) else {}


class HomeModuleConfigInputSerializer(serializers.Serializer):
    is_visible               = serializers.BooleanField(required=False)
    display_order            = serializers.IntegerField(required=False, min_value=0)
    featured_items_limit     = serializers.IntegerField(required=False, min_value=1, max_value=20)
    custom_label             = serializers.CharField(max_length=255, required=False, allow_blank=True)
    custom_icon              = serializers.CharField(max_length=100, required=False, allow_blank=True)
    custom_url               = serializers.CharField(max_length=300, required=False, allow_blank=True)
    custom_color             = serializers.CharField(max_length=30,  required=False, allow_blank=True)
    background_image         = serializers.ImageField(required=False, allow_null=True)
    remove_background_image  = serializers.BooleanField(required=False, default=False)
    display_type             = serializers.CharField(max_length=30, required=False)
    layout_config            = serializers.JSONField(required=False, default=dict)

    def validate_layout_config(self, value):
        return _parse_layout_config(value)


class HomeModuleCreateSerializer(serializers.Serializer):
    module_key           = serializers.CharField(max_length=40)
    custom_label         = serializers.CharField(max_length=255, required=False, default='')
    custom_icon          = serializers.CharField(max_length=100, required=False, default='bi-grid')
    custom_url           = serializers.CharField(max_length=300, required=False, default='/')
    custom_color         = serializers.CharField(max_length=30,  required=False, default='#6b7280')
    is_visible           = serializers.BooleanField(required=False, default=True)
    display_order        = serializers.IntegerField(required=False, default=0, min_value=0)
    featured_items_limit = serializers.IntegerField(required=False, default=8, min_value=1, max_value=20)
    background_image     = serializers.ImageField(required=False, allow_null=True)
    display_type         = serializers.CharField(max_length=30, required=False, default='grid')
    layout_config        = serializers.JSONField(required=False, default=dict)

    def validate_layout_config(self, value):
        return _parse_layout_config(value)


# ── Home Cards serializers ────────────────────────────────────────────────────

class HomeCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeCard
        fields = [
            'id', 'uuid', 'title', 'subtitle', 'description',
            'group_name', 'icon_class', 'background_color',
            'image', 'video',
            'redirect_url', 'display_order', 'is_active', 'created_at',
            'card_type', 'animation', 'is_featured', 'priority', 'badge_text', 'badge_color',
            'url_type', 'url_target', 'stats',
            'secondary_label', 'secondary_icon', 'secondary_url', 'secondary_url_type', 'secondary_target',
        ]


class HomeCardInputSerializer(serializers.Serializer):
    title            = serializers.CharField(max_length=255)
    subtitle         = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    description      = serializers.CharField(required=False, allow_blank=True, default='')
    group_name       = serializers.CharField(max_length=150)
    icon_class       = serializers.CharField(max_length=100, required=False, default='bi-star')
    background_color = serializers.CharField(max_length=30, required=False, default='#3b82f6')
    image            = serializers.ImageField(required=False, allow_null=True)
    video            = serializers.FileField(required=False, allow_null=True)
    redirect_url     = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    display_order    = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active        = serializers.BooleanField(required=False, default=True)
    card_type        = serializers.CharField(max_length=30, required=False, default='vertical')
    animation        = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    is_featured      = serializers.BooleanField(required=False, default=False)
    priority         = serializers.IntegerField(required=False, default=0, min_value=0)
    badge_text       = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    badge_color      = serializers.CharField(max_length=30, required=False, allow_blank=True, default='#2563eb')
    remove_image     = serializers.BooleanField(required=False, default=False)
    remove_video     = serializers.BooleanField(required=False, default=False)

    url_type    = serializers.CharField(max_length=10, required=False, default='INTERNA')
    url_target  = serializers.CharField(max_length=10, required=False, default='_self')
    stats       = serializers.JSONField(required=False, default=list)

    secondary_label    = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    secondary_icon     = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    secondary_url      = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    secondary_url_type = serializers.CharField(max_length=10, required=False, default='INTERNA')
    secondary_target   = serializers.CharField(max_length=10, required=False, default='_self')

    def validate(self, attrs):
        attrs = _strip_html_fields(attrs)
        if isinstance(attrs.get('stats'), list):
            attrs['stats'] = [
                {**s, 'label': strip_tags(s.get('label', '')).strip(), 'value': strip_tags(s.get('value', '')).strip()}
                if isinstance(s, dict) else s
                for s in attrs['stats']
            ]
        return attrs


# ── Home Card Group serializers ──────────────────────────────────────────────

class HomeCardGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeCardGroup
        fields = [
            'uuid', 'name', 'title', 'display_order', 'is_visible',
            'subtitle', 'description', 'bg_color', 'bg_image',
            'layout_type', 'padding', 'divider', 'columns', 'glass', 'hover',
            'columns_tablet', 'columns_mobile', 'gap',
            'carousel_autoplay', 'carousel_loop', 'carousel_speed',
            'show_arrows', 'show_indicators',
        ]


class HomeCardGroupInputSerializer(serializers.Serializer):
    name          = serializers.CharField(max_length=150)
    title         = serializers.CharField(max_length=255)
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_visible    = serializers.BooleanField(required=False, default=True)
    subtitle      = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    description   = serializers.CharField(required=False, allow_blank=True, default='')
    bg_color      = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    bg_image      = serializers.ImageField(required=False, allow_null=True)
    remove_bg_image = serializers.BooleanField(required=False, default=False)
    layout_type   = serializers.CharField(max_length=30, required=False, default='grid')
    padding       = serializers.CharField(max_length=20, required=False, default='normal')
    divider       = serializers.BooleanField(required=False, default=False)
    columns       = serializers.IntegerField(required=False, default=3, min_value=1, max_value=6)
    glass         = serializers.BooleanField(required=False, default=False)
    hover         = serializers.CharField(max_length=20, required=False, default='lift')

    columns_tablet = serializers.IntegerField(required=False, default=2, min_value=1, max_value=6)
    columns_mobile = serializers.IntegerField(required=False, default=1, min_value=1, max_value=6)
    gap            = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, default=1.25, min_value=0)

    carousel_autoplay = serializers.BooleanField(required=False, default=False)
    carousel_loop     = serializers.BooleanField(required=False, default=True)
    carousel_speed    = serializers.IntegerField(required=False, default=40, min_value=1)
    show_arrows       = serializers.BooleanField(required=False, default=True)
    show_indicators   = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        return _strip_html_fields(attrs)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


# ── Footer Group serializers ──────────────────────────────────────────────────

class FooterGroupSerializer(serializers.ModelSerializer):
    links_count = serializers.SerializerMethodField()

    class Meta:
        model = FooterGroup
        fields = [
            'uuid', 'title', 'icon_class', 'description', 'background_color',
            'text_color', 'display_order', 'is_active', 'links_count',
        ]

    def get_links_count(self, obj):
        # N+1 fix: uses prefetched links instead of a COUNT query per group
        return sum(1 for l in obj.links.all() if not l.is_deleted)


class FooterGroupInputSerializer(serializers.Serializer):
    title            = serializers.CharField(max_length=150)
    icon_class       = serializers.CharField(max_length=100, required=False, allow_blank=True, default='bi-folder')
    description      = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    background_color = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    text_color       = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    display_order    = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active        = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs = _strip_html_fields(attrs)
        if 'icon_class' in attrs:
            attrs['icon_class'] = normalize_icon_class(attrs['icon_class'])
        return attrs


class FooterGroupReorderSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class FooterGroupPublicSerializer(serializers.ModelSerializer):
    links = serializers.SerializerMethodField()

    class Meta:
        model = FooterGroup
        fields = [
            'uuid', 'title', 'icon_class', 'description',
            'background_color', 'text_color', 'display_order', 'links',
        ]

    def get_links(self, obj):
        # `visible_links` viene del Prefetch(to_attr=...) en FooterSelector.build_footer_payload();
        # evita una query N+1 por grupo.
        return FooterLinkSerializer(obj.visible_links, many=True).data


# ── Footer Link serializers ───────────────────────────────────────────────────

class FooterLinkSerializer(serializers.ModelSerializer):
    group = serializers.UUIDField(source='group.uuid', read_only=True)

    class Meta:
        model = FooterLink
        fields = [
            'id', 'uuid', 'title', 'url', 'category', 'group',
            'icon_class', 'open_new_tab', 'display_order', 'is_active', 'created_at',
        ]


class FooterLinkInputSerializer(serializers.Serializer):
    title         = serializers.CharField(max_length=255)
    url           = serializers.CharField(max_length=500)
    # 'social' se elimino del alcance de core (migrado a organization.SocialLink,
    # ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md) -- solo 'nav' es valido aqui.
    # dashboard/api/views.py sigue aceptando 'social' en el payload y lo enruta
    # a OrganizationCommands antes de llegar a este serializer.
    category      = serializers.ChoiceField(choices=[('nav', 'nav')], default='nav')
    group         = serializers.UUIDField()
    icon_class    = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    open_new_tab  = serializers.BooleanField(required=False, default=False)
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active     = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        attrs = _strip_html_fields(attrs)
        if 'icon_class' in attrs:
            attrs['icon_class'] = normalize_icon_class(attrs['icon_class'])
        return attrs


class FooterLinkReorderSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


def social_link_to_footer_link_shape(link):
    """
    Adaptador: organization.SocialLink -> misma forma JSON que emitia
    core.FooterLink(category='social') antes de la migracion 2026-07-12, para
    no romper el contrato publico de /api/v1/core/footer/ ni el panel admin
    (/panel/home-config, tab "Footer") sin tocar el frontend todavia (Fase 6,
    "Frontend SPA" es el ultimo consumidor en migrar).
    """
    return {
        'id': link.id,
        'uuid': str(link.uuid),
        'title': link.platform,
        'url': link.url,
        'category': 'social',
        'group_name': '',
        'icon_class': link.icon_class,
        'display_order': link.display_order,
        'is_active': link.is_active,
        'created_at': link.created_at,
    }


class NavbarLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = NavbarLink
        fields = ['uuid', 'label', 'url', 'icon_class', 'display_order', 'is_visible', 'open_in_new_tab']


class NavbarLinkInputSerializer(serializers.Serializer):
    label           = serializers.CharField(max_length=150)
    url             = serializers.CharField(max_length=300)
    icon_class      = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    display_order   = serializers.IntegerField(required=False, default=0)
    is_visible      = serializers.BooleanField(required=False, default=True)
    open_in_new_tab = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


# ── Footer CTA Config serializers ─────────────────────────────────────────────

class FooterCTAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = FooterCTAConfig
        fields = [
            'uuid', 'eyebrow', 'title_prefix', 'title_highlighted',
            'subtitle', 'btn_primary_label', 'btn_primary_url',
            'btn_ghost_label', 'btn_ghost_url', 'is_active', 'updated_at',
        ]


class FooterCTAConfigInputSerializer(serializers.Serializer):
    eyebrow           = serializers.CharField(max_length=150, required=False, allow_blank=True)
    title_prefix      = serializers.CharField(max_length=255, required=False, allow_blank=True)
    title_highlighted = serializers.CharField(max_length=255, required=False, allow_blank=True)
    subtitle          = serializers.CharField(max_length=500, required=False, allow_blank=True)
    btn_primary_label = serializers.CharField(max_length=150, required=False, allow_blank=True)
    btn_primary_url   = serializers.CharField(max_length=300, required=False, allow_blank=True)
    btn_ghost_label   = serializers.CharField(max_length=150, required=False, allow_blank=True)
    btn_ghost_url     = serializers.CharField(max_length=300, required=False, allow_blank=True)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


# ── Brand Slider serializers ──────────────────────────────────────────────────

class BrandSliderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandSliderItem
        fields = [
            'id', 'uuid', 'name', 'logo', 'website',
            'display_order', 'is_active', 'open_new_tab', 'created_at',
        ]


class BrandSliderItemInputSerializer(serializers.Serializer):
    name          = serializers.CharField(max_length=150)
    logo          = serializers.ImageField(required=False, allow_null=True)
    website       = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active     = serializers.BooleanField(required=False, default=True)
    open_new_tab  = serializers.BooleanField(required=False, default=True)
    remove_logo   = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


# ── About Us (Sobre Nosotros) serializers ─────────────────────────────────────

class AboutUsValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUsValue
        fields = [
            'id', 'uuid', 'title', 'description', 'icon_class',
            'display_order', 'is_active', 'created_at',
        ]


class AboutUsValueInputSerializer(serializers.Serializer):
    title         = serializers.CharField(max_length=150)
    description   = serializers.CharField(required=False, allow_blank=True, default='')
    icon_class    = serializers.CharField(max_length=100, required=False, default='bi-gem')
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active     = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if 'icon_class' in attrs:
            attrs['icon_class'] = normalize_icon_class(attrs['icon_class']) or 'bi-gem'
        return _strip_html_fields(attrs)


class AboutUsValueReorderSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class AboutUsConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutUsConfig
        fields = [
            'uuid', 'title', 'subtitle', 'hero_image', 'history',
            'mission', 'vision', 'is_visible', 'updated_at',
        ]


class AboutUsConfigInputSerializer(serializers.Serializer):
    title             = serializers.CharField(max_length=255, required=False, allow_blank=True)
    subtitle          = serializers.CharField(max_length=500, required=False, allow_blank=True)
    hero_image        = serializers.ImageField(required=False, allow_null=True)
    remove_hero_image = serializers.BooleanField(required=False, default=False)
    history           = serializers.CharField(required=False, allow_blank=True)
    mission           = serializers.CharField(required=False, allow_blank=True)
    vision            = serializers.CharField(required=False, allow_blank=True)
    is_visible        = serializers.BooleanField(required=False)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


class BrandSliderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandSliderConfig
        fields = [
            'uuid', 'title', 'subtitle', 'autoplay', 'speed', 'direction', 'loop',
            'pause_on_hover', 'items_desktop', 'items_tablet', 'items_mobile',
            'background_color', 'padding_top', 'padding_bottom', 'is_visible', 'updated_at',
        ]


class BrandSliderConfigInputSerializer(serializers.Serializer):
    title            = serializers.CharField(max_length=255, required=False, allow_blank=True)
    subtitle         = serializers.CharField(max_length=500, required=False, allow_blank=True)
    autoplay         = serializers.BooleanField(required=False)
    speed            = serializers.IntegerField(required=False, min_value=100)
    direction        = serializers.ChoiceField(choices=BrandSliderConfig.DIRECTION_CHOICES, required=False)
    loop             = serializers.BooleanField(required=False)
    pause_on_hover   = serializers.BooleanField(required=False)
    items_desktop    = serializers.IntegerField(required=False, min_value=1, max_value=12)
    items_tablet     = serializers.IntegerField(required=False, min_value=1, max_value=10)
    items_mobile     = serializers.IntegerField(required=False, min_value=1, max_value=6)
    background_color = serializers.CharField(max_length=30, required=False, allow_blank=True)
    padding_top      = serializers.ChoiceField(choices=BrandSliderConfig.PADDING_CHOICES, required=False)
    padding_bottom   = serializers.ChoiceField(choices=BrandSliderConfig.PADDING_CHOICES, required=False)
    is_visible       = serializers.BooleanField(required=False)

    def validate(self, attrs):
        return _strip_html_fields(attrs)


# ── Feature Banner serializers (2026-08-06) ────────────────────────────────────

class FeatureBannerBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureBannerBlock
        fields = [
            'uuid', 'layout_type', 'title', 'title_highlighted', 'description',
            'image', 'image_alt', 'benefits', 'stats', 'badge_text', 'badge_color',
            'btn_primary_text', 'btn_primary_icon', 'btn_primary_color', 'btn_primary_style',
            'btn_primary_url', 'btn_primary_url_type', 'btn_primary_target',
            'btn_secondary_text', 'btn_secondary_icon', 'btn_secondary_color', 'btn_secondary_style',
            'btn_secondary_url', 'btn_secondary_url_type', 'btn_secondary_target',
            'display_order', 'is_active',
        ]


class FeatureBannerBlockInputSerializer(serializers.Serializer):
    layout_type       = serializers.ChoiceField(choices=FeatureBannerBlock.LAYOUT_CHOICES, required=False, default=FeatureBannerBlock.LAYOUT_IMAGE_LEFT)
    title             = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    title_highlighted = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    description       = serializers.CharField(required=False, allow_blank=True, default='')
    image             = serializers.ImageField(required=False, allow_null=True)
    image_alt         = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    benefits          = serializers.JSONField(required=False, default=list)
    stats             = serializers.JSONField(required=False, default=list)
    badge_text        = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    badge_color       = serializers.CharField(max_length=30, required=False, allow_blank=True, default='#f59e0b')

    btn_primary_text     = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    btn_primary_icon     = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    btn_primary_color    = serializers.CharField(max_length=30, required=False, allow_blank=True, default='#2563eb')
    btn_primary_style    = serializers.ChoiceField(choices=FeatureBannerBlock.BTN_STYLE_CHOICES, required=False, default=FeatureBannerBlock.BTN_STYLE_FILLED)
    btn_primary_url      = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    btn_primary_url_type = serializers.ChoiceField(choices=FeatureBannerBlock.URL_TYPE_CHOICES, required=False, default=FeatureBannerBlock.URL_TYPE_INTERNA)
    btn_primary_target   = serializers.ChoiceField(choices=FeatureBannerBlock.TARGET_CHOICES, required=False, default=FeatureBannerBlock.TARGET_SELF)

    btn_secondary_text     = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    btn_secondary_icon     = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    btn_secondary_color    = serializers.CharField(max_length=30, required=False, allow_blank=True, default='#2563eb')
    btn_secondary_style    = serializers.ChoiceField(choices=FeatureBannerBlock.BTN_STYLE_CHOICES, required=False, default=FeatureBannerBlock.BTN_STYLE_OUTLINE)
    btn_secondary_url      = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    btn_secondary_url_type = serializers.ChoiceField(choices=FeatureBannerBlock.URL_TYPE_CHOICES, required=False, default=FeatureBannerBlock.URL_TYPE_INTERNA)
    btn_secondary_target   = serializers.ChoiceField(choices=FeatureBannerBlock.TARGET_CHOICES, required=False, default=FeatureBannerBlock.TARGET_SELF)

    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active     = serializers.BooleanField(required=False, default=True)
    remove_image  = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        attrs = _strip_html_fields(attrs)
        if isinstance(attrs.get('benefits'), list):
            attrs['benefits'] = [
                {**b, 'text': strip_tags(b.get('text', '')).strip()} if isinstance(b, dict) else b
                for b in attrs['benefits']
            ]
        return attrs


class FeatureBannerSectionSerializer(serializers.ModelSerializer):
    blocks = FeatureBannerBlockSerializer(many=True, read_only=True)

    class Meta:
        model = FeatureBannerSection
        fields = [
            'uuid', 'title', 'subtitle', 'description', 'is_visible', 'display_order', 'theme',
            'background_type', 'background_color', 'background_gradient_from',
            'background_gradient_to', 'background_image', 'overlay_enabled', 'overlay_opacity',
            'padding', 'blocks',
        ]


class FeatureBannerSectionInputSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    subtitle    = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    is_visible    = serializers.BooleanField(required=False, default=True)
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    theme = serializers.ChoiceField(choices=FeatureBannerSection.THEME_CHOICES, required=False, default=FeatureBannerSection.THEME_LIGHT)

    background_type          = serializers.ChoiceField(choices=FeatureBannerSection.BACKGROUND_TYPE_CHOICES, required=False, default=FeatureBannerSection.BG_COLOR)
    background_color         = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    background_gradient_from = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    background_gradient_to   = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    background_image         = serializers.ImageField(required=False, allow_null=True)
    remove_background_image  = serializers.BooleanField(required=False, default=False)
    overlay_enabled = serializers.BooleanField(required=False, default=False)
    overlay_opacity = serializers.IntegerField(required=False, default=45, min_value=0, max_value=100)

    padding = serializers.ChoiceField(choices=HomeCardGroup.PADDING_CHOICES, required=False, default=HomeCardGroup.PADDING_NORMAL)

    def validate(self, attrs):
        return _strip_html_fields(attrs)
