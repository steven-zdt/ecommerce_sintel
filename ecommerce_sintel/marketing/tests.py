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
from renting.models import RentingCategory, Equipment, EquipmentVariant
from marketing.models import (
    FlashOffer, MarketingCampaign, CampaignLog, CampaignBenefit, CampaignItem, CampaignMedia,
)

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


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MarketingCampaignSourceAndBenefitsTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 3 (dos modos de
    creacion) + Fase 4 (Producto como base) + Fase 8 (beneficios, set minimo), 2026-09-23.
    [ACTUALIZADO Fase 7, 2026-09-23]: contrato de escritura/lectura paso de
    source_type/source_uuid/source_preview (singular) a items=[{type, uuid, quantity, preview}]
    (lista) -- ver CampaignItem/CampaignItemSerializer.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_source_admin@example.com', password='testpassword123')
        self.client.force_authenticate(user=self.admin)
        category = Category.objects.create(name='Cat Source Marketing', slug='cat-source-marketing-test')
        self.product = Product.objects.create(
            vendor=self.admin, category=category, name='Camara Marketing Test', slug='camara-marketing-test',
            brand=None,
        )
        ProductVariant.objects.create(product=self.product, sku='MKT-SRC-1', price=Decimal('350000.00'), stock=5, is_default=True)

    def _payload(self, **overrides):
        data = {
            'title': 'Campaña de prueba',
            'content': 'Contenido',
            'channels': ['email'],
            'scheduled_at': timezone.now().isoformat(),
        }
        data.update(overrides)
        return data

    def test_create_from_scratch_has_no_items(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['items'], [])

    def test_create_from_product_resolves_real_preview(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'product', 'uuid': str(self.product.uuid), 'quantity': 1}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = response.data['items'][0]
        self.assertEqual(item['type'], 'product')
        self.assertEqual(item['uuid'], str(self.product.uuid))
        self.assertEqual(item['quantity'], 1)
        self.assertEqual(item['preview']['name'], 'Camara Marketing Test')
        self.assertEqual(item['preview']['variants'][0]['price'], '350000.00')

    def test_create_with_invalid_product_uuid_returns_400(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'product', 'uuid': '00000000-0000-0000-0000-000000000000'}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_with_benefits_persists_them(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            benefits=[
                {'benefit_type': CampaignBenefit.BENEFIT_FREE_SHIPPING, 'label': 'Transporte gratis'},
                {'benefit_type': CampaignBenefit.BENEFIT_DISCOUNT_PERCENT, 'label': '10% off', 'value': '10.00'},
            ],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        campaign = MarketingCampaign.objects.get(uuid=response.data['uuid'])
        self.assertEqual(campaign.benefits.count(), 2)
        self.assertTrue(campaign.benefits.filter(benefit_type=CampaignBenefit.BENEFIT_DISCOUNT_PERCENT, value=Decimal('10.00')).exists())

    def test_update_replaces_benefits(self):
        create_response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            benefits=[{'benefit_type': CampaignBenefit.BENEFIT_FREE_SHIPPING, 'label': 'Transporte gratis'}],
        ), format='json')
        uuid = create_response.data['uuid']
        update_response = self.client.patch(f'/api/v1/marketing/campaigns/{uuid}/', {
            'benefits': [{'benefit_type': CampaignBenefit.BENEFIT_FREE_INSTALLATION, 'label': 'Instalacion gratis'}],
        }, format='json')
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        campaign = MarketingCampaign.objects.get(uuid=uuid)
        self.assertEqual(campaign.benefits.count(), 1)
        self.assertEqual(campaign.benefits.first().benefit_type, CampaignBenefit.BENEFIT_FREE_INSTALLATION)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MarketingCampaignServiceAndRentingSourceTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 5 (Servicio como
    base) + Fase 6 (Renting como base), 2026-09-23 -- mismo patron que
    MarketingCampaignSourceAndBenefitsTestCase (Fase 4, Producto), extendido a los otros 2
    origenes de catalogo ya soportados por el serializer.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_source2_admin@example.com', password='testpassword123')
        self.client.force_authenticate(user=self.admin)

        service_category = ServiceCategory.objects.create(name='Cat Servicio Source Test', slug='cat-servicio-source-test')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=service_category, name='Mantenimiento CCTV Marketing Test',
            slug='mantenimiento-cctv-marketing-test', description='desc',
        )
        ServiceVariant.objects.create(
            service=self.service, sku='MKT-SVC-SRC-1', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('120000.00'), is_default=True,
        )

        renting_category = RentingCategory.objects.create(name='Cat Renting Source Test', slug='cat-renting-source-test')
        self.equipment = Equipment.objects.create(
            vendor=self.admin, category=renting_category, name='Camara PTZ Marketing Test',
            description='desc',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment, sku='MKT-RENT-SRC-1', rental_price_per_day=Decimal('45000.00'), stock=3,
        )

    def _payload(self, **overrides):
        data = {
            'title': 'Campaña de prueba', 'content': 'Contenido',
            'channels': ['email'], 'scheduled_at': timezone.now().isoformat(),
        }
        data.update(overrides)
        return data

    def test_create_from_service_resolves_real_preview(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'service', 'uuid': str(self.service.uuid)}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = response.data['items'][0]
        self.assertEqual(item['type'], 'service')
        self.assertEqual(item['uuid'], str(self.service.uuid))
        self.assertEqual(item['preview']['name'], 'Mantenimiento CCTV Marketing Test')

    def test_create_with_invalid_service_uuid_returns_400(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'service', 'uuid': '00000000-0000-0000-0000-000000000000'}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_from_renting_variant_resolves_real_preview(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'renting', 'uuid': str(self.variant.uuid)}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = response.data['items'][0]
        self.assertEqual(item['type'], 'renting')
        self.assertEqual(item['uuid'], str(self.variant.uuid))
        self.assertEqual(item['preview']['name'], 'Camara PTZ Marketing Test')
        self.assertEqual(item['preview']['selected_variant']['sku'], 'MKT-RENT-SRC-1')
        self.assertEqual(item['preview']['selected_variant']['stock'], 3)

    def test_create_with_invalid_renting_uuid_returns_400(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'renting', 'uuid': '00000000-0000-0000-0000-000000000000'}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MarketingCampaignCompositeTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 7 (campanas
    compuestas), 2026-09-23 -- "Lleva 02 camaras y te damos transporte e instalacion gratis":
    un CampaignItem con quantity=2 (misma camara), no dos items separados; items de tipos
    mixtos (producto + servicio) en la misma campana.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_composite_admin@example.com', password='testpassword123')
        self.client.force_authenticate(user=self.admin)
        category = Category.objects.create(name='Cat Composite Marketing', slug='cat-composite-marketing-test')
        self.camera = Product.objects.create(
            vendor=self.admin, category=category, name='Camara Compuesta Test', slug='camara-compuesta-test',
        )
        ProductVariant.objects.create(product=self.camera, sku='MKT-COMP-1', price=Decimal('350000.00'), stock=10, is_default=True)

        service_category = ServiceCategory.objects.create(name='Cat Servicio Composite Test', slug='cat-servicio-composite-test')
        self.install_service = TechnicalService.objects.create(
            vendor=self.admin, category=service_category, name='Instalacion Compuesta Test',
            slug='instalacion-compuesta-test', description='desc',
        )
        ServiceVariant.objects.create(
            service=self.install_service, sku='MKT-COMP-SVC-1', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('50000.00'), is_default=True,
        )

    def _payload(self, **overrides):
        data = {
            'title': 'Campaña de prueba compuesta', 'content': 'Contenido',
            'channels': ['email'], 'scheduled_at': timezone.now().isoformat(),
        }
        data.update(overrides)
        return data

    def test_two_cameras_is_one_item_with_quantity_two(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[{'type': 'product', 'uuid': str(self.camera.uuid), 'quantity': 2}],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['items']), 1)
        self.assertEqual(response.data['items'][0]['quantity'], 2)
        campaign = MarketingCampaign.objects.get(uuid=response.data['uuid'])
        self.assertEqual(campaign.items.count(), 1)
        self.assertEqual(campaign.items.first().quantity, 2)

    def test_mixed_type_items_product_and_service(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[
                {'type': 'product', 'uuid': str(self.camera.uuid), 'quantity': 2},
                {'type': 'service', 'uuid': str(self.install_service.uuid), 'quantity': 1},
            ],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['items']), 2)
        types = {i['type'] for i in response.data['items']}
        self.assertEqual(types, {'product', 'service'})

    def test_zero_items_is_from_scratch(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(items=[]), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['items'], [])

    def test_invalid_item_uuid_in_composite_list_returns_400(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            items=[
                {'type': 'product', 'uuid': str(self.camera.uuid), 'quantity': 2},
                {'type': 'product', 'uuid': '00000000-0000-0000-0000-000000000000'},
            ],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_acceptance_case_full(self):
        """Caso de aceptacion del plan (seccion 42), sin media/canales-UI: 2 camaras +
        transporte e instalacion gratis como beneficios (no como item de servicio -- ver
        docstring de CampaignItem: son beneficios de la campana, no un item de catalogo)."""
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            title='02 cámaras + transporte e instalación gratis',
            items=[{'type': 'product', 'uuid': str(self.camera.uuid), 'quantity': 2}],
            benefits=[
                {'benefit_type': CampaignBenefit.BENEFIT_FREE_SHIPPING, 'label': 'Transporte gratis'},
                {'benefit_type': CampaignBenefit.BENEFIT_FREE_INSTALLATION, 'label': 'Instalación gratis'},
            ],
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        campaign = MarketingCampaign.objects.get(uuid=response.data['uuid'])
        self.assertEqual(campaign.items.count(), 1)
        self.assertEqual(campaign.items.first().quantity, 2)
        self.assertEqual(campaign.benefits.count(), 2)
        get_response = self.client.get(f'/api/v1/marketing/campaigns/{campaign.uuid}/')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data['items'][0]['preview']['name'], 'Camara Compuesta Test')


class MarketingCampaignScratchFieldsTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 9 (campana
    desde cero, set completo de campos) + Fase 10 (contenido estructurado), 2026-09-23.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_scratch_admin@example.com', password='testpassword123')
        self.client.force_authenticate(user=self.admin)

    def _payload(self, **overrides):
        data = {
            'title': 'Campaña de prueba', 'content': 'Contenido',
            'channels': ['email'], 'scheduled_at': timezone.now().isoformat(),
        }
        data.update(overrides)
        return data

    def test_plan_example_from_scratch(self):
        """Recrea el ejemplo exacto del plan (seccion 12)."""
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            title='02 cámaras + instalación y transporte gratis',
            content='Lleva 2 cámaras de seguridad y recibe instalación y transporte gratis.',
            cta_label='Solicitar información',
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], '02 cámaras + instalación y transporte gratis')
        self.assertEqual(response.data['cta_label'], 'Solicitar información')
        campaign = MarketingCampaign.objects.get(uuid=response.data['uuid'])
        get_response = self.client.get(f'/api/v1/marketing/campaigns/{campaign.uuid}/')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            get_response.data['content'],
            'Lleva 2 cámaras de seguridad y recibe instalación y transporte gratis.',
        )

    def test_all_new_fields_persist_and_read_back(self):
        now = timezone.now()
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            description='Resumen corto', subheadline='Subtítulo de apoyo',
            cta_label='Comprar ahora', cta_url='https://sintel.net.co/promo',
            terms='Válido mientras haya stock.',
            valid_from=now.isoformat(), valid_until=(now + timezone.timedelta(days=7)).isoformat(),
            target_audience={'segment': 'clientes_recurrentes'},
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], 'Resumen corto')
        self.assertEqual(response.data['subheadline'], 'Subtítulo de apoyo')
        self.assertEqual(response.data['cta_url'], 'https://sintel.net.co/promo')
        self.assertEqual(response.data['terms'], 'Válido mientras haya stock.')
        self.assertEqual(response.data['target_audience'], {'segment': 'clientes_recurrentes'})

    def test_new_fields_are_optional(self):
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['description'], '')
        self.assertEqual(response.data['cta_label'], '')
        self.assertIsNone(response.data['valid_from'])

    def test_valid_until_before_valid_from_returns_400(self):
        now = timezone.now()
        response = self.client.post('/api/v1/marketing/campaigns/', self._payload(
            valid_from=now.isoformat(),
            valid_until=(now - timezone.timedelta(days=1)).isoformat(),
        ), format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('valid_until', response.data)


def _make_png_bytes(width=64, height=48) -> bytes:
    import io
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (width, height), color=(200, 50, 50)).save(buf, format='PNG')
    return buf.getvalue()


class MarketingCampaignMediaTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 11-14 (media
    imagen/video + galeria), 2026-09-23.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_media_admin@example.com', password='testpassword123')
        self.client.force_authenticate(user=self.admin)
        self.campaign = MarketingCampaign.objects.create(
            title='Campana con media', content='contenido', channels=['email'],
            scheduled_at=timezone.now(),
        )
        self.media_url = f'/api/v1/marketing/campaigns/{self.campaign.uuid}/media/'

    def _upload_png(self, name='foto.png'):
        from django.core.files.uploadedfile import SimpleUploadedFile
        png = SimpleUploadedFile(name, _make_png_bytes(), content_type='image/png')
        return self.client.post(self.media_url, {'file': png, 'media_type': 'IMAGE'}, format='multipart')

    def test_upload_valid_image_persists_real_dimensions(self):
        response = self._upload_png()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['media_type'], 'IMAGE')
        self.assertEqual(response.data['width'], 64)
        self.assertEqual(response.data['height'], 48)
        self.assertEqual(response.data['mime_type'], 'image/png')
        self.assertTrue(response.data['is_active'])
        self.assertEqual(self.campaign.media.count(), 1)

    def test_upload_valid_video_mp4(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_mp4 = SimpleUploadedFile('promo.mp4', b'\x00\x00\x00\x18ftypmp42' + b'0' * 100, content_type='video/mp4')
        response = self.client.post(self.media_url, {'file': fake_mp4, 'media_type': 'VIDEO'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['media_type'], 'VIDEO')
        self.assertEqual(response.data['mime_type'], 'video/mp4')
        # Sin libreria de metadata de video en el proyecto -- duration queda sin poblar a proposito.
        self.assertIsNone(response.data['duration'])

    def test_upload_rejects_fake_image_wrong_mime(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile('foto.jpg', b'esto no es una imagen real', content_type='image/jpeg')
        response = self.client.post(self.media_url, {'file': fake, 'media_type': 'IMAGE'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.campaign.media.count(), 0)

    def test_upload_rejects_video_with_wrong_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake = SimpleUploadedFile('promo.avi', b'0' * 100, content_type='video/x-msvideo')
        response = self.client.post(self.media_url, {'file': fake, 'media_type': 'VIDEO'}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(MARKETING_MEDIA_MAX_IMAGE_MB=0)
    def test_upload_rejects_image_exceeding_size_limit(self):
        response = self._upload_png()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tamano maximo', response.data['detail'])

    def test_delete_media(self):
        upload = self._upload_png()
        media_uuid = upload.data['uuid']
        response = self.client.delete(f'{self.media_url}{media_uuid}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.campaign.media.count(), 0)

    def test_toggle_media_active(self):
        upload = self._upload_png()
        media_uuid = upload.data['uuid']
        response = self.client.post(f'{self.media_url}{media_uuid}/toggle/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_active'])
        response = self.client.post(f'{self.media_url}{media_uuid}/toggle/')
        self.assertTrue(response.data['is_active'])

    def test_reorder_media(self):
        first = self._upload_png('a.png').data['uuid']
        second = self._upload_png('b.png').data['uuid']
        self.assertEqual(list(self.campaign.media.order_by('sort_order').values_list('uuid', flat=True)), [
            __import__('uuid').UUID(first), __import__('uuid').UUID(second),
        ])
        response = self.client.post(f'{self.media_url}reorder/', {'ordered_uuids': [second, first]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reordered = list(self.campaign.media.order_by('sort_order').values_list('uuid', flat=True))
        self.assertEqual([str(u) for u in reordered], [second, first])

    def test_editing_text_fields_does_not_touch_existing_media(self):
        """Fase 14: 'no debe perder medios existentes al editar otros campos'."""
        self._upload_png()
        self.assertEqual(self.campaign.media.count(), 1)
        response = self.client.patch(
            f'/api/v1/marketing/campaigns/{self.campaign.uuid}/',
            {'title': 'Titulo editado'}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.campaign.media.count(), 1)
        self.assertEqual(len(response.data['media']), 1)

    def test_campaign_detail_includes_media_gallery(self):
        self._upload_png()
        response = self.client.get(f'/api/v1/marketing/campaigns/{self.campaign.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['media']), 1)
        self.assertEqual(response.data['media'][0]['media_type'], 'IMAGE')


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


@override_settings(ROOT_URLCONF='ecommerce.urls')
class MarketingCampaignSendAndStatusTestCase(APITestCase):
    """PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 15-18 (2026-09-23):
    endpoint manual "Enviar ahora" (conecta MarketingCommands.dispatch(), ya existente, al CRUD
    admin) + campo `status` derivado."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='send_admin@example.com', password='x')
        self.customer = User.objects.create_user(email='send_customer@example.com', password='x')

    def _campaign(self, **kwargs):
        defaults = {'title': 'Campaña de prueba', 'content': 'Contenido', 'channels': [], 'scheduled_at': timezone.now()}
        defaults.update(kwargs)
        return MarketingCampaign.objects.create(**defaults)

    def test_send_requiere_admin(self):
        campaign = self._campaign(channels=['facebook'])
        self.client.force_authenticate(self.customer)
        resp = self.client.post(f'/api/v1/marketing/campaigns/{campaign.uuid}/send/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_send_rechaza_campana_sin_canales_reales(self):
        campaign = self._campaign(channels=[])
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/marketing/campaigns/{campaign.uuid}/send/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('marketing.tasks.send_via_channel_task.delay')
    def test_send_despacha_canales_de_broadcast_sin_necesitar_recipient(self, mock_delay):
        campaign = self._campaign(channels=['facebook', 'x'])
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/marketing/campaigns/{campaign.uuid}/send/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(resp.data['dispatched_channels']), ['facebook', 'x'])
        self.assertEqual(resp.data['skipped_channels'], [])
        self.assertEqual(mock_delay.call_count, 2)
        logs = list(CampaignLog.objects.filter(campaign=campaign))
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(l.recipient == 'broadcast' for l in logs))

    @patch('marketing.tasks.send_via_channel_task.delay')
    def test_send_omite_canal_directo_sin_recipient(self, mock_delay):
        campaign = self._campaign(channels=['email'])
        self.client.force_authenticate(self.admin)
        resp = self.client.post(f'/api/v1/marketing/campaigns/{campaign.uuid}/send/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['skipped_channels'], ['email'])
        self.assertEqual(resp.data['dispatched_channels'], [])
        mock_delay.assert_not_called()
        self.assertEqual(CampaignLog.objects.filter(campaign=campaign).count(), 0)

    @patch('marketing.tasks.send_via_channel_task.delay')
    def test_send_despacha_canal_directo_con_recipient_explicito(self, mock_delay):
        campaign = self._campaign(channels=['email', 'facebook'])
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            f'/api/v1/marketing/campaigns/{campaign.uuid}/send/',
            {'recipient': 'contacto@sintel.net.co'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(resp.data['dispatched_channels']), ['email', 'facebook'])
        self.assertEqual(resp.data['skipped_channels'], [])
        email_log = CampaignLog.objects.get(campaign=campaign, channel='email')
        self.assertEqual(email_log.recipient, 'contacto@sintel.net.co')
        fb_log = CampaignLog.objects.get(campaign=campaign, channel='facebook')
        self.assertEqual(fb_log.recipient, 'broadcast')

    def test_status_derivado_draft_running_completed(self):
        campaign = self._campaign(channels=['facebook'], scheduled_at=timezone.now() - timezone.timedelta(days=1))
        url = f'/api/v1/marketing/campaigns/{campaign.uuid}/'
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(url).data['status'], 'DRAFT')

        CampaignLog.objects.create(campaign=campaign, channel='facebook', recipient='broadcast')
        self.assertEqual(self.client.get(url).data['status'], 'RUNNING')

        campaign.is_completed = True
        campaign.save(update_fields=['is_completed'])
        self.assertEqual(self.client.get(url).data['status'], 'COMPLETED')

    def test_status_derivado_scheduled_cuando_es_futuro_sin_logs(self):
        campaign = self._campaign(channels=['facebook'], scheduled_at=timezone.now() + timezone.timedelta(days=1))
        self.client.force_authenticate(self.admin)
        resp = self.client.get(f'/api/v1/marketing/campaigns/{campaign.uuid}/')
        self.assertEqual(resp.data['status'], 'SCHEDULED')


class MarketingCampaignPreviewTestCase(APITestCase):
    """
    PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 22 (2026-09-23):
    el preview reusa MarketingCommands.build_message() -- el MISMO metodo que send_now() usa
    para el envio real -- para que nunca se desincronice de lo que realmente se enviaria.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='mkt_preview_admin@example.com', password='x')
        self.customer = User.objects.create_user(email='mkt_preview_customer@example.com', password='x')
        category = Category.objects.create(name='Cat Preview Marketing', slug='cat-preview-marketing-test')
        self.camera = Product.objects.create(
            vendor=self.admin, category=category, name='Camara Preview Test', slug='camara-preview-test',
        )
        ProductVariant.objects.create(product=self.camera, sku='MKT-PREV-1', price=Decimal('350000.00'), stock=10, is_default=True)

    def test_preview_requiere_admin(self):
        campaign = MarketingCampaign.objects.create(title='X', content='Y', channels=['email'], scheduled_at=timezone.now())
        self.client.force_authenticate(self.customer)
        resp = self.client.get(f'/api/v1/marketing/campaigns/{campaign.uuid}/preview/')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_preview_incluye_items_beneficios_y_cta_reales(self):
        self.client.force_authenticate(self.admin)
        create_resp = self.client.post('/api/v1/marketing/campaigns/', {
            'title': '02 camaras + transporte e instalacion gratis',
            'content': 'Lleva 2 camaras de seguridad y recibe instalacion y transporte gratis.',
            'channels': ['email', 'facebook'],
            'scheduled_at': timezone.now().isoformat(),
            'cta_label': 'Solicitar informacion',
            'cta_url': 'https://sintel.net.co/contacto',
            'terms': 'Aplican condiciones.',
            'items': [{'type': 'product', 'uuid': str(self.camera.uuid), 'quantity': 2}],
            'benefits': [
                {'benefit_type': 'FREE_SHIPPING', 'label': 'Transporte gratis'},
                {'benefit_type': 'FREE_INSTALLATION', 'label': 'Instalacion gratis'},
            ],
        }, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        campaign_uuid = create_resp.data['uuid']

        resp = self.client.get(f'/api/v1/marketing/campaigns/{campaign_uuid}/preview/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        channels = {p['channel'] for p in resp.data['channels']}
        self.assertEqual(channels, {'email', 'facebook'})

        body = resp.data['channels'][0]['body']
        self.assertIn('Camara Preview Test', body)
        self.assertIn('x2', body)
        self.assertIn('Transporte gratis', body)
        self.assertIn('Instalacion gratis', body)
        self.assertIn('Solicitar informacion', body)
        self.assertIn('https://sintel.net.co/contacto', body)
        self.assertIn('Aplican condiciones.', body)

        campaign = MarketingCampaign.objects.get(uuid=campaign_uuid)
        campaign.delete()

    def test_preview_de_campana_desde_cero_sin_items(self):
        self.client.force_authenticate(self.admin)
        campaign = MarketingCampaign.objects.create(
            title='Promo generica', content='Texto libre.', channels=['email'], scheduled_at=timezone.now(),
        )
        resp = self.client.get(f'/api/v1/marketing/campaigns/{campaign.uuid}/preview/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['channels'][0]['body'], 'Texto libre.')
