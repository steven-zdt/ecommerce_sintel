"""
Tests para core app.

Cubre:
- Validaciones de modelos
- Señales de invalidación de cache
- Selectores y comandos
"""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client

from core.models import HomeBanner, HomeModuleConfig
from core.api.views import HOME_FEED_CACHE_KEY, FOOTER_CACHE_KEY, SITE_CONFIG_CACHE_KEY


@pytest.mark.django_db
class TestHomeBannerValidation:
    """Tests para validaciones en HomeBanner."""
    
    def test_banner_link_label_required_if_link_url_exists(self):
        """link_label debe ser requerido si link_url está presente."""
        banner = HomeBanner(
            title='Test Banner',
            link_url='/tienda',
            link_label='',  # ← Vacío, debe fallar
        )
        
        with pytest.raises(ValidationError) as exc_info:
            banner.full_clean()
        
        assert 'link_label' in str(exc_info.value)
    
    def test_banner_link_label_optional_if_no_link_url(self):
        """link_label es opcional si no hay link_url."""
        banner = HomeBanner(
            title='Test Banner',
            link_url='',  # ← Vacío
            link_label='',  # ← Puede estar vacío
        )
        
        # No debe lanzar excepción
        banner.full_clean()
        banner.save()
        assert banner.pk is not None
    
    def test_banner_with_link_url_and_label_is_valid(self):
        """Banner con URL y label es válido."""
        banner = HomeBanner(
            title='Test Banner',
            link_url='/tienda',
            link_label='Ver Tienda',
        )
        
        banner.full_clean()
        banner.save()
        assert banner.pk is not None


@pytest.mark.django_db
class TestHomeModuleConfigValidation:
    """Tests para validaciones en HomeModuleConfig."""
    
    def test_valid_module_key_is_accepted(self):
        """Un module_key válido no requiere custom fields."""
        config = HomeModuleConfig(
            module_key='shop',  # Válido en MODULE_META
            # custom fields pueden estar vacíos
        )
        
        config.full_clean()
        config.save()
        assert config.pk is not None
    
    def test_invalid_module_key_without_custom_fields_fails(self):
        """Un module_key inválido sin custom fields falla."""
        config = HomeModuleConfig(
            module_key='invalid_module',  # ← No existe en MODULE_META
            # custom fields vacíos
        )
        
        with pytest.raises(ValidationError) as exc_info:
            config.full_clean()
        
        assert 'module_key' in str(exc_info.value)
    
    def test_invalid_module_key_with_custom_fields_succeeds(self):
        """Un module_key inválido CON custom fields completos funciona."""
        config = HomeModuleConfig(
            module_key='custom_module',  # ← No existe en MODULE_META
            custom_label='Mi Módulo',
            custom_url='/mi-modulo',
            custom_icon='bi-star',
        )
        
        config.full_clean()
        config.save()
        assert config.pk is not None


# NOTA (2026-07-12): los tests de singleton de SiteBrandConfig/CompanyContactInfo se
# movieron a organization/tests.py (Company/Branding/ContactInfo) -- esos modelos ya
# no existen en core, se migraron a `organization`. Ver
# Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.


@pytest.mark.django_db
class TestCacheInvalidationSignals:
    """Tests para señales de invalidación de cache."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Limpiar cache antes de cada test."""
        cache.clear()
        yield
        cache.clear()
    
    def test_banner_change_invalidates_home_feed_cache(self):
        """Editar un banner invalida home-feed cache."""
        # Simular cache establecido
        cache.set(HOME_FEED_CACHE_KEY, {'test': 'data'}, 300)
        assert cache.get(HOME_FEED_CACHE_KEY) is not None
        
        # Crear/editar banner dispara signal
        banner = HomeBanner.objects.create(
            title='Test',
            display_order=0,
        )
        
        # Cache debe estar invalidado
        assert cache.get(HOME_FEED_CACHE_KEY) is None
    
    def test_home_module_config_change_invalidates_cache(self):
        """Editar HomeModuleConfig invalida home-feed cache."""
        cache.set(HOME_FEED_CACHE_KEY, {'test': 'data'}, 300)
        
        config = HomeModuleConfig.objects.create(
            module_key='test_module',
            custom_label='Test',
            custom_url='/test',
            custom_icon='bi-test',
        )
        
        assert cache.get(HOME_FEED_CACHE_KEY) is None
    
    # NOTA (2026-07-12): la invalidacion de SITE_CONFIG_CACHE_KEY/FOOTER_CACHE_KEY para
    # datos de marca/contacto ya NO es por signal (esos modelos viven en `organization`,
    # que no usa signals) -- ahora es explicita en dashboard/api/views.py justo despues
    # de llamar a OrganizationCommands. Ver organization/tests.py para los tests de
    # singleton de esos modelos.


@pytest.mark.django_db
class TestCacheInvalidationOnDelete:
    """Tests para invalidación de cache en eliminación de objetos."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        cache.clear()
        yield
        cache.clear()
    
    def test_banner_deletion_invalidates_cache(self):
        """Eliminar un banner invalida cache."""
        banner = HomeBanner.objects.create(title='Test', display_order=0)
        cache.set(HOME_FEED_CACHE_KEY, {'test': 'data'}, 300)
        
        banner.delete()
        
        assert cache.get(HOME_FEED_CACHE_KEY) is None
    
    def test_footer_link_deletion_invalidates_cache(self):
        """Eliminar un enlace del footer invalida cache."""
        from core.models import FooterLink
        
        link = FooterLink.objects.create(
            title='Test Link',
            url='https://example.com',
        )
        cache.set(FOOTER_CACHE_KEY, {'test': 'data'}, 300)
        
        link.delete()
        
        assert cache.get(FOOTER_CACHE_KEY) is None
