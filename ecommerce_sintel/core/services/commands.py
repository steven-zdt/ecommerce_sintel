# core/services/commands.py
# Extraido de selectors.py — Sprint 1 refactorizacion (2026-07-16)
from django.db import transaction
from django.utils import timezone
from django.db.models import Prefetch
from core.models import (
    HomeBanner, HomeModuleConfig, HomeCard, HomeCardGroup, FooterLink, FooterGroup, NavbarLink, FooterCTAConfig,
    BrandSliderItem, BrandSliderConfig, AboutUsConfig, AboutUsValue,
)
from core.services.selectors import HomeConfigSelector


class HomeConfigCommands:

    @staticmethod
    @transaction.atomic
    def create_banner(title, subtitle='', link_url='', link_label='', display_order=0, image=None, video=None):
        return HomeBanner.objects.create(
            title=title,
            subtitle=subtitle,
            link_url=link_url,
            link_label=link_label,
            display_order=display_order,
            image=image,
            video=video,
        )

    @staticmethod
    @transaction.atomic
    def update_banner(banner, data):
        if data.pop('remove_image', False):
            banner.image = None
        if data.pop('remove_video', False):
            banner.video = None
        allowed = (
            'title', 'subtitle', 'eyebrow',
            'link_url', 'link_label',
            'background_color', 'cta_ghost_label', 'cta_ghost_url',
            'display_order', 'is_active', 'image', 'video',
        )
        for field in allowed:
            if field in data:
                setattr(banner, field, data[field])
        banner.save()
        return banner

    @staticmethod
    def deactivate_banner(banner):
        banner.is_active = False
        banner.is_deleted = True
        banner.save(update_fields=['is_active', 'is_deleted'])

    @staticmethod
    @transaction.atomic
    def update_module_config(config, data):
        allowed = (
            'is_visible', 'display_order', 'featured_items_limit',
            'custom_label', 'custom_icon', 'custom_url', 'custom_color',
            'background_image', 'display_type', 'layout_config',
        )
        if data.pop('remove_background_image', False):
            config.background_image = None
        for field in allowed:
            if field in data:
                setattr(config, field, data[field])
        config.save()
        return config

    @staticmethod
    @transaction.atomic
    def create_module(module_key, custom_label='', custom_icon='bi-grid', custom_url='/',
                      custom_color='#6b7280', is_visible=True, display_order=0,
                      featured_items_limit=8, background_image=None,
                      display_type='grid', layout_config=None):
        return HomeModuleConfig.objects.create(
            module_key=module_key,
            custom_label=custom_label,
            custom_icon=custom_icon,
            custom_url=custom_url,
            custom_color=custom_color,
            is_visible=is_visible,
            display_order=display_order,
            featured_items_limit=featured_items_limit,
            background_image=background_image,
            display_type=display_type,
            layout_config=layout_config or {},
        )

    @staticmethod
    @transaction.atomic
    def delete_module(config):
        config.is_deleted = True
        config.save(update_fields=['is_deleted'])


class HomeCardSelector:

    @staticmethod
    def list_active():
        return HomeCard.objects.filter(is_active=True, is_deleted=False).order_by('group_name', 'display_order')

    @staticmethod
    def list_for_admin():
        return HomeCard.objects.filter(is_deleted=False).order_by('group_name', 'display_order')

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(HomeCard, uuid=uuid, is_deleted=False)


class HomeCardGroupSelector:

    @staticmethod
    def list_all():
        return HomeCardGroup.objects.filter(is_deleted=False).order_by('display_order', 'name')

    @staticmethod
    def get_titles_map():
        return {g.name: g.title for g in HomeCardGroup.objects.filter(is_deleted=False, is_visible=True)}

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(HomeCardGroup, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_by_name(name):
        return HomeCardGroup.objects.filter(name=name, is_deleted=False).first()


class HomeCardGroupCommands:

    @staticmethod
    @transaction.atomic
    def upsert(name, title, display_order=0, is_visible=True, **kwargs):
        group = HomeCardGroupSelector.get_by_name(name)
        remove_bg_image = kwargs.pop('remove_bg_image', False)
        extra_fields = (
            'subtitle', 'description', 'bg_color', 'bg_image',
            'layout_type', 'padding', 'divider', 'columns', 'glass', 'hover',
        )
        if group:
            group.title         = title
            group.display_order = display_order
            group.is_visible    = is_visible
            if remove_bg_image:
                group.bg_image = None
            for field in extra_fields:
                if field in kwargs:
                    setattr(group, field, kwargs[field])
            group.save()
        else:
            create_kwargs = dict(
                name=name, title=title,
                display_order=display_order, is_visible=is_visible,
            )
            for field in extra_fields:
                if field in kwargs:
                    create_kwargs[field] = kwargs[field]
            group = HomeCardGroup.objects.create(**create_kwargs)
        return group

    @staticmethod
    @transaction.atomic
    def update(group, data):
        if data.pop('remove_bg_image', False):
            group.bg_image = None
        allowed = (
            'title', 'display_order', 'is_visible',
            'subtitle', 'description', 'bg_color', 'bg_image',
            'layout_type', 'padding', 'divider', 'columns', 'glass', 'hover',
        )
        for field in allowed:
            if field in data:
                setattr(group, field, data[field])
        group.save()
        return group

    @staticmethod
    @transaction.atomic
    def delete(group):
        group.is_deleted = True
        group.save(update_fields=['is_deleted'])


class HomeCardCommands:

    @staticmethod
    @transaction.atomic
    def create_card(title, subtitle='', description='', group_name='', icon_class='bi-star',
                    background_color='#3b82f6', redirect_url='', display_order=0,
                    image=None, video=None, card_type='vertical', animation='',
                    is_featured=False, priority=0, badge_text=''):
        return HomeCard.objects.create(
            title=title,
            subtitle=subtitle,
            description=description,
            group_name=group_name,
            icon_class=icon_class,
            background_color=background_color,
            redirect_url=redirect_url,
            display_order=display_order,
            image=image,
            video=video,
            card_type=card_type,
            animation=animation,
            is_featured=is_featured,
            priority=priority,
            badge_text=badge_text,
        )

    @staticmethod
    @transaction.atomic
    def update_card(card, data):
        if data.pop('remove_image', False):
            card.image = None
        if data.pop('remove_video', False):
            card.video = None
        allowed = (
            'title', 'subtitle', 'description', 'group_name', 'icon_class',
            'background_color', 'image', 'video', 'redirect_url', 'display_order', 'is_active',
            'card_type', 'animation', 'is_featured', 'priority', 'badge_text',
        )
        for field in allowed:
            if field in data:
                setattr(card, field, data[field])
        card.save()
        return card

    @staticmethod
    @transaction.atomic
    def delete_card(card):
        card.is_active = False
        card.is_deleted = True
        card.save(update_fields=['is_active', 'is_deleted'])


class HomeFeedSelector:
    """
    Agrega datos de multiples apps para alimentar la Home publica.
    Usa lazy imports para evitar imports circulares a nivel de modulo.
    Limite por seccion: configurable via HomeModuleConfig; default 8.
    """

    @staticmethod
    def _get_limit(module_key, default=8):
        try:
            cfg = HomeModuleConfig.objects.get(module_key=module_key, is_deleted=False)
            return cfg.featured_items_limit
        except HomeModuleConfig.DoesNotExist:
            return default

    @staticmethod
    def get_flash_offers():
        from marketing.services.selectors import MarketingSelector
        return MarketingSelector.list_active_flash_offers()

    @staticmethod
    def get_featured_products():
        from shop.services.selectors import ProductSelector
        limit = HomeFeedSelector._get_limit(HomeModuleConfig.MODULE_SHOP)
        return ProductSelector.list_featured()[:limit]

    @staticmethod
    def get_featured_equipment():
        from renting.services.selectors import RentingSelector
        limit = HomeFeedSelector._get_limit(HomeModuleConfig.MODULE_RENTING)
        return RentingSelector.list_featured()[:limit]

    @staticmethod
    def get_featured_services():
        from technical_services.services.selectors import ServiceSelector
        limit = HomeFeedSelector._get_limit(HomeModuleConfig.MODULE_SERVICES)
        return ServiceSelector.list_featured()[:limit]

    @staticmethod
    def get_module_configs(request=None):
        configs = list(HomeConfigSelector.list_module_configs())
        if not configs:
            configs = list(HomeConfigSelector.get_or_create_default_modules())
        result = []
        for cfg in configs:
            meta = HomeModuleConfig.MODULE_META.get(cfg.module_key, {})
            image_url = None
            if cfg.background_image:
                image_url = cfg.background_image.url
                if request is not None:
                    image_url = request.build_absolute_uri(image_url)
            result.append({
                'key':        cfg.module_key,
                'label':      cfg.custom_label  or meta.get('label', cfg.module_key),
                'url':        cfg.custom_url    or meta.get('url', '/'),
                'icon':       cfg.custom_icon   or meta.get('icon', 'bi-grid'),
                'color':      cfg.custom_color  or meta.get('color', '#6b7280'),
                'is_visible': cfg.is_visible,
                'background_image': image_url,
                'display_type':  cfg.display_type,
                'layout_config': cfg.layout_config,
            })
        return result

    @staticmethod
    def build_home_feed():
        """
        Consolida todos los datos de la Home en un unico dict.
        Cada seccion es una query independiente con select_related ya aplicado.
        """
        return {
            'modules':           HomeFeedSelector.get_module_configs(),
            'flash_offers':      list(HomeFeedSelector.get_flash_offers()),
            'featured_products': list(HomeFeedSelector.get_featured_products()),
            'featured_equipment':list(HomeFeedSelector.get_featured_equipment()),
            'featured_services': list(HomeFeedSelector.get_featured_services()),
        }


class NavbarLinkSelector:

    @staticmethod
    def list_visible():
        return NavbarLink.objects.filter(is_visible=True, is_deleted=False).order_by('display_order')

    @staticmethod
    def list_all():
        return NavbarLink.objects.filter(is_deleted=False).order_by('display_order')

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(NavbarLink, uuid=uuid, is_deleted=False)


class NavbarLinkCommands:

    @staticmethod
    @transaction.atomic
    def create(label, url, icon_class='', display_order=0, is_visible=True, open_in_new_tab=False):
        return NavbarLink.objects.create(
            label=label, url=url, icon_class=icon_class,
            display_order=display_order, is_visible=is_visible,
            open_in_new_tab=open_in_new_tab,
        )

    @staticmethod
    @transaction.atomic
    def update(link, data):
        allowed = ('label', 'url', 'icon_class', 'display_order', 'is_visible', 'open_in_new_tab')
        for field in allowed:
            if field in data:
                setattr(link, field, data[field])
        link.save()
        return link

    @staticmethod
    @transaction.atomic
    def delete(link):
        link.is_deleted = True
        link.save(update_fields=['is_deleted'])


class FooterGroupSelector:

    @staticmethod
    def list_all():
        return FooterGroup.objects.filter(is_deleted=False).prefetch_related('links').order_by('display_order', 'title')

    @staticmethod
    def list_visible():
        return FooterGroup.objects.filter(is_active=True, is_deleted=False).prefetch_related('links').order_by('display_order', 'title')

    @staticmethod
    def get_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(FooterGroup, uuid=uuid, is_deleted=False)


class FooterGroupCommands:

    @staticmethod
    @transaction.atomic
    def create(title, icon_class='bi-folder', description='', background_color='',
               text_color='', display_order=0, is_active=True):
        return FooterGroup.objects.create(
            title=title, icon_class=icon_class, description=description,
            background_color=background_color, text_color=text_color,
            display_order=display_order, is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update(group, data):
        allowed = ('title', 'icon_class', 'description', 'background_color',
                   'text_color', 'display_order', 'is_active')
        for field in allowed:
            if field in data:
                setattr(group, field, data[field])
        group.save()
        return group

    @staticmethod
    @transaction.atomic
    def delete(group):
        group.is_active = False
        group.is_deleted = True
        group.save(update_fields=['is_active', 'is_deleted'])

    @staticmethod
    @transaction.atomic
    def reorder_groups(ordered_uuids):
        for index, group_uuid in enumerate(ordered_uuids):
            FooterGroup.objects.filter(uuid=group_uuid, is_deleted=False).update(display_order=index)


class FooterSelector:
    """
    Enlaces de navegacion del footer. Contacto y redes sociales ya NO viven
    aqui -- se migraron a `organization` (ver
    Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md).
    `FooterLink` de este modulo solo administra category='nav' desde 2026-07-12.
    Desde 2026-07-15 el agrupamiento es via FK real (`FooterGroup`), no texto libre.
    """

    @staticmethod
    def list_active_links():
        return list(
            FooterLink.objects.filter(is_active=True, is_deleted=False, category=FooterLink.CATEGORY_NAV)
            .select_related('group').order_by('group__display_order', 'display_order')
        )

    @staticmethod
    def list_all_links():
        return FooterLink.objects.filter(
            is_deleted=False, category=FooterLink.CATEGORY_NAV
        ).select_related('group').order_by('group__display_order', 'display_order')

    @staticmethod
    def get_link_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(FooterLink, uuid=uuid, is_deleted=False)

    @staticmethod
    def build_footer_payload(contact=None, social_links=None):
        """
        Combina columnas de navegacion (core.FooterGroup + FooterLink) con
        contacto y redes sociales (organization, via OrganizationSelector) en
        un unico payload.
        """
        from organization.services.selectors import OrganizationSelector

        if contact is None:
            contact = OrganizationSelector.get_contact_info()
        if social_links is None:
            social_links = OrganizationSelector.list_social_links()

        groups = FooterGroupSelector.list_visible().prefetch_related(
            Prefetch(
                'links',
                queryset=FooterLink.objects.filter(
                    category=FooterLink.CATEGORY_NAV, is_active=True, is_deleted=False
                ).order_by('display_order'),
                to_attr='visible_links',
            )
        )

        return {
            'contact':      contact,
            'social_links': list(social_links),
            'groups':       list(groups),
        }


class FooterCommands:

    @staticmethod
    @transaction.atomic
    def create_link(title, url, category, group=None, icon_class='', open_new_tab=False, display_order=0):
        return FooterLink.objects.create(
            title=title, url=url, category=category,
            group=group, icon_class=icon_class, open_new_tab=open_new_tab,
            display_order=display_order,
        )

    @staticmethod
    @transaction.atomic
    def update_link(link, data):
        allowed = ('title', 'url', 'category', 'group', 'icon_class',
                   'open_new_tab', 'display_order', 'is_active')
        for field in allowed:
            if field in data:
                setattr(link, field, data[field])
        link.save()
        return link

    @staticmethod
    @transaction.atomic
    def delete_link(link):
        link.is_active = False
        link.is_deleted = True
        link.save(update_fields=['is_active', 'is_deleted'])

    @staticmethod
    @transaction.atomic
    def reorder_links(ordered_uuids):
        for index, link_uuid in enumerate(ordered_uuids):
            FooterLink.objects.filter(uuid=link_uuid, is_deleted=False, category=FooterLink.CATEGORY_NAV).update(display_order=index)


class FooterCTASelector:

    @staticmethod
    def get_active():
        return FooterCTAConfig.objects.filter(is_active=True, is_deleted=False).first()


class FooterCTACommands:

    @staticmethod
    @transaction.atomic
    def upsert(data):
        cfg = FooterCTASelector.get_active()
        if not cfg:
            cfg = FooterCTAConfig.objects.create()
        allowed = (
            'eyebrow', 'title_prefix', 'title_highlighted', 'subtitle',
            'btn_primary_label', 'btn_primary_url',
            'btn_ghost_label', 'btn_ghost_url',
        )
        for field in allowed:
            if field in data:
                setattr(cfg, field, data[field])
        cfg.save()
        return cfg


class BrandSliderSelector:

    @staticmethod
    def list_items_active():
        return BrandSliderItem.objects.filter(is_active=True, is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def list_items_for_admin():
        return BrandSliderItem.objects.filter(is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def get_item_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(BrandSliderItem, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_config():
        return BrandSliderConfig.objects.filter(is_deleted=False).first()

    @staticmethod
    def get_or_create_config():
        cfg = BrandSliderSelector.get_config()
        if not cfg:
            cfg = BrandSliderConfig.objects.create()
        return cfg


class BrandSliderCommands:

    @staticmethod
    @transaction.atomic
    def create_item(name, logo=None, website='', display_order=0, is_active=True, open_new_tab=True):
        return BrandSliderItem.objects.create(
            name=name,
            logo=logo,
            website=website,
            display_order=display_order,
            is_active=is_active,
            open_new_tab=open_new_tab,
        )

    @staticmethod
    @transaction.atomic
    def update_item(item, data):
        if data.pop('remove_logo', False):
            item.logo = None
        allowed = ('name', 'logo', 'website', 'display_order', 'is_active', 'open_new_tab')
        for field in allowed:
            if field in data:
                setattr(item, field, data[field])
        item.save()
        return item

    @staticmethod
    @transaction.atomic
    def delete_item(item):
        item.is_active = False
        item.is_deleted = True
        item.save(update_fields=['is_active', 'is_deleted'])

    @staticmethod
    @transaction.atomic
    def reorder_items(ordered_uuids):
        for index, item_uuid in enumerate(ordered_uuids):
            BrandSliderItem.objects.filter(uuid=item_uuid, is_deleted=False).update(display_order=index)

    @staticmethod
    @transaction.atomic
    def upsert_config(data):
        cfg = BrandSliderSelector.get_or_create_config()
        allowed = (
            'title', 'subtitle', 'autoplay', 'speed', 'direction', 'loop',
            'pause_on_hover', 'items_desktop', 'items_tablet', 'items_mobile',
            'background_color', 'padding_top', 'padding_bottom', 'is_visible',
        )
        for field in allowed:
            if field in data:
                setattr(cfg, field, data[field])
        cfg.save()
        return cfg


class AboutUsSelector:

    @staticmethod
    def list_values_active():
        return AboutUsValue.objects.filter(is_active=True, is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def list_values_for_admin():
        return AboutUsValue.objects.filter(is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def get_value_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(AboutUsValue, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_config():
        return AboutUsConfig.objects.filter(is_deleted=False).first()

    @staticmethod
    def get_or_create_config():
        cfg = AboutUsSelector.get_config()
        if not cfg:
            cfg = AboutUsConfig.objects.create()
        return cfg


class AboutUsCommands:

    @staticmethod
    @transaction.atomic
    def create_value(title, description='', icon_class='bi-gem', display_order=0, is_active=True):
        return AboutUsValue.objects.create(
            title=title,
            description=description,
            icon_class=icon_class,
            display_order=display_order,
            is_active=is_active,
        )

    @staticmethod
    @transaction.atomic
    def update_value(value, data):
        allowed = ('title', 'description', 'icon_class', 'display_order', 'is_active')
        for field in allowed:
            if field in data:
                setattr(value, field, data[field])
        value.save()
        return value

    @staticmethod
    @transaction.atomic
    def delete_value(value):
        value.is_active = False
        value.is_deleted = True
        value.save(update_fields=['is_active', 'is_deleted'])

    @staticmethod
    @transaction.atomic
    def reorder_values(ordered_uuids):
        for index, value_uuid in enumerate(ordered_uuids):
            AboutUsValue.objects.filter(uuid=value_uuid, is_deleted=False).update(display_order=index)

    @staticmethod
    @transaction.atomic
    def upsert_config(data):
        cfg = AboutUsSelector.get_or_create_config()
        if data.pop('remove_hero_image', False):
            cfg.hero_image = None
        allowed = ('title', 'subtitle', 'hero_image', 'history', 'mission', 'vision', 'is_visible')
        for field in allowed:
            if field in data:
                setattr(cfg, field, data[field])
        cfg.save()
        return cfg
