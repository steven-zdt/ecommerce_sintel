"""
Tests para "Card Group Section" -- extension de HomeCardGroup/HomeCard (Home Builder),
en vez de un modelo paralelo. Ver core/.AGENT/docs/CARD_GROUP_ARCHITECTURE.md.

Cubre:
- validate_url_type_pair() (helper compartido, tambien usado por FeatureBannerBlock)
- Validacion de url_type/secondary_url_type en HomeCard.clean()
- Whitelist de campos nuevos en HomeCardCommands/HomeCardGroupCommands
- Exposicion de los campos nuevos en GET core/home-feed/
- Integridad del backfill de url_type sobre datos existentes
"""

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from core.models import HomeCard, HomeCardGroup
from core.services.commands import HomeCardCommands, HomeCardGroupCommands
from core.validators import validate_url_type_pair


class TestValidateUrlTypePair:

    def test_empty_url_is_always_valid(self):
        assert validate_url_type_pair('INTERNA', '') is None
        assert validate_url_type_pair('EXTERNA', '') is None
        assert validate_url_type_pair('ANCHOR', '') is None

    def test_interna_requires_leading_slash(self):
        assert validate_url_type_pair('INTERNA', 'tienda') is not None
        assert validate_url_type_pair('INTERNA', '/tienda') is None

    def test_externa_requires_scheme(self):
        assert validate_url_type_pair('EXTERNA', 'www.example.com') is not None
        assert validate_url_type_pair('EXTERNA', 'https://example.com') is None
        assert validate_url_type_pair('EXTERNA', 'http://example.com') is None

    def test_anchor_requires_hash(self):
        assert validate_url_type_pair('ANCHOR', 'seccion-2') is not None
        assert validate_url_type_pair('ANCHOR', '#seccion-2') is None


@pytest.mark.django_db
class TestHomeCardUrlValidation:

    def test_redirect_url_interna_without_slash_fails(self):
        card = HomeCard(title='T', group_name='g', redirect_url='tienda', url_type='INTERNA')
        with pytest.raises(ValidationError) as exc_info:
            card.full_clean()
        assert 'redirect_url' in str(exc_info.value)

    def test_redirect_url_externa_with_scheme_succeeds(self):
        card = HomeCard(title='T', group_name='g', redirect_url='https://example.com', url_type='EXTERNA')
        card.full_clean()
        card.save()
        assert card.pk is not None

    def test_secondary_url_anchor_without_hash_fails(self):
        card = HomeCard(title='T', group_name='g', secondary_label='Ver', secondary_url='seccion', secondary_url_type='ANCHOR')
        with pytest.raises(ValidationError) as exc_info:
            card.full_clean()
        assert 'secondary_url' in str(exc_info.value)

    def test_secondary_url_anchor_with_hash_succeeds(self):
        card = HomeCard(title='T', group_name='g', secondary_label='Ver', secondary_url='#seccion', secondary_url_type='ANCHOR')
        card.full_clean()
        card.save()
        assert card.pk is not None


@pytest.mark.django_db
class TestHomeCardCommandsNewFields:

    def test_create_card_persists_stats_and_secondary_button(self):
        card = HomeCardCommands.create_card(
            title='Curso', group_name='cursos',
            stats=[{'label': 'Duracion', 'value': '8 semanas'}],
            badge_color='#22c55e',
            secondary_label='Ver temario', secondary_url='/temario', secondary_url_type='INTERNA',
        )
        assert card.stats == [{'label': 'Duracion', 'value': '8 semanas'}]
        assert card.badge_color == '#22c55e'
        assert card.secondary_label == 'Ver temario'

    def test_create_card_ignores_unknown_fields(self):
        card = HomeCardCommands.create_card(title='X', group_name='g', not_a_real_field='ignored')
        assert not hasattr(card, 'not_a_real_field')

    def test_update_card_applies_url_type(self):
        card = HomeCardCommands.create_card(title='X', group_name='g')
        updated = HomeCardCommands.update_card(card, {'url_type': 'ANCHOR', 'redirect_url': '#top'})
        updated.refresh_from_db()
        assert updated.url_type == 'ANCHOR'
        assert updated.redirect_url == '#top'


@pytest.mark.django_db
class TestHomeCardGroupCommandsNewFields:

    def test_upsert_persists_responsive_and_carousel_fields(self):
        group = HomeCardGroupCommands.upsert(
            name='cursos', title='Cursos',
            layout_type='slider', columns_tablet=2, columns_mobile=1, gap=1.5,
            carousel_autoplay=True, carousel_loop=True, carousel_speed=60,
            show_arrows=True, show_indicators=False,
        )
        assert group.columns_tablet == 2
        assert group.carousel_autoplay is True
        assert group.show_indicators is False

    def test_upsert_existing_group_updates_carousel_fields(self):
        HomeCardGroupCommands.upsert(name='cursos', title='Cursos', carousel_autoplay=False)
        updated = HomeCardGroupCommands.upsert(name='cursos', title='Cursos', carousel_autoplay=True)
        updated.refresh_from_db()
        assert updated.carousel_autoplay is True


@pytest.mark.django_db
class TestHomeCardGroupDefaults:

    def test_group_defaults_match_previous_visual_behavior(self):
        """Autoplay=False por defecto -- grupos slider existentes no cambian de
        apariencia hasta que el admin lo active explicitamente."""
        group = HomeCardGroup.objects.create(name='g', title='G', layout_type='slider')
        assert group.carousel_autoplay is False
        assert group.carousel_loop is True
        assert group.show_arrows is True
        assert group.show_indicators is True


@pytest.mark.django_db
class TestCardGroupInHomeFeed:

    def test_home_feed_exposes_new_card_and_group_fields(self):
        HomeCardGroupCommands.upsert(name='cursos', title='Cursos', layout_type='slider', carousel_autoplay=True)
        HomeCardCommands.create_card(
            title='Curso Python', group_name='cursos',
            stats=[{'label': 'Nivel', 'value': 'Intermedio'}],
            secondary_label='Ver temario', secondary_url='/temario', secondary_url_type='INTERNA',
        )

        client = Client()
        response = client.get('/api/v1/core/home-feed/')
        assert response.status_code == 200
        payload = response.json()

        group = next(g for g in payload['card_groups'] if g['name'] == 'cursos')
        assert group['carousel_autoplay'] is True

        card = next(c for c in payload['home_cards'] if c['title'] == 'Curso Python')
        assert card['stats'] == [{'label': 'Nivel', 'value': 'Intermedio'}]
        assert card['secondary_label'] == 'Ver temario'


@pytest.mark.django_db
class TestUrlTypeBackfillLogic:
    """
    La migracion 0029 (core/migrations/0029_card_group_section_fields.py::
    backfill_url_type) aplica: url_type='EXTERNA' si redirect_url empieza con
    'http', 'INTERNA' en cualquier otro caso -- misma regla que la inferencia
    por regex que tenia CardItem.vue::navigate() antes del refactor a
    resolveUrlNavigation(). Se replica la MISMA query aqui (no se puede re-correr
    la migracion historica en un test unitario) para verificar que produce
    resultados coherentes con validate_url_type_pair().
    """

    def test_backfill_query_produces_valid_pairings(self):
        # bulk_create() no llama a save()/clean() -- igual que el modelo historico
        # que usa RunPython (apps.get_model()), que no tiene el full_clean() del
        # modelo real. Simula el estado "antes del backfill": url_type=INTERNA
        # (default) conviviendo con un redirect_url externo, exactamente el
        # estado en el que estarian filas creadas antes de que url_type existiera.
        HomeCard.objects.bulk_create([
            HomeCard(title='A', group_name='g', redirect_url='https://example.com'),
            HomeCard(title='B', group_name='g', redirect_url='/tienda'),
            HomeCard(title='C', group_name='g', redirect_url=''),
        ])

        # Misma query que el RunPython de la migracion.
        HomeCard.objects.filter(redirect_url__startswith='http').update(url_type='EXTERNA')

        for card in HomeCard.objects.all():
            assert validate_url_type_pair(card.url_type, card.redirect_url) is None

        assert HomeCard.objects.get(title='A').url_type == 'EXTERNA'
        assert HomeCard.objects.get(title='B').url_type == 'INTERNA'
        assert HomeCard.objects.get(title='C').url_type == 'INTERNA'
