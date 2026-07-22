from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import UserProfile
from shop.models import Category, Product, ProductReview
from shop.api.serializers import ProductReviewSerializer

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
