from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile
from shop.models import Category, Product, ProductReview, ProductVariant, ProductFunctioningStep
from shop.api.serializers import ProductReviewSerializer
from shop.services.catalog import ProductFunctioningStepCommands
from orders.models import Order, OrderItem

User = get_user_model()


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ProductReviewDuplicatePreventionTestCase(APITestCase):
    """
    Cubre un hallazgo de Fase 6 (auditoria de BD, 2026-07-03): la prevencion de reseñas
    duplicadas (ProductReviewSerializer.validate()) solo existia a nivel de aplicacion, sin
    constraint de BD -- una condicion de carrera (dos envios simultaneos) podia dejar
    reseñas duplicadas. Se agrego unique_together=('user','product') en ProductReview.Meta
    (verificado que no habia duplicados existentes antes de aplicar la migracion) y se
    envolvio ProductReviewCommands.create_review() en el ViewSet con manejo de
    IntegrityError, para que el caso de carrera devuelva 400 limpio en vez de 500.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='reviewer@example.com', password='testpass123')
        UserProfile.objects.create(user=self.user, user_type='CUSTOMER')
        category = Category.objects.create(name='Categoria Review', slug='categoria-review-test')
        self.product = Product.objects.create(
            vendor=self.user, category=category, name='Producto Review Test', slug='producto-review-test',
        )
        variant = ProductVariant.objects.create(product=self.product, sku='REVIEW-SKU-1', price=10000, stock=5)
        # [AGREGADO 2026-08-06] Gate de compra: desde ahora, resenar exige una Order
        # DELIVERED con el producto (ver ProductReviewCommands.create_review()) --
        # sin esto, ambos tests de esta clase fallarian antes de llegar al chequeo
        # de duplicado que realmente quieren probar.
        order = Order.objects.create(user=self.user, status=Order.STATUS_DELIVERED, total_amount=10000)
        OrderItem.objects.create(order=order, variant=variant, item_name=self.product.name, sku=variant.sku, quantity=1, price=10000)
        ProductReview.objects.create(user=self.user, product=self.product, rating=4, comment='Primera reseña')

    def test_second_review_blocked_by_serializer_validation(self):
        """Camino normal: el .exists() del serializer atrapa el duplicado con 400."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/v1/shop/products/{self.product.uuid}/review/',
            {'rating': 5, 'comment': 'Segunda reseña'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_race_condition_blocked_at_db_level_returns_400_not_500(self):
        """
        Simula la condicion de carrera: dos requests pasan la validacion del serializer
        (aqui forzado con un patch) antes de que cualquiera confirme en BD. La constraint
        unique_together debe bloquear el segundo INSERT, y el ViewSet debe traducir el
        IntegrityError resultante a un 400 legible, no dejarlo escalar a un 500.
        """
        self.client.force_authenticate(user=self.user)
        with patch.object(ProductReviewSerializer, 'validate', new=lambda self, data: data):
            response = self.client.post(
                f'/api/v1/shop/products/{self.product.uuid}/review/',
                {'rating': 5, 'comment': 'Segunda reseña (race)'},
            )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Ya has calificado', response.data['detail'])
        self.assertEqual(ProductReview.objects.filter(user=self.user, product=self.product).count(), 1)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ProductReviewPurchaseGateTestCase(APITestCase):
    """
    [AGREGADO 2026-08-06] Cubre el gate de compra agregado a
    ProductReviewCommands.create_review() -- mismo criterio "ownership + estado
    terminal" que ya usaban renting.EquipmentReviewCommands/
    technical_services.ServiceReviewCommands (Order en status DELIVERED, no solo
    PAID), cerrando la unica diferencia real que habia entre los 3 dominios de
    resenas de catalogo (ver PLAN_SPRINT6_EVALUACION_2026-08-05.md #1.2).
    """

    def setUp(self):
        self.user = User.objects.create_user(email='buyer@example.com', password='testpass123')
        UserProfile.objects.create(user=self.user, user_type='CUSTOMER')
        category = Category.objects.create(name='Categoria Gate', slug='categoria-gate-test')
        self.product = Product.objects.create(
            vendor=self.user, category=category, name='Producto Gate Test', slug='producto-gate-test',
        )
        self.variant = ProductVariant.objects.create(product=self.product, sku='GATE-SKU-1', price=10000, stock=5)

    def _post_review(self):
        self.client.force_authenticate(user=self.user)
        return self.client.post(
            f'/api/v1/shop/products/{self.product.uuid}/review/',
            {'rating': 5, 'comment': 'Excelente producto'},
        )

    def test_review_blocked_without_any_order(self):
        """Sin ninguna Order del producto: 400, con el mensaje del gate de compra."""
        response = self._post_review()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprado y recibido', response.data['detail'])
        self.assertFalse(ProductReview.objects.filter(user=self.user, product=self.product).exists())

    def test_review_blocked_with_order_not_yet_delivered(self):
        """Order existe pero no esta DELIVERED (ej. PAID): sigue bloqueado."""
        order = Order.objects.create(user=self.user, status=Order.STATUS_PAID, total_amount=10000)
        OrderItem.objects.create(
            order=order, variant=self.variant, item_name=self.product.name,
            sku=self.variant.sku, quantity=1, price=10000,
        )
        response = self._post_review()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprado y recibido', response.data['detail'])

    def test_review_allowed_with_delivered_order(self):
        """Order DELIVERED del producto: permite crear la resena, marcada como compra verificada."""
        order = Order.objects.create(user=self.user, status=Order.STATUS_DELIVERED, total_amount=10000)
        OrderItem.objects.create(
            order=order, variant=self.variant, item_name=self.product.name,
            sku=self.variant.sku, quantity=1, price=10000,
        )
        response = self._post_review()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = ProductReview.objects.get(user=self.user, product=self.product)
        self.assertTrue(review.is_verified_purchase)

    def test_review_blocked_for_delivered_order_of_a_different_product(self):
        """Order DELIVERED existe, pero de OTRO producto: no habilita resenar este."""
        other_category = Category.objects.create(name='Otra Categoria', slug='otra-categoria-gate')
        other_product = Product.objects.create(
            vendor=self.user, category=other_category, name='Otro Producto', slug='otro-producto-gate',
        )
        other_variant = ProductVariant.objects.create(product=other_product, sku='GATE-SKU-2', price=5000, stock=5)
        order = Order.objects.create(user=self.user, status=Order.STATUS_DELIVERED, total_amount=5000)
        OrderItem.objects.create(
            order=order, variant=other_variant, item_name=other_product.name,
            sku=other_variant.sku, quantity=1, price=5000,
        )
        response = self._post_review()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprado y recibido', response.data['detail'])


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ProductFunctioningStepTestCase(APITestCase):
    """
    [AGREGADO 2026-08-06] Cubre ProductFunctioningStep, mirror de
    technical_services.ServiceProcessStep -- bloque nuevo "Como funciona" pedido
    por el usuario para el catalogo enriquecido de Shop (sin equivalente previo).
    """

    def setUp(self):
        self.user = User.objects.create_user(email='functioning@example.com', password='testpass123')
        UserProfile.objects.create(user=self.user, user_type='CUSTOMER')
        category = Category.objects.create(name='Categoria Funcionamiento', slug='categoria-funcionamiento')
        self.product = Product.objects.create(
            vendor=self.user, category=category, name='Producto Funcionamiento', slug='producto-funcionamiento',
        )

    def test_create_update_delete_toggle_reorder(self):
        step1 = ProductFunctioningStepCommands.create(self.product, title='Paso 1', step_number=1)
        step2 = ProductFunctioningStepCommands.create(self.product, title='Paso 2', step_number=2)
        self.assertEqual(step1.product, self.product)
        self.assertTrue(step1.is_active)

        updated = ProductFunctioningStepCommands.update(step1, title='Paso 1 editado', estimated_time='10 min')
        self.assertEqual(updated.title, 'Paso 1 editado')
        self.assertEqual(updated.estimated_time, '10 min')

        toggled = ProductFunctioningStepCommands.toggle_active(step1)
        self.assertFalse(toggled.is_active)

        ProductFunctioningStepCommands.reorder(self.product.id, [str(step2.uuid), str(step1.uuid)])
        step1.refresh_from_db()
        step2.refresh_from_db()
        self.assertEqual(step2.position, 0)
        self.assertEqual(step1.position, 1)

        ProductFunctioningStepCommands.delete(step2)
        self.assertTrue(ProductFunctioningStep.objects.get(uuid=step2.uuid).is_deleted)

    def test_public_detail_exposes_only_active_functioning_steps(self):
        ProductFunctioningStepCommands.create(self.product, title='Paso visible', step_number=1)
        inactive = ProductFunctioningStepCommands.create(self.product, title='Paso oculto', step_number=2)
        ProductFunctioningStepCommands.toggle_active(inactive)

        response = self.client.get(f'/api/v1/shop/products/{self.product.uuid}/detail/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [s['title'] for s in response.data['functioning_steps']]
        self.assertIn('Paso visible', titles)
        self.assertNotIn('Paso oculto', titles)
