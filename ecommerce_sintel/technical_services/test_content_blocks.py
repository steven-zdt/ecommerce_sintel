"""
technical_services/test_content_blocks.py

Cubre el catalogo enriquecido de TechnicalService (models.py, services/catalog.py)
y su exposicion via el endpoint publico de detalle y los endpoints admin --
reingenieria SDP (2026-08-05). Mismo patron que
shared/tests/test_content_blocks.py (Shop) -- aca ademas se cubre el orden
por defecto PROPIO de servicios (18 bloques, no los 15 de Shop -- ajustado de
19 a 18 en la auditoria FASE 7 2026-08-14 al quitar 'support', bloque sin
backing data ni render en ServiceDetailContent.vue) y la relacion cruzada
real hacia shop.Product.
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from technical_services.models import TechnicalService, ServiceCategory
from shop.models import Category as ShopCategory, Product
from shared.models import ContentBlockConfig, CatalogRelation
from shared.services.content_blocks import (
    ContentBlockConfigSelector, ContentBlockConfigCommands,
    CatalogRelationSelector, CatalogRelationCommands,
)

User = get_user_model()


def _make_service(**overrides):
    token = uuid.uuid4().hex[:8]
    category = ServiceCategory.objects.create(
        name=overrides.pop('category_name', f'Categoria CB Test {token}'),
        slug=overrides.pop('category_slug', f'categoria-cb-test-{token}'),
    )
    vendor = overrides.pop('vendor', None)
    defaults = {
        'vendor': vendor,
        'category': category,
        'name': f'Servicio CB Test {token}',
        'slug': f'servicio-cb-test-{token}',
    }
    defaults.update(overrides)
    return TechnicalService.objects.create(**defaults)


def _make_product(**overrides):
    token = uuid.uuid4().hex[:8]
    category = ShopCategory.objects.create(
        name=overrides.pop('category_name', f'Categoria Prod CB {token}'),
        slug=overrides.pop('category_slug', f'categoria-prod-cb-{token}'),
    )
    vendor = overrides.pop('vendor', None)
    defaults = {
        'vendor': vendor,
        'category': category,
        'name': f'Producto CB Test {token}',
        'slug': f'producto-cb-test-{token}',
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ServiceContentBlockDefaultOrderTestCase(APITestCase):
    """El orden por defecto de servicios (SERVICE_DEFAULT_ORDER, 18 bloques)
    es distinto del de Shop (DEFAULT_ORDER, 15) -- ambos deben seguir
    funcionando de forma independiente sobre el mismo modelo compartido."""

    def setUp(self):
        self.user = User.objects.create_user(email='svccbvendor@example.com', password='testpass123')
        self.service = _make_service(vendor=self.user)
        self.content_type = ContentType.objects.get_for_model(TechnicalService)

    def test_default_order_has_18_service_specific_blocks(self):
        blocks = ContentBlockConfigSelector.resolve_for(
            self.content_type, self.service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER,
        )
        self.assertEqual(len(blocks), 18)
        block_types = {b['block_type'] for b in blocks}
        self.assertTrue({'coverage', 'process', 'materials', 'technicians', 'recommended_products'} <= block_types)
        self.assertEqual(ContentBlockConfig.objects.filter(object_uuid=self.service.uuid).count(), 0)

    def test_set_order_with_service_specific_block_type(self):
        new_order = ['process'] + [b for b in ContentBlockConfig.SERVICE_DEFAULT_ORDER if b != 'process']
        ContentBlockConfigCommands.set_order(self.content_type, self.service.uuid, new_order)
        blocks = ContentBlockConfigSelector.resolve_for(
            self.content_type, self.service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER,
        )
        self.assertEqual(blocks[0]['block_type'], 'process')

    def test_set_visibility_with_service_specific_block_type(self):
        ContentBlockConfigCommands.set_visibility(
            self.content_type, self.service.uuid, 'materials', False, ContentBlockConfig.SERVICE_DEFAULT_ORDER,
        )
        blocks = ContentBlockConfigSelector.resolve_for(
            self.content_type, self.service.uuid, ContentBlockConfig.SERVICE_DEFAULT_ORDER,
        )
        materials_block = next(b for b in blocks if b['block_type'] == 'materials')
        self.assertFalse(materials_block['is_visible'])


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ServiceCatalogRelationCrossModuleTestCase(APITestCase):
    """CatalogRelation ya soportaba relacion cruzada por diseno (Regla 6 del
    brief de Shop) -- este es el primer uso real: TechnicalService -> shop.Product."""

    def setUp(self):
        self.user = User.objects.create_user(email='svccbvendor2@example.com', password='testpass123')
        self.service = _make_service(vendor=self.user)
        self.product = _make_product(vendor=self.user)
        self.service_ct = ContentType.objects.get_for_model(TechnicalService)
        self.product_ct = ContentType.objects.get_for_model(Product)

    def test_add_and_resolve_cross_module_relation(self):
        CatalogRelationCommands.add(
            self.service_ct, self.service.uuid, self.product_ct, self.product.uuid,
            CatalogRelation.RELATION_ACCESSORY,
        )
        resolved = CatalogRelationSelector.get_related_objects(
            self.service_ct, self.service.uuid, CatalogRelation.RELATION_ACCESSORY,
        )
        self.assertEqual(len(resolved), 1)
        self.assertIsInstance(resolved[0], Product)
        self.assertEqual(resolved[0].id, self.product.id)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class TechnicalServiceDetailSerializerTestCase(APITestCase):
    """Integracion via el endpoint publico GET /services/services/{uuid}/detail/."""

    def setUp(self):
        self.user = User.objects.create_user(email='svccbvendor3@example.com', password='testpass123')
        self.service = _make_service(vendor=self.user, warranty='6 meses', scope='Incluye visita tecnica')
        self.product = _make_product(vendor=self.user, name='Kit de instalacion')
        service_ct = ContentType.objects.get_for_model(TechnicalService)
        product_ct = ContentType.objects.get_for_model(Product)
        CatalogRelationCommands.add(
            service_ct, self.service.uuid, product_ct, self.product.uuid,
            CatalogRelation.RELATION_ACCESSORY,
        )

    def test_detail_endpoint_exposes_new_fields(self):
        response = self.client.get(f'/api/v1/services/services/{self.service.uuid}/detail/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['warranty'], '6 meses')
        self.assertEqual(response.data['scope'], 'Incluye visita tecnica')
        self.assertEqual(len(response.data['content_blocks']), 18)
        self.assertEqual(response.data['related_services'], [])
        self.assertEqual(response.data['compatible_services'], [])
        self.assertEqual(len(response.data['recommended_products']), 1)
        self.assertEqual(response.data['recommended_products'][0]['name'], 'Kit de instalacion')


@override_settings(ROOT_URLCONF='ecommerce.urls')
class AdminServiceContentBlockEndpointsTestCase(APITestCase):
    """Contrato admin (dashboard) -- mismo esquema de permisos que Shop (IsAdminUser)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='svccbadmin@example.com', password='testpass123', is_staff=True, is_superuser=True,
        )
        self.customer = User.objects.create_user(email='svccbcustomer@example.com', password='testpass123')
        self.service = _make_service(vendor=self.admin)
        self.other_service = _make_service(vendor=self.admin, name='Servicio Relacionado')
        self.product = _make_product(vendor=self.admin)

    def test_list_content_blocks_requires_admin(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f'/api/v1/dashboard/service-content-blocks/?service={self.service.uuid}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_content_blocks_default_order_has_18_blocks(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/v1/dashboard/service-content-blocks/?service={self.service.uuid}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 18)

    def test_reorder_and_set_visibility_roundtrip(self):
        self.client.force_authenticate(user=self.admin)
        new_order = ['coverage'] + [b for b in ContentBlockConfig.SERVICE_DEFAULT_ORDER if b != 'coverage']
        reorder_resp = self.client.post(
            '/api/v1/dashboard/service-content-blocks/reorder/',
            {'service': str(self.service.uuid), 'ordered_block_types': new_order},
            format='json',
        )
        self.assertEqual(reorder_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reorder_resp.data[0]['block_type'], 'coverage')

        visibility_resp = self.client.post(
            '/api/v1/dashboard/service-content-blocks/set-visibility/',
            {'service': str(self.service.uuid), 'block_type': 'coverage', 'is_visible': False},
            format='json',
        )
        self.assertEqual(visibility_resp.status_code, status.HTTP_200_OK)
        coverage_block = next(b for b in visibility_resp.data if b['block_type'] == 'coverage')
        self.assertFalse(coverage_block['is_visible'])

    def test_create_list_delete_relation_to_another_service(self):
        self.client.force_authenticate(user=self.admin)
        create_resp = self.client.post(
            '/api/v1/dashboard/service-relations/',
            {
                'service': str(self.service.uuid),
                'relation_type': 'related',
                'related_entity_type': 'service',
                'related_uuid': str(self.other_service.uuid),
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['related_entity_type'], 'service')
        self.assertEqual(create_resp.data['entity']['name'], 'Servicio Relacionado')
        relation_uuid = create_resp.data['uuid']

        list_resp = self.client.get(
            f'/api/v1/dashboard/service-relations/?service={self.service.uuid}&relation_type=related',
        )
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 1)

        delete_resp = self.client.delete(f'/api/v1/dashboard/service-relations/{relation_uuid}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_relation_to_shop_product(self):
        self.client.force_authenticate(user=self.admin)
        create_resp = self.client.post(
            '/api/v1/dashboard/service-relations/',
            {
                'service': str(self.service.uuid),
                'relation_type': 'accessory',
                'related_entity_type': 'product',
                'related_uuid': str(self.product.uuid),
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_resp.data['related_entity_type'], 'product')
        self.assertEqual(create_resp.data['entity']['name'], self.product.name)

    def test_cannot_relate_service_to_itself(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/v1/dashboard/service-relations/',
            {
                'service': str(self.service.uuid),
                'relation_type': 'related',
                'related_entity_type': 'service',
                'related_uuid': str(self.service.uuid),
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
