import uuid
from decimal import Decimal
from unittest.mock import patch
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import StockRecord, InventoryTransaction
from shop.models import ProductVariant, Product, Category, Tax
from technical_services.models import TechnicalService, ServiceVariant, ServiceCategory
from cart.models import Cart, CartItem
from cart.services import CartCommands, CartSelector
from cart.api.serializers import CartItemSerializer, CartSerializer

User = get_user_model()

class CartTestCase(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()

        # Create user
        self.user = User.objects.create_user(
            email="buyer@example.com",
            password="buyerpassword"
        )
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, user_type='CUSTOMER')
        self.client.force_authenticate(user=self.user)

        # Create category & product
        self.category = Category.objects.create(
            name="Electronics",
            slug="electronics"
        )
        self.product = Product.objects.create(
            vendor=self.user,
            category=self.category,
            name="Laptop",
            slug="laptop"
        )

        # Create product variant
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="LAPTOP-BASE",
            price=Decimal("1000.00"),
            stock=0
        )

        # Create StockRecord for variant
        self.content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=self.content_type,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=10
        )
        InventoryTransaction.objects.create(
            stock_record=self.stock_record,
            movement_type='ENTRY',
            quantity=10,
            balance_after=10
        )

        # Create active tax (IVA 19%)
        self.tax = Tax.objects.create(
            name="IVA 19%",
            tax_type=Tax.TaxType.PERCENTAGE,
            value=Decimal("19.00"),
            is_active=True
        )

        # Create service category & service
        self.service_category = ServiceCategory.objects.create(
            name="Installations",
            slug="installations"
        )
        self.service = TechnicalService.objects.create(
            vendor=self.user,
            category=self.service_category,
            name="Laptop Setup",
            slug="laptop-setup",
            description="Setup the laptop for the user"
        )

        # Create service variant
        self.service_variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SETUP-BASIC",
            pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal("50.00")
        )

        # Create StockRecord for service variant
        self.service_content_type = ContentType.objects.get_for_model(self.service_variant)
        self.service_stock_record = StockRecord.objects.create(
            content_type=self.service_content_type,
            object_id=self.service_variant.uuid,
            sku=self.service_variant.sku,
            stock=10
        )
        InventoryTransaction.objects.create(
            stock_record=self.service_stock_record,
            movement_type='ENTRY',
            quantity=10,
            balance_after=10
        )

        # Create cart
        self.cart = CartSelector.get_for_user(self.user)

    def test_add_item_success_and_stock_validation(self):
        # Adding product item to cart
        item = CartCommands.add_item(self.cart, variant=self.variant, quantity=2)
        self.assertEqual(item.quantity, 2)

        # Adding same product variant increases quantity
        item = CartCommands.add_item(self.cart, variant=self.variant, quantity=3)
        self.assertEqual(item.quantity, 5)

        # Adding beyond stock raises ValidationError
        with self.assertRaises(ValidationError):
            CartCommands.add_item(self.cart, variant=self.variant, quantity=6)

    def test_update_item_quantity(self):
        # Initial add
        CartCommands.add_item(self.cart, variant=self.variant, quantity=3)

        # Update quantity to 5
        item = CartCommands.update_item_quantity(self.cart, variant=self.variant, quantity=5)
        self.assertEqual(item.quantity, 5)

        # Try updating quantity beyond stock
        with self.assertRaises(ValidationError):
            CartCommands.update_item_quantity(self.cart, variant=self.variant, quantity=15)

        # Update quantity to 0 removes the item
        result = CartCommands.update_item_quantity(self.cart, variant=self.variant, quantity=0)
        self.assertIsNone(result)
        self.assertFalse(CartItem.objects.filter(cart=self.cart, variant=self.variant).exists())

    def test_serializers_pricing(self):
        # Add product and service
        item_prod = CartCommands.add_item(self.cart, variant=self.variant, quantity=2)
        item_serv = CartCommands.add_item(self.cart, service_variant=self.service_variant, quantity=1)

        # Verify unit price with tax (1000 + 19% = 1190)
        item_serializer = CartItemSerializer(item_prod)
        self.assertEqual(item_serializer.data['unit_price_with_tax'], '1190.00')
        self.assertEqual(item_serializer.data['final_price'], '2380.00')

        self.cart = CartSelector.get_for_user(self.user)
        cart_serializer = CartSerializer(self.cart)
        # total_cart_value: 2380.00 (product final price) + 50.00 (service) = 2430.00
        self.assertEqual(cart_serializer.data['total_cart_value'], '2430.00')

    def test_checkout_cart_services(self):
        # Empty cart checkout raises ValidationError
        with self.assertRaises(ValidationError):
            CartCommands.checkout_cart(self.user, self.cart)

        # Add items
        CartCommands.add_item(self.cart, variant=self.variant, quantity=2)
        CartCommands.add_item(self.cart, service_variant=self.service_variant, quantity=1)

        payload = CartCommands.checkout_cart(self.user, self.cart)
        self.assertEqual(payload['total_items'], 3)
        self.assertEqual(payload['subtotal'], '2050.00') # 1000 * 2 + 50 = 2050
        self.assertEqual(payload['total_amount'], '2430.00') # 1190 * 2 + 50 = 2430
        self.assertEqual(payload['total_tax'], '380.00') # (1190-1000)*2 = 380

    def test_cart_viewset_endpoints(self):
        # Add item via POST
        url_add = "/api/v1/cart/add_item/"
        data_add = {
            "variant_uuid": str(self.variant.uuid),
            "quantity": 2
        }
        response = self.client.post(url_add, data_add, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['quantity'], 2)

        # Update item via POST
        url_update = "/api/v1/cart/update_item/"
        data_update = {
            "variant_uuid": str(self.variant.uuid),
            "quantity": 4
        }
        response = self.client.post(url_update, data_update, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 4)

        # Checkout via POST
        url_checkout = "/api/v1/cart/checkout/"
        response = self.client.post(url_checkout, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_items'], 4)


class CartIntegrityTestCase(TransactionTestCase):
    """
    Cubre hallazgos de Fase 6 (auditoria de BD, 2026-07-03): "un carrito por usuario" y
    "un CartItem por (cart, variant)/(cart, service_variant)" solo se garantizaban por
    convencion de aplicacion (get_or_create() y get_or_create() dentro de select_for_update(),
    ambos vulnerables a condiciones de carrera si dos requests llegan simultaneamente antes
    de que exista la primera fila). Se agregaron UniqueConstraint/CheckConstraint en BD y se
    reescribio CartCommands.add_item() para fusionar cantidades en vez de fallar si la
    constraint bloquea un INSERT duplicado.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email='cart_integrity@example.com', password='testpass123')
        category = Category.objects.create(name='Cat Integridad', slug='cat-integridad-test')
        product = Product.objects.create(
            vendor=self.user, category=category, name='Producto Integridad', slug='producto-integridad-test',
        )
        self.variant = ProductVariant.objects.create(product=product, sku='INTEGRITY-SKU', price=Decimal('100.00'), stock=0)
        content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=content_type, object_id=self.variant.uuid, sku=self.variant.sku, stock=10,
        )
        InventoryTransaction.objects.create(
            stock_record=self.stock_record, movement_type='ENTRY', quantity=10, balance_after=10,
        )
        self.cart = CartSelector.get_for_user(self.user)

    def test_db_constraint_blocks_second_cart_for_same_user(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Cart.objects.create(user=self.user)

    def test_add_item_race_condition_merges_instead_of_erroring(self):
        """
        Simula la condicion de carrera de add_item(): la primera consulta de existing_item
        no encuentra ningun CartItem (como pasaria si dos requests llegan a la vez para un
        producto nuevo en el carrito), pero la constraint de BD bloquea el segundo INSERT
        porque otro proceso ya inserto la fila. add_item() debe recuperarse en el bloque
        except fusionando la cantidad, no propagar el IntegrityError.
        """
        CartItem.objects.create(cart=self.cart, variant=self.variant, quantity=2)

        call_count = {'n': 0}
        real_select_for_update = CartItem.objects.select_for_update

        def fake_select_for_update(*args, **kwargs):
            call_count['n'] += 1
            if call_count['n'] == 1:
                return CartItem.objects.filter(pk=None)  # simula que el racer no ve la fila
            return real_select_for_update(*args, **kwargs)

        with patch('cart.services.commands.CartItem.objects.select_for_update', side_effect=fake_select_for_update):
            item = CartCommands.add_item(self.cart, variant=self.variant, quantity=3)

        self.assertEqual(item.quantity, 5)
        self.assertEqual(CartItem.objects.filter(cart=self.cart, variant=self.variant).count(), 1)
