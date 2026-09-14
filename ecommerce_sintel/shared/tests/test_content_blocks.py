"""
shared/tests/test_content_blocks.py

Cubre ContentBlockConfig/CatalogRelation (shared/models.py, shared/services/
content_blocks.py) y su exposicion via el endpoint publico de Shop y los
endpoints admin -- Fase 3, reingenieria PDP (2026-08-05).
"""
import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from shop.models import Category, Product
from shared.models import ContentBlockConfig, CatalogRelation
from shared.services.content_blocks import (
    ContentBlockConfigSelector, ContentBlockConfigCommands,
    CatalogRelationSelector, CatalogRelationCommands,
)

User = get_user_model()


def _make_product(**overrides):
    token = uuid.uuid4().hex[:8]
    category = Category.objects.create(
        name=overrides.pop('category_name', f'Categoria CB Test {token}'),
        slug=overrides.pop('category_slug', f'categoria-cb-test-{token}'),
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
class ContentBlockConfigServiceTestCase(APITestCase):
    """Selector/Commands puros, sin pasar por la API -- backward-compat es el hallazgo central del diseno (SS7)."""

    def setUp(self):
        self.user = User.objects.create_user(email='cbvendor@example.com', password='testpass123')
        self.product = _make_product(vendor=self.user)
        self.content_type = ContentType.objects.get_for_model(Product)

    def test_default_order_when_no_rows_exist(self):
        blocks = ContentBlockConfigSelector.resolve_for(self.content_type, self.product.uuid)
        self.assertEqual(len(blocks), 15)
        self.assertEqual(blocks[0]['block_type'], ContentBlockConfig.BLOCK_DESCRIPTION)
        self.assertTrue(all(b['is_visible'] for b in blocks))
        self.assertEqual(ContentBlockConfig.objects.filter(object_uuid=self.product.uuid).count(), 0)

    def test_set_order_persists_and_resolves(self):
        new_order = ['warranty'] + [b for b in ContentBlockConfig.DEFAULT_ORDER if b != 'warranty']
        ContentBlockConfigCommands.set_order(self.content_type, self.product.uuid, new_order)
        blocks = ContentBlockConfigSelector.resolve_for(self.content_type, self.product.uuid)
        self.assertEqual(blocks[0]['block_type'], 'warranty')
        self.assertEqual(blocks[0]['display_order'], 0)

    def test_set_visibility_persists(self):
        ContentBlockConfigCommands.set_visibility(self.content_type, self.product.uuid, 'description', False)
        blocks = ContentBlockConfigSelector.resolve_for(self.content_type, self.product.uuid)
        desc = next(b for b in blocks if b['block_type'] == 'description')
        self.assertFalse(desc['is_visible'])

    def test_set_visibility_twice_does_not_duplicate_row(self):
        ContentBlockConfigCommands.set_visibility(self.content_type, self.product.uuid, 'faq', False)
        ContentBlockConfigCommands.set_visibility(self.content_type, self.product.uuid, 'faq', True)
        self.assertEqual(
            ContentBlockConfig.objects.filter(object_uuid=self.product.uuid, block_type='faq').count(), 1,
        )


@override_settings(ROOT_URLCONF='ecommerce.urls')
class CatalogRelationServiceTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='cbvendor2@example.com', password='testpass123')
        self.product = _make_product(vendor=self.user, name='Producto A')
        self.related = _make_product(vendor=self.user, name='Producto B')
        self.content_type = ContentType.objects.get_for_model(Product)

    def test_add_and_resolve_relation(self):
        CatalogRelationCommands.add(
            self.content_type, self.product.uuid, self.content_type, self.related.uuid,
            CatalogRelation.RELATION_COMPATIBLE,
        )
        resolved = CatalogRelationSelector.get_related_objects(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_COMPATIBLE,
        )
        self.assertEqual([p.id for p in resolved], [self.related.id])

    def test_relation_types_are_independent(self):
        CatalogRelationCommands.add(
            self.content_type, self.product.uuid, self.content_type, self.related.uuid,
            CatalogRelation.RELATION_ACCESSORY,
        )
        compatible = CatalogRelationSelector.get_related_objects(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_COMPATIBLE,
        )
        accessories = CatalogRelationSelector.get_related_objects(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_ACCESSORY,
        )
        self.assertEqual(compatible, [])
        self.assertEqual([p.id for p in accessories], [self.related.id])

    def test_remove_relation_excludes_from_resolve(self):
        relation = CatalogRelationCommands.add(
            self.content_type, self.product.uuid, self.content_type, self.related.uuid,
            CatalogRelation.RELATION_RELATED,
        )
        CatalogRelationCommands.remove(relation)
        resolved = CatalogRelationSelector.get_related_objects(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_RELATED,
        )
        self.assertEqual(resolved, [])

    def test_reorder_relations(self):
        third = _make_product(vendor=self.user, name='Producto C')
        rel_b = CatalogRelationCommands.add(
            self.content_type, self.product.uuid, self.content_type, self.related.uuid,
            CatalogRelation.RELATION_RELATED, display_order=0,
        )
        rel_c = CatalogRelationCommands.add(
            self.content_type, self.product.uuid, self.content_type, third.uuid,
            CatalogRelation.RELATION_RELATED, display_order=1,
        )
        CatalogRelationCommands.reorder(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_RELATED,
            [str(rel_c.uuid), str(rel_b.uuid)],
        )
        resolved = CatalogRelationSelector.get_related_objects(
            self.content_type, self.product.uuid, CatalogRelation.RELATION_RELATED,
        )
        self.assertEqual([p.id for p in resolved], [third.id, self.related.id])


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ProductDetailSerializerContentBlocksTestCase(APITestCase):
    """Integracion via el endpoint publico GET /shop/products/{uuid}/detail/."""

    def setUp(self):
        self.user = User.objects.create_user(email='cbvendor3@example.com', password='testpass123')
        self.product = _make_product(vendor=self.user, warranty='12 meses', scope='Incluye instalacion basica')
        self.related = _make_product(vendor=self.user, name='Accesorio X')
        content_type = ContentType.objects.get_for_model(Product)
        CatalogRelationCommands.add(
            content_type, self.product.uuid, content_type, self.related.uuid,
            CatalogRelation.RELATION_ACCESSORY,
        )

    def test_detail_endpoint_exposes_new_fields(self):
        response = self.client.get(f'/api/v1/shop/products/{self.product.uuid}/detail/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['warranty'], '12 meses')
        self.assertEqual(response.data['scope'], 'Incluye instalacion basica')
        self.assertEqual(len(response.data['content_blocks']), 15)
        self.assertEqual(response.data['related_products'], [])
        self.assertEqual(response.data['compatible_products'], [])
        self.assertEqual(len(response.data['accessories']), 1)
        self.assertEqual(response.data['accessories'][0]['name'], 'Accesorio X')


@override_settings(ROOT_URLCONF='ecommerce.urls')
class AdminContentBlockEndpointsTestCase(APITestCase):
    """Contrato admin (dashboard) -- mismo esquema de permisos que los otros
    endpoints de catalogo enriquecido de Shop (IsAdminUser)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='cbadmin@example.com', password='testpass123', is_staff=True, is_superuser=True,
        )
        self.customer = User.objects.create_user(email='cbcustomer@example.com', password='testpass123')
        self.product = _make_product(vendor=self.admin)
        self.related = _make_product(vendor=self.admin, name='Producto Relacionado')

    def test_list_content_blocks_requires_admin(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(f'/api/v1/dashboard/product-content-blocks/?product={self.product.uuid}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_content_blocks_default_order(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/v1/dashboard/product-content-blocks/?product={self.product.uuid}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 15)

    def test_reorder_and_set_visibility_roundtrip(self):
        self.client.force_authenticate(user=self.admin)
        new_order = ['faq'] + [b for b in ContentBlockConfig.DEFAULT_ORDER if b != 'faq']
        reorder_resp = self.client.post(
            '/api/v1/dashboard/product-content-blocks/reorder/',
            {'product': str(self.product.uuid), 'ordered_block_types': new_order},
            format='json',
        )
        self.assertEqual(reorder_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(reorder_resp.data[0]['block_type'], 'faq')

        visibility_resp = self.client.post(
            '/api/v1/dashboard/product-content-blocks/set-visibility/',
            {'product': str(self.product.uuid), 'block_type': 'faq', 'is_visible': False},
            format='json',
        )
        self.assertEqual(visibility_resp.status_code, status.HTTP_200_OK)
        faq_block = next(b for b in visibility_resp.data if b['block_type'] == 'faq')
        self.assertFalse(faq_block['is_visible'])

    def test_create_list_delete_relation(self):
        self.client.force_authenticate(user=self.admin)
        create_resp = self.client.post(
            '/api/v1/dashboard/product-relations/',
            {
                'product': str(self.product.uuid),
                'relation_type': 'compatible',
                'related_product': str(self.related.uuid),
            },
            format='json',
        )
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)
        relation_uuid = create_resp.data['uuid']
        self.assertEqual(create_resp.data['product']['name'], 'Producto Relacionado')

        list_resp = self.client.get(
            f'/api/v1/dashboard/product-relations/?product={self.product.uuid}&relation_type=compatible',
        )
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_resp.data), 1)

        delete_resp = self.client.delete(f'/api/v1/dashboard/product-relations/{relation_uuid}/')
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        list_after_delete = self.client.get(
            f'/api/v1/dashboard/product-relations/?product={self.product.uuid}&relation_type=compatible',
        )
        self.assertEqual(list_after_delete.data, [])

    def test_cannot_relate_product_to_itself(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/v1/dashboard/product-relations/',
            {
                'product': str(self.product.uuid),
                'relation_type': 'related',
                'related_product': str(self.product.uuid),
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
