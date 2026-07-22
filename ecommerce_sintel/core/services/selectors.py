from django.utils import timezone
from django.db import transaction
from django.db.models import Prefetch
from core.models import (
    HomeBanner, HomeModuleConfig, HomeCard, HomeCardGroup, FooterLink, FooterGroup, NavbarLink, FooterCTAConfig,
    BrandSliderItem, BrandSliderConfig,
)


class HomeConfigSelector:

    @staticmethod
    def list_banners_active():
        return HomeBanner.objects.filter(is_active=True, is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def list_banners_for_admin():
        return HomeBanner.objects.filter(is_deleted=False).order_by('display_order', '-created_at')

    @staticmethod
    def get_banner_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(HomeBanner, uuid=uuid, is_deleted=False)

    @staticmethod
    def list_module_configs():
        return HomeModuleConfig.objects.filter(is_deleted=False).order_by('display_order')

    @staticmethod
    def get_module_config_by_uuid(uuid):
        from django.shortcuts import get_object_or_404
        return get_object_or_404(HomeModuleConfig, uuid=uuid, is_deleted=False)

    @staticmethod
    def get_or_create_default_modules():
        """Asegura que los 4 modulos de home existan con valores por defecto."""
        defaults = [
            {'module_key': HomeModuleConfig.MODULE_SHOP,     'display_order': 1},
            {'module_key': HomeModuleConfig.MODULE_RENTING,  'display_order': 2},
            {'module_key': HomeModuleConfig.MODULE_SERVICES, 'display_order': 3},
            {'module_key': HomeModuleConfig.MODULE_QUOTES,   'display_order': 4},
        ]
        for d in defaults:
            HomeModuleConfig.objects.get_or_create(module_key=d['module_key'], defaults=d)
        return HomeConfigSelector.list_module_configs()
