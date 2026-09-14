"""
shop/tests_catalog.py

Cobertura del catalogo enriquecido de Product (2026-08-03), espejo de
renting.Equipment. Cubre: service layer (Commands/Selectors) para un recurso
simple (ProductFeature) y el caso anidado (ProductSpecificationGroup +
ProductSpecification), mas los endpoints admin via dashboard (permisos,
ciclo CRUD completo, reorder, toggle, duplicate, y el caso de archivo real
para ProductDocument). No repite el mismo test 11 veces -- la delegacion
generica (ProductCatalogChildOrchestrator) es identica para los 8 recursos
no probados explicitamente aqui; el smoke test final confirma que los 11
estan realmente registrados y accesibles.
"""
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from shop.models import (
    Category, Product,
    ProductFeature, ProductSpecificationGroup, ProductSpecification,
)
from shop.services.catalog import (
    ProductFeatureCommands,
    ProductSpecificationGroupCommands, ProductSpecificationCommands,
)

User = get_user_model()


def _make_product(vendor):
    # sufijo unico -- Category.name y Product.slug son unique=True, y este helper puede
    # llamarse mas de una vez en el mismo test (ej. "otro producto").
    suffix = uuid.uuid4().hex[:8]
    category = Category.objects.create(name=f'Cat Catalogo Test {suffix}', slug=f'cat-catalogo-test-{suffix}')
    return Product.objects.create(
        vendor=vendor, category=category, name='Producto Catalogo Test', slug=f'producto-catalogo-test-{suffix}',
    )


class ProductFeatureServiceLayerTestCase(APITestCase):
    """Service layer directo (sin HTTP) -- representativo del patron compartido por los
    8 recursos con el mismo shape (title/description-o-value/icon/position/is_active)."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_cat@example.com', password='testpass123')
        self.product = _make_product(self.vendor)

    def test_create_update_toggle_duplicate_delete(self):
        feature = ProductFeatureCommands.create(self.product, title='Resolucion', value='4MP')
        self.assertEqual(feature.position, 0)
        self.assertTrue(feature.is_active)

        updated = ProductFeatureCommands.update(feature, value='8MP')
        self.assertEqual(updated.value, '8MP')

        toggled = ProductFeatureCommands.toggle_active(feature)
        self.assertFalse(toggled.is_active)

        copy = ProductFeatureCommands.duplicate(feature)
        self.assertEqual(copy.title, 'Resolucion (copia)')
        self.assertNotEqual(copy.pk, feature.pk)

        ProductFeatureCommands.delete(feature)
        feature.refresh_from_db()
        self.assertTrue(feature.is_deleted)
        # El soft-delete no debe filtrar al selector activo.
        self.assertEqual(ProductFeature.objects.filter(product=self.product, is_deleted=False).count(), 1)

    def test_reorder(self):
        f1 = ProductFeatureCommands.create(self.product, title='A')
        f2 = ProductFeatureCommands.create(self.product, title='B')
        f3 = ProductFeatureCommands.create(self.product, title='C')

        ProductFeatureCommands.reorder(self.product.id, [str(f3.uuid), str(f1.uuid), str(f2.uuid)])

        f1.refresh_from_db(); f2.refresh_from_db(); f3.refresh_from_db()
        self.assertEqual(f3.position, 0)
        self.assertEqual(f1.position, 1)
        self.assertEqual(f2.position, 2)


class ProductSpecificationNestedTestCase(APITestCase):
    """Caso anidado: ProductSpecification cuelga de ProductSpecificationGroup ademas de
    Product -- distinto del resto (shape plano)."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_spec@example.com', password='testpass123')
        self.product = _make_product(self.vendor)
        self.group = ProductSpecificationGroupCommands.create(self.product, name='Camara')

    def test_specification_must_belong_to_a_group_of_the_same_product(self):
        other_product = _make_product(self.vendor)
        other_group = ProductSpecificationGroupCommands.create(other_product, name='Otro grupo')

        with self.assertRaises(ValueError):
            ProductSpecificationCommands.create(self.product, other_group, name='Resolucion', value='4MP')

    def test_deleting_group_soft_deletes_its_specifications(self):
        spec = ProductSpecificationCommands.create(self.product, self.group, name='Resolucion', value='4MP')

        ProductSpecificationGroupCommands.delete(self.group)

        self.group.refresh_from_db()
        spec.refresh_from_db()
        self.assertTrue(self.group.is_deleted)
        self.assertTrue(spec.is_deleted)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ProductCatalogAdminEndpointsTestCase(APITestCase):
    """Ciclo completo via HTTP -- permisos, CRUD, reorder/toggle/duplicate, y el caso de
    archivo real de ProductDocument (magic-bytes/extension, mismo validate_file que renting)."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='admin_catalog@example.com', password='testpass123')
        self.customer = User.objects.create_user(email='customer_catalog@example.com', password='testpass123')
        self.vendor = User.objects.create_user(email='vendor_endpoint@example.com', password='testpass123')
        self.product = _make_product(self.vendor)

    def test_anonymous_and_non_admin_blocked(self):
        url = f'/api/v1/dashboard/product-features/?product={self.product.uuid}'
        anon = self.client.get(url)
        self.assertIn(anon.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        self.client.force_authenticate(user=self.customer)
        forbidden = self.client.get(url)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_feature_full_crud_cycle(self):
        self.client.force_authenticate(user=self.admin)

        create = self.client.post('/api/v1/dashboard/product-features/', {
            'product': str(self.product.uuid), 'title': 'Alcance IR', 'value': '20m',
        })
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        feature_uuid = create.data['uuid']

        listed = self.client.get(f'/api/v1/dashboard/product-features/?product={self.product.uuid}')
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listed.data), 1)

        patched = self.client.patch(f'/api/v1/dashboard/product-features/{feature_uuid}/', {'value': '30m'})
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(patched.data['value'], '30m')

        toggled = self.client.post(f'/api/v1/dashboard/product-features/{feature_uuid}/toggle-active/')
        self.assertEqual(toggled.status_code, status.HTTP_200_OK)
        self.assertFalse(toggled.data['is_active'])

        duplicated = self.client.post(f'/api/v1/dashboard/product-features/{feature_uuid}/duplicate/')
        self.assertEqual(duplicated.status_code, status.HTTP_201_CREATED)
        self.assertIn('(copia)', duplicated.data['title'])

        deleted = self.client.delete(f'/api/v1/dashboard/product-features/{feature_uuid}/')
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_document_upload_requires_valid_file(self):
        self.client.force_authenticate(user=self.admin)

        fake_pdf = SimpleUploadedFile('ficha.pdf', b'%PDF-1.4 contenido de prueba', content_type='application/pdf')
        response = self.client.post('/api/v1/dashboard/product-documents/', {
            'product': str(self.product.uuid),
            'title': 'Ficha tecnica',
            'document_type': 'FICHA_TECNICA',
            'file': fake_pdf,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['document_type'], 'FICHA_TECNICA')

    def test_document_upload_rejects_disallowed_extension(self):
        self.client.force_authenticate(user=self.admin)

        fake_exe = SimpleUploadedFile('firmware.exe', b'MZ fake binary', content_type='application/octet-stream')
        response = self.client.post('/api/v1/dashboard/product-documents/', {
            'product': str(self.product.uuid),
            'title': 'Archivo invalido',
            'document_type': 'OTRO',
            'file': fake_exe,
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_all_11_resources_are_registered_and_reachable(self):
        self.client.force_authenticate(user=self.admin)
        resources = [
            'product-included-items', 'product-excluded-items', 'product-features',
            'product-specification-groups', 'product-requirements',
            'product-services-included', 'product-optional-services',
            'product-faqs', 'product-videos', 'product-documents',
            'product-catalog-images',
        ]
        for resource in resources:
            response = self.client.get(f'/api/v1/dashboard/{resource}/?product={self.product.uuid}')
            self.assertEqual(response.status_code, status.HTTP_200_OK, msg=f'{resource} fallo: {response.data}')
            self.assertEqual(response.data, [])
