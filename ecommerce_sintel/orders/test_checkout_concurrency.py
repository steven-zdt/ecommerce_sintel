"""Test de regresion de concurrencia para O-01 (auditoria enterprise).

create_from_cart() no tenia proteccion contra doble-submit: dos requests casi
simultaneos del mismo carrito (doble clic / reintento de red) creaban dos
ordenes. El fix usa el carrito como ancla de idempotencia (select_for_update
sobre sus items dentro del bloque atomico + re-chequeo de vacio).

Este test lanza dos hilos REALES (no mocks) que llaman create_from_cart a la
vez y verifica que solo se crea UNA orden y el otro hilo aborta con
ValidationError. Requiere PostgreSQL (SQLite no aplica bloqueo de fila real);
el conftest.py de la raiz garantiza que la suite corra contra Postgres.
"""
import threading
from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase

from users.models import User
from accounts.models import UserProfile
from orders.models import Order, ShippingAddress
from orders.services.commands import OrderCommands
from cart.models import Cart, CartItem
from shop.models import Category, Product, ProductVariant
from inventory.models import StockRecord
from inventory.services.commands import InventoryCommands
from inventory.services.dtos import StockAdjustmentDTO


class CheckoutConcurrencyTestCase(TransactionTestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email='concurrency_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer, first_name='Cliente', last_name='Concurrencia',
            user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Concurrencia',
            address_line_1='Calle 9 # 9-9', city='Bogota',
            phone_number='3000000009', is_default=True,
        )

        category = Category.objects.create(name='Categoria Conc', slug='categoria-conc-test')
        product = Product.objects.create(
            vendor=self.customer, category=category,
            name='Producto Conc Test', slug='producto-conc-test',
        )
        self.variant = ProductVariant.objects.create(
            product=product, sku='CONC-TEST-SKU-1', price=Decimal('40000.00'), stock=0,
        )
        content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=content_type, object_id=self.variant.uuid,
            sku=self.variant.sku, stock=0,
        )
        InventoryCommands.register_entry(StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid, quantity=10,
            reference='Stock inicial para test de concurrencia',
        ))

        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=2)

    @patch('notifications.services.commands.NotificationCommands.dispatch_notification')
    def test_concurrent_checkout_creates_single_order(self, _mock_dispatch):
        results = []
        errors = []
        barrier = threading.Barrier(2)

        def worker():
            # Sincroniza ambos hilos para que golpeen create_from_cart a la vez.
            barrier.wait()
            try:
                order = OrderCommands.create_from_cart(
                    user=self.customer, shipping_address=self.address,
                    payment_method='WOMPI',
                )
                results.append(order.uuid)
            except ValidationError:
                errors.append('validation')
            except Exception as exc:  # pragma: no cover - diagnostico
                errors.append(repr(exc))
            finally:
                connection.close()

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Exactamente UNA orden creada para este carrito, pase lo que pase.
        self.assertEqual(
            Order.objects.filter(user=self.customer).count(), 1,
            msg=f"Se crearon ordenes duplicadas. results={results} errors={errors}",
        )
        self.assertEqual(len(results), 1, msg=f"errors={errors}")
        self.assertEqual(len(errors), 1, msg=f"errors={errors}")
        self.assertEqual(errors[0], 'validation')


class PaymentInitializeIdempotencyTestCase(TransactionTestCase):
    """Test de regresion para F-02: dos initialize() del mismo pago (doble clic /
    reintento) no deben crear dos Transaction para la misma orden. El flujo
    Widget no llama a Wompi en initialize_transaction (solo crea la fila + firma
    de integridad), asi que se puede probar sin mocks de la pasarela."""

    def setUp(self):
        from payment.models import PaymentFeatureFlags
        PaymentFeatureFlags.get_active()  # asegura flags por defecto (widget on)

        self.customer = User.objects.create_user(
            email='initialize_idem@example.com', password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer, first_name='Cliente', last_name='Init',
            user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Init', address_line_1='Cra 1 # 1-1',
            city='Bogota', phone_number='3000000001', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address,
            status=Order.STATUS_PENDING_PAYMENT, payment_method='WOMPI',
            total_amount=Decimal('50000.00'), discount_amount=Decimal('0.00'),
        )

    def test_repeat_initialize_reuses_pending_transaction(self):
        from rest_framework.test import APIClient
        from payment.models import Transaction

        client = APIClient()
        client.force_authenticate(user=self.customer)
        url = '/api/v1/payment/payments/initialize/'

        r1 = client.post(url, {'order_uuid': str(self.order.uuid)}, format='json')
        self.assertEqual(r1.status_code, 200, msg=r1.content)
        r2 = client.post(url, {'order_uuid': str(self.order.uuid)}, format='json')
        self.assertEqual(r2.status_code, 200, msg=r2.content)

        # Una sola Transaction para la orden, y ambas respuestas apuntan a ella.
        self.assertEqual(Transaction.objects.filter(order=self.order).count(), 1)
        self.assertEqual(r1.data['transaction_uuid'], r2.data['transaction_uuid'])
