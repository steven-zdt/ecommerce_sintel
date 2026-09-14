"""
Tests para el modulo Feature Banner (Home Builder).

Cubre:
- Validaciones de modelo (overlay_opacity, coherencia url_type/url)
- Selectores y comandos (FeatureBannerSectionCommands/BlockCommands)
- Filtrado real de visibilidad en FeatureBannerSectionSelector.list_active_with_blocks()
- Exposicion en GET core/home-feed/
"""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client

from core.models import FeatureBannerBlock, FeatureBannerSection
from core.services.commands import (
    FeatureBannerBlockCommands,
    FeatureBannerSectionCommands,
    FeatureBannerSectionSelector,
)
from core.api.views import HOME_FEED_CACHE_KEY


@pytest.mark.django_db
class TestFeatureBannerSectionValidation:

    def test_overlay_opacity_out_of_range_fails(self):
        section = FeatureBannerSection(title='Test', overlay_opacity=150)
        with pytest.raises(ValidationError) as exc_info:
            section.full_clean()
        assert 'overlay_opacity' in str(exc_info.value)

    def test_overlay_opacity_in_range_succeeds(self):
        section = FeatureBannerSection(title='Test', overlay_opacity=45)
        section.full_clean()
        section.save()
        assert section.pk is not None


@pytest.mark.django_db
class TestFeatureBannerBlockUrlValidation:

    def _make_section(self):
        return FeatureBannerSection.objects.create(title='Seccion')

    def test_interna_url_without_leading_slash_fails(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_primary_text='Ir', btn_primary_url='tienda', btn_primary_url_type='INTERNA',
        )
        with pytest.raises(ValidationError) as exc_info:
            block.full_clean()
        assert 'btn_primary_url' in str(exc_info.value)

    def test_interna_url_with_leading_slash_succeeds(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_primary_text='Ir', btn_primary_url='/tienda', btn_primary_url_type='INTERNA',
        )
        block.full_clean()
        block.save()
        assert block.pk is not None

    def test_externa_url_without_scheme_fails(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_secondary_text='Ver', btn_secondary_url='www.example.com', btn_secondary_url_type='EXTERNA',
        )
        with pytest.raises(ValidationError) as exc_info:
            block.full_clean()
        assert 'btn_secondary_url' in str(exc_info.value)

    def test_externa_url_with_scheme_succeeds(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_secondary_text='Ver', btn_secondary_url='https://example.com', btn_secondary_url_type='EXTERNA',
        )
        block.full_clean()
        block.save()
        assert block.pk is not None

    def test_anchor_url_without_hash_fails(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_primary_text='Ver', btn_primary_url='seccion-2', btn_primary_url_type='ANCHOR',
        )
        with pytest.raises(ValidationError) as exc_info:
            block.full_clean()
        assert 'btn_primary_url' in str(exc_info.value)

    def test_anchor_url_with_hash_succeeds(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_primary_text='Ver', btn_primary_url='#seccion-2', btn_primary_url_type='ANCHOR',
        )
        block.full_clean()
        block.save()
        assert block.pk is not None

    def test_empty_url_skips_validation_regardless_of_type(self):
        block = FeatureBannerBlock(
            section=self._make_section(),
            btn_primary_text='', btn_primary_url='', btn_primary_url_type='EXTERNA',
        )
        block.full_clean()
        block.save()
        assert block.pk is not None


@pytest.mark.django_db
class TestFeatureBannerSectionCommands:

    def test_create_only_persists_allowed_fields(self):
        section = FeatureBannerSectionCommands.create(
            title='Promo', subtitle='Sub', theme='dark', background_type='gradient',
            background_gradient_from='#000', background_gradient_to='#111',
            not_a_real_field='ignored',
        )
        assert section.pk is not None
        assert section.title == 'Promo'
        assert section.theme == 'dark'
        assert not hasattr(section, 'not_a_real_field')

    def test_update_applies_partial_fields(self):
        section = FeatureBannerSectionCommands.create(title='Original')
        updated = FeatureBannerSectionCommands.update(section, {'title': 'Actualizado', 'is_visible': False})
        updated.refresh_from_db()
        assert updated.title == 'Actualizado'
        assert updated.is_visible is False

    def test_delete_is_soft_delete(self):
        section = FeatureBannerSectionCommands.create(title='Borrar')
        FeatureBannerSectionCommands.delete(section)
        section.refresh_from_db()
        assert section.is_deleted is True
        # Soft-deleted: no debe aparecer en el selector admin.
        assert section.uuid not in [s.uuid for s in FeatureBannerSectionSelector.list_all()]


@pytest.mark.django_db
class TestFeatureBannerBlockCommands:

    def test_create_assigns_section_and_filters_fields(self):
        section = FeatureBannerSectionCommands.create(title='Seccion')
        block = FeatureBannerBlockCommands.create(
            section, layout_type='fifty_fifty', title='Bloque', benefits=[{'icon': 'bi-check', 'text': 'X'}],
            not_a_real_field='ignored',
        )
        assert block.section_id == section.id
        assert block.layout_type == 'fifty_fifty'
        assert block.benefits == [{'icon': 'bi-check', 'text': 'X'}]

    def test_update_can_remove_image_flag(self):
        section = FeatureBannerSectionCommands.create(title='Seccion')
        block = FeatureBannerBlockCommands.create(section, title='Bloque')
        updated = FeatureBannerBlockCommands.update(block, {'remove_image': True, 'title': 'Editado'})
        updated.refresh_from_db()
        assert updated.title == 'Editado'
        assert not updated.image

    def test_reorder_updates_display_order_by_position(self):
        section = FeatureBannerSectionCommands.create(title='Seccion')
        b1 = FeatureBannerBlockCommands.create(section, title='B1', display_order=0)
        b2 = FeatureBannerBlockCommands.create(section, title='B2', display_order=1)
        FeatureBannerBlockCommands.reorder(section.id, [str(b2.uuid), str(b1.uuid)])
        b1.refresh_from_db()
        b2.refresh_from_db()
        assert b2.display_order == 0
        assert b1.display_order == 1

    def test_delete_is_soft_delete(self):
        section = FeatureBannerSectionCommands.create(title='Seccion')
        block = FeatureBannerBlockCommands.create(section, title='Bloque')
        FeatureBannerBlockCommands.delete(block)
        block.refresh_from_db()
        assert block.is_deleted is True


@pytest.mark.django_db
class TestFeatureBannerSectionSelectorVisibility:
    """El filtrado real de visibilidad ocurre en el backend (a diferencia de
    HomeFeedSelector.get_module_configs()), verificado aqui explicitamente."""

    def test_hidden_section_excluded_from_active_selector(self):
        visible = FeatureBannerSectionCommands.create(title='Visible', is_visible=True)
        hidden = FeatureBannerSectionCommands.create(title='Oculta', is_visible=False)
        FeatureBannerBlockCommands.create(visible, title='B')
        FeatureBannerBlockCommands.create(hidden, title='B')

        uuids = [s.uuid for s in FeatureBannerSectionSelector.list_active_with_blocks()]
        assert visible.uuid in uuids
        assert hidden.uuid not in uuids

    def test_inactive_block_excluded_but_section_stays(self):
        section = FeatureBannerSectionCommands.create(title='Visible', is_visible=True)
        active_block = FeatureBannerBlockCommands.create(section, title='Activo', is_active=True)
        inactive_block = FeatureBannerBlockCommands.create(section, title='Inactivo', is_active=False)

        result = FeatureBannerSectionSelector.list_active_with_blocks().get(uuid=section.uuid)
        block_uuids = [b.uuid for b in result.blocks.all()]
        assert active_block.uuid in block_uuids
        assert inactive_block.uuid not in block_uuids


@pytest.mark.django_db
class TestFeatureBannerInHomeFeed:

    @pytest.fixture(autouse=True)
    def setup(self):
        cache.clear()
        yield
        cache.clear()

    def test_home_feed_exposes_visible_sections_with_blocks(self):
        section = FeatureBannerSectionCommands.create(title='Promo Home', is_visible=True)
        FeatureBannerBlockCommands.create(
            section, title='Bloque Home', btn_primary_text='Ir', btn_primary_url='/tienda',
            btn_primary_url_type='INTERNA',
        )

        client = Client()
        response = client.get('/api/v1/core/home-feed/')
        assert response.status_code == 200

        payload = response.json()
        assert 'feature_banner_sections' in payload
        titles = [s['title'] for s in payload['feature_banner_sections']]
        assert 'Promo Home' in titles

        found = next(s for s in payload['feature_banner_sections'] if s['title'] == 'Promo Home')
        assert found['blocks'][0]['title'] == 'Bloque Home'
        assert found['blocks'][0]['btn_primary_url_type'] == 'INTERNA'

    def test_home_feed_excludes_hidden_section(self):
        FeatureBannerSectionCommands.create(title='Oculta Home', is_visible=False)

        client = Client()
        response = client.get('/api/v1/core/home-feed/')
        payload = response.json()

        titles = [s['title'] for s in payload['feature_banner_sections']]
        assert 'Oculta Home' not in titles

    def test_creating_section_invalidates_home_feed_cache(self):
        cache.set(HOME_FEED_CACHE_KEY, {'stale': True}, 300)
        assert cache.get(HOME_FEED_CACHE_KEY) is not None

        FeatureBannerSectionCommands.create(title='Nueva')

        assert cache.get(HOME_FEED_CACHE_KEY) is None
