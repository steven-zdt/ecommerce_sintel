from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from shop.models import Category, Product, ProductVariant
from technical_services.models import ServiceCategory, TechnicalService, ServiceVariant
from marketing.models import FlashOffer, MarketingCampaign

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
