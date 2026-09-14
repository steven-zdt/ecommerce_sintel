import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from shop.models import Category, Product, ProductVariant
from technical_services.models import ServiceCategory, TechnicalService, ServiceVariant
from marketing.models import FlashOffer, MarketingCampaign, CampaignLog

User = get_user_model()


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MarketingPermissionsTestCase(APITestCase):
    """
    Cubre el gap detectado el 2026-07-03: ninguna de las 4 ViewSets de marketing declaraba
    permission_classes -- todas caian al default del proyecto (IsAuthenticated). Efecto real:
    FlashOfferViewSet (pensada para la vitrina publica, su selector ya filtra is_active=True)
    exigia login sin necesidad; MarketingCampaignViewSet (un ModelViewSet con escritura
    completa) era alcanzable por cualquier usuario autenticado, no solo admin.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='marketing_admin@example.com', password='testpassword123',
        )
        self.customer = User.objects.create_user(
            email='marketing_customer@example.com', password='testpassword123',
        )
        now = timezone.now()
        FlashOffer.objects.create(
            name='Oferta relampago',
            description='Descuento por tiempo limitado',
            discount_percentage=Decimal('20.00'),
            start_time=now - timezone.timedelta(hours=1),
            end_time=now + timezone.timedelta(hours=1),
            is_active=True,
        )
        MarketingCampaign.objects.create(
            title='Campaña de prueba',
            content='Contenido',
            scheduled_at=now,
        )

    def test_offers_list_is_public(self):
        response = self.client.get('/api/v1/marketing/offers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_campaigns_list_requires_admin_anonymous(self):
        response = self.client.get('/api/v1/marketing/campaigns/')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_campaigns_list_requires_admin_regular_user_forbidden(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/v1/marketing/campaigns/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_campaigns_list_allowed_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/marketing/campaigns/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_runs_requires_admin(self):
        response = self.client.get('/api/v1/marketing/agent-runs/')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_dashboard_requires_admin(self):
        response = self.client.get('/api/v1/marketing/dashboard/')
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class MarketingModelIntegrityTestCase(APITestCase):
    """
    Cubre 2 hallazgos de Fase 6 (auditoria de BD, 2026-07-03):
    1. MarketingCampaign.__str__() referenciaba un atributo `self.channel` inexistente (el campo
       real es `channels`, plural, JSONField) -- AttributeError en cualquier render de
       str(campaign), incluido Django Admin.
    2. FlashOffer podia apuntar simultaneamente a mas de un tipo de item (variant +
       service_variant + equipment_variant a la vez), una combinacion ambigua sin sentido de
       negocio. Se agrego un CheckConstraint "como maximo uno" -- deliberadamente NO "exactamente
       uno", porque una FlashOffer sin ningun target (oferta general de vitrina) es un caso valido
       ya presente en datos reales.
    """

    def setUp(self):
        category = Category.objects.create(name='Cat Marketing', slug='cat-marketing-test')
        product = Product.objects.create(
            vendor=self._admin_user(), category=category,
            name='Producto Marketing', slug='producto-marketing-test',
        )
        self.variant = ProductVariant.objects.create(product=product, sku='MKT-SKU-1', price=Decimal('10.00'), stock=0)
        service_category = ServiceCategory.objects.create(name='Cat Servicio Marketing', slug='cat-servicio-marketing-test')
        service = TechnicalService.objects.create(
            vendor=self._admin_user(), category=service_category, name='Servicio Marketing', slug='servicio-marketing-test',
            description='desc',
        )
        self.service_variant = ServiceVariant.objects.create(
            service=service, sku='MKT-SVC-1', pricing_strategy=ServiceVariant.FIXED, fixed_price=Decimal('10.00'),
        )

    def _admin_user(self):
        if not hasattr(self, '_admin'):
            self._admin = User.objects.create_superuser(email='marketing_model_admin@example.com', password='testpassword123')
        return self._admin

    def test_marketing_campaign_str_does_not_raise(self):
        campaign = MarketingCampaign.objects.create(
            title='Campaña', content='Contenido', channels=['email', 'whatsapp'], scheduled_at=timezone.now(),
        )
        self.assertEqual(str(campaign), 'Campaña (email, whatsapp)')

    def test_flashoffer_with_no_target_is_allowed(self):
        now = timezone.now()
        offer = FlashOffer.objects.create(
            name='Oferta general', description='desc', discount_percentage=Decimal('10.00'),
            start_time=now, end_time=now + timezone.timedelta(hours=1),
        )
        self.assertIsNone(offer.variant)

    def test_flashoffer_with_two_targets_blocked_by_db_constraint(self):
        now = timezone.now()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                FlashOffer.objects.create(
                    name='Oferta ambigua', description='desc', discount_percentage=Decimal('10.00'),
                    start_time=now, end_time=now + timezone.timedelta(hours=1),
                    variant=self.variant, service_variant=self.service_variant,
                )


class MarketingAgentBroadcastChannelFilterTestCase(TestCase):
    """
    Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): MarketingAgent.run() despachaba
    SIEMPRE con recipient="broadcast", incluso para email/whatsapp (canales que si usan ese
    valor como direccion real) -- el envio fallaba en silencio siempre que el LLM los elegia.
    Ahora se filtran a los canales realmente broadcast antes de despachar.
    """

    def _mock_llm_decision(self, channels):
        return json.dumps({
            'should_dispatch': True,
            'campaign_title': 'Promo de prueba',
            'content': 'Contenido de prueba',
            'channels': channels,
            'target_audience': 'todos',
            'rationale': 'razon de prueba',
        })

    @patch('marketing.services.commands.MarketingCommands.dispatch')
    @patch('marketing.agent.brain.LLMRouter.complete')
    @patch('marketing.agent.brain.MarketingSelector.get_consolidated_dashboard')
    def test_solo_despacha_canales_broadcast_y_omite_email_whatsapp(
        self, mock_dashboard, mock_llm, mock_dispatch,
    ):
        from marketing.agent.brain import MarketingAgent

        mock_dashboard.return_value = {}
        mock_llm.return_value = self._mock_llm_decision(['facebook', 'email', 'whatsapp', 'instagram'])

        run = MarketingAgent().run(triggered_by='manual')

        self.assertEqual(run.status, 'completed_dispatched')
        self.assertEqual(sorted(run.campaign.channels), ['facebook', 'instagram'])
        self.assertIn('email', run.notes)
        self.assertIn('whatsapp', run.notes)
        mock_dispatch.assert_called_once()

    @patch('marketing.services.commands.MarketingCommands.dispatch')
    @patch('marketing.agent.brain.LLMRouter.complete')
    @patch('marketing.agent.brain.MarketingSelector.get_consolidated_dashboard')
    def test_si_todos_los_canales_elegidos_requieren_destinatario_no_despacha_nada(
        self, mock_dashboard, mock_llm, mock_dispatch,
    ):
        from marketing.agent.brain import MarketingAgent

        mock_dashboard.return_value = {}
        mock_llm.return_value = self._mock_llm_decision(['email', 'whatsapp'])

        run = MarketingAgent().run(triggered_by='manual')

        self.assertEqual(run.status, 'completed_no_action')
        self.assertEqual(run.campaign.channels, [])
        mock_dispatch.assert_not_called()


class MarketingWhatsappRateLimitTestCase(TestCase):
    """Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): el canal whatsapp de
    marketing comparte cuota de Meta con notifications (soporte transaccional, OTPs)."""

    def setUp(self):
        from marketing.services.commands import _WHATSAPP_MARKETING_RATE_LIMIT_KEY
        cache.delete(_WHATSAPP_MARKETING_RATE_LIMIT_KEY)

    @patch('marketing.tasks.send_via_channel_task.delay')
    def test_whatsapp_se_omite_tras_superar_el_limite(self, mock_delay):
        from marketing.services.commands import MarketingCommands, _WHATSAPP_MARKETING_RATE_LIMIT_MAX

        campaign = MarketingCampaign.objects.create(
            title='Campaña WA', content='Contenido', channels=['whatsapp'], scheduled_at=timezone.now(),
        )
        for i in range(_WHATSAPP_MARKETING_RATE_LIMIT_MAX + 3):
            MarketingCommands.dispatch(campaign=campaign, recipient=f'+5730012345{i:02d}')

        self.assertEqual(mock_delay.call_count, _WHATSAPP_MARKETING_RATE_LIMIT_MAX)

    @patch('marketing.tasks.send_via_channel_task.delay')
    def test_otros_canales_no_se_afectan_por_el_limite_de_whatsapp(self, mock_delay):
        from marketing.services.commands import MarketingCommands, _WHATSAPP_MARKETING_RATE_LIMIT_KEY

        cache.set(_WHATSAPP_MARKETING_RATE_LIMIT_KEY, 9999, timeout=3600)  # whatsapp ya al limite

        campaign = MarketingCampaign.objects.create(
            title='Campaña FB', content='Contenido', channels=['facebook'], scheduled_at=timezone.now(),
        )
        MarketingCommands.dispatch(campaign=campaign, recipient='broadcast')

        mock_delay.assert_called_once()


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MetaAdsInternalAiViewsTestCase(APITestCase):
    """FASE 9 integracion Meta Business: endpoints internal_ai Meta Ads READ,
    admin-only, envuelven MetaCampaignSelector y mapean las excepciones de la
    frontera Meta a HTTP status."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='meta_admin@example.com', password='x')
        self.customer = User.objects.create_user(email='meta_customer@example.com', password='x')

    def test_campaigns_requires_admin(self):
        url = '/api/v1/internal/ai/marketing/meta/campaigns/'
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    @patch('marketing.api.internal_ai.MetaCampaignSelector.get_campaigns')
    def test_campaigns_returns_selector_payload_for_admin(self, mock_get):
        mock_get.return_value = {'count': 1, 'campaigns': [{'id': 'c1', 'name': 'BF'}]}
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/internal/ai/marketing/meta/campaigns/?limit=10')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['campaigns'][0]['id'], 'c1')

    @patch('marketing.api.internal_ai.MetaCampaignSelector.get_account_summary')
    def test_config_error_maps_to_503(self, mock_sum):
        from marketing.integrations.meta.exceptions import MetaConfigError
        mock_sum.side_effect = MetaConfigError('META_AD_ACCOUNT_ID no configurado.')
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/internal/ai/marketing/meta/account-summary/')
        self.assertEqual(resp.status_code, 503)
        self.assertFalse(resp.data['configured'])

    @patch('marketing.api.internal_ai.MetaCampaignSelector.get_insights')
    def test_transient_error_maps_to_502(self, mock_ins):
        from marketing.integrations.meta.exceptions import MetaApiTransientError
        mock_ins.side_effect = MetaApiTransientError('timeout')
        self.client.force_authenticate(self.admin)
        resp = self.client.get('/api/v1/internal/ai/marketing/meta/insights/?object_id=c1')
        self.assertEqual(resp.status_code, 502)

    def test_insights_rejects_missing_object_id_and_bad_level(self):
        self.client.force_authenticate(self.admin)
        base = '/api/v1/internal/ai/marketing/meta/insights/'
        self.assertEqual(self.client.get(base).status_code, 400)
        self.assertEqual(self.client.get(base + '?object_id=c1&level=galaxy').status_code, 400)
