import threading
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import requests as requests_lib
from django.test import TestCase, TransactionTestCase, override_settings
from django.core.cache import cache
from django.db import connection, transaction, IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APITransactionTestCase

from users.models import User
from accounts.models import UserProfile
from orders.models import Order, OrderItem, ShippingAddress
from shop.models import ProductVariant, Product, Category
from inventory.models import StockRecord
from inventory.services.commands import InventoryCommands
from inventory.services.selectors import InventorySelector
from inventory.services.dtos import StockAdjustmentDTO

from payment.models import (
    Transaction, CodTransaction, NequiTransaction, TokenizedCard, TransactionEvent, PaymentFeatureFlags,
)
from payment.shared.commands import confirm_order_payment
from payment.online.services.commands import PaymentCommands, WompiCommands
from payment.online.wompi_client import (
    WompiApiClient, WompiApiError, WompiApiTransientError, WompiDuplicateReferenceError,
)
from security.models import SecurityEvent
from payment.cod.services.commands import CodCommands
from payment.nequi.services.commands import NequiCommands

from renting.models import RentingCategory, Equipment, EquipmentVariant, RentalRequest, RentalPeriod
from renting.services.commands import RentalRequestCommands


# Estos mocks evitan que el flujo real de confirmacion toque agenda de servicios,
# tickets de operaciones o el envio de notificaciones — el foco de esta suite es
# unicamente el efecto sobre inventario, que fue el punto que quedo roto por un
# refactor incompleto (ver payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md).
_PATCH_SERVICE_COMMANDS = patch('technical_services.services.commands.ServiceCommands.confirm_slot_on_payment')
_PATCH_OPERATION_COMMANDS = patch('operations.services.commands.OperationCommands.ensure_tickets_for_order')
_PATCH_NOTIFICATION_COMMANDS = patch('notifications.services.commands.NotificationCommands.dispatch_notification')


class PaymentInventoryIntegrationTestCase(TransactionTestCase):
    """
    Cubre la regresion detectada el 2026-07-03: _deduct_inventory_for_order() y
    _has_sufficient_stock() habian sido convertidas en no-ops, por lo que ningun
    pago (Wompi, Nequi, COD) descontaba stock real. Estos tests aseguran que el
    descuento vuelva a ocurrir y detectan si alguien lo desconecta de nuevo.
    """

    def setUp(self):
        cache.clear()

        self.customer = User.objects.create_user(
            email='payment_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='Pagos',
            user_type='CUSTOMER',
        )

        self.address = ShippingAddress.objects.create(
            user=self.customer,
            full_name='Cliente Pagos',
            address_line_1='Calle 1 # 1-1',
            city='Bogota',
            phone_number='3000000000',
            is_default=True,
        )

        category = Category.objects.create(name='Categoria Pagos', slug='categoria-pagos-test')
        product = Product.objects.create(
            vendor=self.customer,
            category=category,
            name='Producto Pagos Test',
            slug='producto-pagos-test',
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            sku='PAY-TEST-SKU-1',
            price=Decimal('50000.00'),
            stock=0,
        )

        content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=content_type,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=0,
        )
        InventoryCommands.register_entry(StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid,
            quantity=10,
            reference='Stock inicial para tests de pago',
        ))

    def _current_stock(self) -> int:
        return InventorySelector.get_current_stock(self.stock_record.id)

    def _create_order(self, quantity, status=Order.STATUS_PENDING_PAYMENT):
        order = Order.objects.create(
            user=self.customer,
            shipping_address=self.address,
            status=status,
            payment_method='WOMPI',
            total_amount=self.variant.price * quantity,
        )
        OrderItem.objects.create(
            order=order,
            variant=self.variant,
            item_name=self.variant.sku,
            sku=self.variant.sku,
            quantity=quantity,
            price=self.variant.price,
        )
        return order

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    def test_confirm_order_payment_deducts_stock(self, *_mocks):
        order = self._create_order(quantity=3)

        confirm_order_payment(order, reference='test-wompi-001')

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(self._current_stock(), 7)

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    def test_confirm_order_payment_is_idempotent(self, *_mocks):
        order = self._create_order(quantity=2)

        confirm_order_payment(order, reference='test-wompi-002')
        confirm_order_payment(order, reference='test-wompi-002-retry')

        self.assertEqual(self._current_stock(), 8)

    def test_payment_commands_confirm_payment_blocks_on_insufficient_stock(self):
        order = self._create_order(quantity=999)
        wompi_tx = Transaction.objects.create(
            order=order,
            amount_in_cents=int(order.total_amount * 100),
            status='APPROVED',
        )

        with patch('payment.online.services.commands.confirm_order_payment') as confirm_mock:
            with self.assertRaises(ValueError):
                PaymentCommands.confirm_payment(wompi_tx)
            confirm_mock.assert_not_called()

        wompi_tx.refresh_from_db()
        self.assertEqual(wompi_tx.status, 'ERROR')
        self.assertEqual(self._current_stock(), 10)

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    def test_cod_confirm_order_deducts_stock_immediately(self, *_mocks):
        order = self._create_order(quantity=4, status=Order.STATUS_CREATED)

        cod_tx = CodCommands.confirm_order(order)

        order.refresh_from_db()
        self.assertEqual(self._current_stock(), 6)
        self.assertEqual(cod_tx.status, CodTransaction.STATUS_CONFIRMED)
        self.assertEqual(order.status, Order.STATUS_PAID)

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.nequi.services.commands.NequiApiClient')
    def test_nequi_approved_deducts_stock(self, client_cls_mock, *_mocks):
        order = self._create_order(quantity=1)
        client_cls_mock.return_value.get_payment_status.return_value = NequiTransaction.STATUS_APPROVED

        nequi_tx = NequiTransaction.objects.create(
            order=order,
            phone_number='3000000000',
            message_id='msg-test-1',
            amount=order.total_amount,
            status=NequiTransaction.STATUS_PENDING,
        )

        NequiCommands.check_and_update_status(nequi_tx)

        order.refresh_from_db()
        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertEqual(self._current_stock(), 9)

    def test_webhook_duplicate_approved_does_not_reprocess_payment(self):
        order = self._create_order(quantity=2)
        wompi_tx = Transaction.objects.create(
            order=order,
            wompi_id='wompi-ext-id-1',
            amount_in_cents=int(order.total_amount * 100),
            status='APPROVED',
        )

        payload = {
            'data': {
                'transaction': {
                    'reference': str(wompi_tx.uuid),
                    'status': 'APPROVED',
                    'id': 'wompi-ext-id-1',
                }
            }
        }

        with patch('payment.online.services.commands.PaymentCommands.confirm_payment') as confirm_mock:
            WompiCommands.process_webhook_notification(payload)
            confirm_mock.assert_not_called()

        self.assertEqual(self._current_stock(), 10)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class WompiConfirmationSyncTestCase(APITransactionTestCase):
    """
    Cubre `_sync_wompi_status()`: cuando el frontend consulta `confirmation/` y la
    Transaction sigue PENDING (el usuario volvio del widget antes de que llegara el
    webhook), el endpoint debe consultar la API de Wompi y, si ya aprobo, disparar
    PaymentCommands.confirm_payment() end-to-end (orden pagada + stock descontado).
    No estaba cubierto por ningun test antes de esta sesion.
    """

    def setUp(self):
        cache.clear()

        self.customer = User.objects.create_user(
            email='wompi_sync_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='Sync',
            user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer,
            full_name='Cliente Sync',
            address_line_1='Calle 2 # 2-2',
            city='Bogota',
            phone_number='3000000001',
            is_default=True,
        )
        category = Category.objects.create(name='Categoria Sync', slug='categoria-sync-test')
        product = Product.objects.create(
            vendor=self.customer,
            category=category,
            name='Producto Sync Test',
            slug='producto-sync-test',
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            sku='SYNC-TEST-SKU-1',
            price=Decimal('30000.00'),
            stock=0,
        )
        content_type = ContentType.objects.get_for_model(self.variant)
        self.stock_record = StockRecord.objects.create(
            content_type=content_type,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=0,
        )
        InventoryCommands.register_entry(StockAdjustmentDTO(
            stock_record_uuid=self.stock_record.uuid,
            quantity=5,
            reference='Stock inicial para test de sync',
        ))

        self.order = Order.objects.create(
            user=self.customer,
            shipping_address=self.address,
            status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI',
            total_amount=self.variant.price * 2,
        )
        OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            item_name=self.variant.sku,
            sku=self.variant.sku,
            quantity=2,
            price=self.variant.price,
        )
        self.wompi_tx = Transaction.objects.create(
            order=self.order,
            wompi_id='wompi-ext-sync-1',
            amount_in_cents=int(self.order.total_amount * 100),
            status='PENDING',
        )
        self.url = f'/api/v1/payment/payments/confirmation/?tx={self.wompi_tx.uuid}'

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @patch('payment.online.api.views.http_requests.get')
    def test_confirmation_endpoint_syncs_approved_and_deducts_stock(self, get_mock):
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {
            'data': {'status': 'APPROVED', 'payment_method_type': 'CARD'}
        }

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.wompi_tx.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.wompi_tx.status, 'APPROVED')
        self.assertEqual(self.order.status, Order.STATUS_PAID)
        self.assertEqual(InventorySelector.get_current_stock(self.stock_record.id), 3)
        self.assertEqual(response.data['payment']['status'], 'APPROVED')

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @patch('payment.online.api.views.http_requests.get')
    def test_confirmation_endpoint_leaves_pending_on_wompi_api_error(self, get_mock):
        get_mock.return_value.status_code = 500

        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.wompi_tx.refresh_from_db()
        self.assertEqual(self.wompi_tx.status, 'PENDING')
        self.assertEqual(response.data['payment']['status'], 'PENDING')
        self.assertEqual(InventorySelector.get_current_stock(self.stock_record.id), 5)

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @patch('payment.online.api.views.http_requests.get')
    def test_confirmation_endpoint_syncs_via_id_hint_before_webhook_arrives(self, get_mock):
        """
        Cubre la causa raiz real del bug reportado (2026-07-07): justo despues de que
        el widget de Wompi cierra, el webhook (unico lugar que escribia wompi_id) puede
        no haber llegado todavia, asi que la Transaction sigue con wompi_id=None. Antes,
        _sync_wompi_status() se abortaba de inmediato en ese caso y la pantalla se
        quedaba en PENDING para siempre. Ahora el frontend manda `?id=` (el ID de Wompi,
        conocido de inmediato via el callback del widget) como hint, y el backend debe
        usarlo para consultar Wompi igual, y ademas rellenar wompi_id en BD.
        """
        wompi_tx_no_id = Transaction.objects.create(
            order=self.order,
            amount_in_cents=int(self.order.total_amount * 100),
            status='PENDING',
        )
        self.assertIsNone(wompi_tx_no_id.wompi_id)

        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {
            'data': {'status': 'APPROVED', 'payment_method_type': 'CARD'}
        }

        self.client.force_authenticate(user=self.customer)
        url = f'/api/v1/payment/payments/confirmation/?tx={wompi_tx_no_id.uuid}&id=wompi-hint-id-1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        wompi_tx_no_id.refresh_from_db()
        self.assertEqual(wompi_tx_no_id.wompi_id, 'wompi-hint-id-1')
        self.assertEqual(wompi_tx_no_id.status, 'APPROVED')
        self.assertEqual(response.data['payment']['status'], 'APPROVED')
        get_mock.assert_called_once()
        self.assertIn('wompi-hint-id-1', get_mock.call_args[0][0])


@override_settings(ROOT_URLCONF='ecommerce.urls')
class PaymentInitializeAcceptsPendingPaymentStatusTestCase(APITransactionTestCase):
    """
    Cubre el bug detectado el 2026-07-03: OrderCommands.create_from_cart() crea
    ordenes con Order.STATUS_PENDING_PAYMENT ('PENDING_PAYMENT'), pero
    initialize() de Wompi y de Nequi comparaban contra el string legacy
    'pending', rechazando siempre con 400 la orden recien creada. Esto rompia
    el checkout completo para ambos metodos de pago online.
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='checkout_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='Checkout',
            user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer,
            full_name='Cliente Checkout',
            address_line_1='Calle 3 # 3-3',
            city='Bogota',
            phone_number='3000000002',
            is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer,
            shipping_address=self.address,
            status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI',
            total_amount=Decimal('100000.00'),
        )

    def test_wompi_initialize_accepts_order_created_by_create_from_cart(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Transaction.objects.filter(order=self.order).exists())

    @patch('payment.nequi.services.commands.NequiApiClient')
    def test_nequi_initialize_accepts_order_created_by_create_from_cart(self, client_cls_mock):
        client_cls_mock.return_value.request_push_payment.return_value = 'msg-checkout-1'

        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/v1/payment/nequi/initialize/',
            {'order_uuid': str(self.order.uuid), 'phone_number': '3000000002'},
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(NequiTransaction.objects.filter(order=self.order).exists())


@override_settings(ROOT_URLCONF='ecommerce.urls')
class TokenizedCardDefaultIntegrityTestCase(APITransactionTestCase):
    """
    Cubre un hallazgo de Fase 6 (auditoria de BD, 2026-07-03): "una sola tarjeta
    is_default=True por usuario" solo se garantizaba a nivel de aplicacion (dos
    UPDATE/SAVE separados y sin bloqueo), y `destroy()` promovia una tarjeta nueva
    como default sin limpiar el flag de la tarjeta recien eliminada -- dejando dos
    filas con is_default=True para el mismo usuario. Se agrego
    UniqueConstraint(user, condition=is_default & ~is_deleted) en BD y se corrigio
    destroy()/create()/set_default() para manejar la condicion de carrera con un
    409 limpio en vez de un IntegrityError sin capturar.
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='cards_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='Tarjetas',
            user_type='CUSTOMER',
        )
        self.client.force_authenticate(user=self.customer)

    def _create_card(self, token_id, masked_number='4242'):
        return self.client.post('/api/v1/payment/cards/', {
            'token_id': token_id,
            'masked_number': masked_number,
            'brand': 'VISA',
            'exp_month': '12',
            'exp_year': '2030',
            'cardholder_name': 'Cliente Tarjetas',
        })

    def test_first_card_is_default_second_is_not(self):
        r1 = self._create_card('tok_1')
        r2 = self._create_card('tok_2')
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertTrue(r1.data['is_default'])
        self.assertFalse(r2.data['is_default'])

    def test_set_default_clears_previous_default(self):
        r1 = self._create_card('tok_1')
        r2 = self._create_card('tok_2')
        card2_uuid = r2.data['uuid']

        response = self.client.post(f'/api/v1/payment/cards/{card2_uuid}/set-default/')
        self.assertEqual(response.status_code, 200)

        defaults = TokenizedCard.objects.filter(user=self.customer, is_default=True, is_deleted=False)
        self.assertEqual(defaults.count(), 1)
        self.assertEqual(str(defaults.first().uuid), card2_uuid)

    def test_deleting_default_card_promotes_next_without_leaving_duplicate(self):
        r1 = self._create_card('tok_1')
        self._create_card('tok_2')
        card1_uuid = r1.data['uuid']

        response = self.client.delete(f'/api/v1/payment/cards/{card1_uuid}/')
        self.assertEqual(response.status_code, 204)

        deleted_card = TokenizedCard.objects.get(uuid=card1_uuid)
        self.assertFalse(deleted_card.is_default)

        defaults = TokenizedCard.objects.filter(user=self.customer, is_default=True, is_deleted=False)
        self.assertEqual(defaults.count(), 1)

    def test_db_constraint_blocks_second_default_card_for_same_user(self):
        """
        Reproduce a nivel de BD lo que una condicion de carrera de aplicacion
        dejaria pasar: dos filas is_default=True para el mismo usuario. La
        UniqueConstraint(user, condition=is_default & ~is_deleted) debe bloquear
        el segundo INSERT con IntegrityError, que es lo que create()/set_default()
        en el ViewSet capturan para responder 409 en vez de dejar un 500.
        """
        self._create_card('tok_1')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TokenizedCard.objects.create(
                    user=self.customer,
                    token_id='tok_race',
                    masked_number='0000',
                    brand='VISA',
                    exp_month='01',
                    exp_year='2031',
                    is_default=True,
                )
        self.assertEqual(
            TokenizedCard.objects.filter(user=self.customer, is_default=True, is_deleted=False).count(),
            1,
        )


class RentalPaymentFailureReleaseTestCase(TransactionTestCase):
    """
    Cubre el bug documentado en renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md
    (Plan Maestro Fase 1, 2026-07-07): process_webhook_notification() llamaba
    ServiceCommands.release_slot_on_failure(wompi_tx.order) incondicionalmente; para
    una Transaction de renta, wompi_tx.order es None (CheckConstraint garantiza
    exactamente uno de order/rental_request), asi que la liberacion fallaba
    silenciosamente dentro de un try/except. Un pago de renta rechazado/anulado
    ahora debe cancelar la RentalRequest via RentalRequestCommands.release_on_payment_failure().
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='rental_payment_customer@example.com', password='testpassword123',
        )
        category = RentingCategory.objects.create(name='Cat Payment Fail', slug='cat-payment-fail-test')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Equipo Payment Fail', slug='equipo-payment-fail-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='PAY-FAIL-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )
        self.rental_request = RentalRequestCommands.create_request(self.customer, {
            'equipment_variant': self.variant,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=13),
            'quantity': 1,
            'rental_mode': 'days',
            'contact_full_name': 'Cliente Renta',
            'contact_email': self.customer.email,
            'terms_accepted': True,
        })

    @_PATCH_NOTIFICATION_COMMANDS
    def test_wompi_declined_cancels_rental_request(self, *_mocks):
        wompi_tx = Transaction.objects.create(
            rental_request=self.rental_request,
            amount_in_cents=int(self.rental_request.grand_total * 100),
            status='PENDING',
        )
        payload = {
            'data': {'transaction': {
                'reference': str(wompi_tx.uuid), 'status': 'DECLINED', 'id': 'wompi-rental-decl-1',
            }}
        }

        WompiCommands.process_webhook_notification(payload)

        self.rental_request.refresh_from_db()
        self.assertEqual(self.rental_request.status, RentalRequest.STATUS_CANCELLED)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=self.rental_request).count(), 0)

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    def test_wompi_declined_order_path_is_unaffected(self, *_mocks):
        address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Renta', address_line_1='Calle 1 # 1-1',
            city='Bogota', phone_number='3000000000', is_default=True,
        )
        order = Order.objects.create(
            user=self.customer, shipping_address=address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('50000.00'),
        )
        wompi_tx = Transaction.objects.create(
            order=order, amount_in_cents=5000000, status='PENDING',
        )
        payload = {
            'data': {'transaction': {
                'reference': str(wompi_tx.uuid), 'status': 'DECLINED', 'id': 'wompi-order-decl-1',
            }}
        }

        with patch('technical_services.services.commands.ServiceCommands.release_slot_on_failure') as release_mock:
            WompiCommands.process_webhook_notification(payload)
            release_mock.assert_called_once_with(order)

    @_PATCH_NOTIFICATION_COMMANDS
    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @patch('payment.online.api.views.http_requests.get')
    def test_sync_wompi_status_declined_cancels_rental_request(self, get_mock, *_mocks):
        """
        Cubre el gap real cerrado 2026-07-14 (roadmap "Reconciliacion de pagos"):
        _sync_wompi_status() -- el fallback de reconciliacion usado por el polling
        de PaymentResultView y por payment.tasks.reconcile_pending_wompi_transactions,
        NO por el webhook -- solo manejaba APPROVED. Si el webhook se perdia/
        retrasaba y la reconciliacion descubria un DECLINED, la Transaction se
        actualizaba pero la RentalRequest quedaba huerfana en pending_payment.
        """
        from payment.online.api.views import _sync_wompi_status

        wompi_tx = Transaction.objects.create(
            rental_request=self.rental_request, wompi_id='wompi-rental-sync-decl-1',
            amount_in_cents=int(self.rental_request.grand_total * 100), status='PENDING',
        )
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {'data': {'status': 'DECLINED', 'payment_method_type': 'CARD'}}

        _sync_wompi_status(wompi_tx)

        wompi_tx.refresh_from_db()
        self.rental_request.refresh_from_db()
        self.assertEqual(wompi_tx.status, 'DECLINED')
        self.assertEqual(self.rental_request.status, RentalRequest.STATUS_CANCELLED)

    @_PATCH_NOTIFICATION_COMMANDS
    @patch('payment.nequi.services.commands.NequiApiClient')
    def test_nequi_rejected_cancels_rental_request(self, client_cls_mock, *_mocks):
        client_cls_mock.return_value.get_payment_status.return_value = NequiTransaction.STATUS_REJECTED
        nequi_tx = NequiTransaction.objects.create(
            rental_request=self.rental_request, phone_number='3000000000',
            message_id='msg-rental-rejected-1', amount=self.rental_request.grand_total,
            status=NequiTransaction.STATUS_PENDING,
        )

        NequiCommands.check_and_update_status(nequi_tx)

        self.rental_request.refresh_from_db()
        self.assertEqual(self.rental_request.status, RentalRequest.STATUS_CANCELLED)


class WompiWebhookConcurrencyTestCase(TransactionTestCase):
    """
    Cubre el endurecimiento de Fase 10 (2026-07-07): process_webhook_notification()
    ahora usa select_for_update() para serializar entregas concurrentes del mismo
    webhook (Wompi reintenta la entrega si no recibe 200 a tiempo). Sin el lock, dos
    entregas podian leer PENDING antes de que cualquiera escribiera, evadiendo el
    guard de idempotencia (que solo compara contra el status ya guardado en BD) y
    disparando PaymentCommands.confirm_payment() dos veces para el mismo pago.
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            email='wompi_webhook_concurrency@example.com', password='testpass123',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Concurrencia', address_line_1='Calle 1 # 1-1',
            city='Bogota', phone_number='3000000009', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('50000.00'),
        )
        self.wompi_tx = Transaction.objects.create(
            order=self.order, amount_in_cents=5000000, status='PENDING',
        )

    def test_concurrent_webhook_deliveries_confirm_payment_only_once(self):
        payload = {
            'data': {'transaction': {
                'reference': str(self.wompi_tx.uuid), 'status': 'APPROVED', 'id': 'wompi-concurrency-1',
            }}
        }
        calls = []
        lock = threading.Lock()

        def counting_confirm(tx):
            with lock:
                calls.append(tx.pk)

        def worker():
            try:
                WompiCommands.process_webhook_notification(payload)
            finally:
                connection.close()

        with patch('payment.online.services.commands.PaymentCommands.confirm_payment', side_effect=counting_confirm):
            t1 = threading.Thread(target=worker)
            t2 = threading.Thread(target=worker)
            t1.start()
            t2.start()
            t1.join(timeout=15)
            t2.join(timeout=15)

        self.wompi_tx.refresh_from_db()
        self.assertEqual(self.wompi_tx.status, 'APPROVED')
        self.assertEqual(self.wompi_tx.wompi_id, 'wompi-concurrency-1')
        self.assertEqual(len(calls), 1)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class WompiReconcilePendingTransactionsTaskTestCase(APITransactionTestCase):
    """
    Cubre la reconciliacion periodica de Fase 12 (2026-07-07): payment.tasks.
    reconcile_pending_wompi_transactions() debe re-consultar Wompi para las
    Transaction PENDING que ya tienen wompi_id (backfilleado por el webhook o por
    _sync_wompi_status) y llevan mas de 1 minuto pendientes -- cubre al usuario que
    cierra la pestana antes de que llegue el webhook o antes de volver a
    /payment/result.
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='wompi_reconcile@example.com', password='testpass123',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Reconcile', address_line_1='Calle 1 # 1-1',
            city='Bogota', phone_number='3000000008', is_default=True,
        )

        def _make_order():
            return Order.objects.create(
                user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
                payment_method='WOMPI', total_amount=Decimal('40000.00'),
            )

        stale_time = timezone.now() - timedelta(minutes=5)

        # Elegible: PENDING, con wompi_id, vieja.
        self.eligible_tx = Transaction.objects.create(
            order=_make_order(), wompi_id='wompi-stale-1', amount_in_cents=4000000, status='PENDING',
        )
        Transaction.objects.filter(pk=self.eligible_tx.pk).update(created_at=stale_time)

        # No elegible: sin wompi_id todavia (nada que consultar).
        self.no_wompi_id_tx = Transaction.objects.create(
            order=_make_order(), amount_in_cents=4000000, status='PENDING',
        )
        Transaction.objects.filter(pk=self.no_wompi_id_tx.pk).update(created_at=stale_time)

        # No elegible: demasiado reciente (todavia puede resolverse por el webhook normal).
        self.recent_tx = Transaction.objects.create(
            order=_make_order(), wompi_id='wompi-recent-1', amount_in_cents=4000000, status='PENDING',
        )

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.online.api.views.http_requests.get')
    def test_reconcile_only_touches_stale_transactions_with_known_wompi_id(self, get_mock, *_mocks):
        from payment.tasks import reconcile_pending_wompi_transactions

        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {
            'data': {'status': 'APPROVED', 'payment_method_type': 'CARD'}
        }

        reconcile_pending_wompi_transactions()

        self.eligible_tx.refresh_from_db()
        self.no_wompi_id_tx.refresh_from_db()
        self.recent_tx.refresh_from_db()

        self.assertEqual(self.eligible_tx.status, 'APPROVED')
        self.assertEqual(self.no_wompi_id_tx.status, 'PENDING')
        self.assertEqual(self.recent_tx.status, 'PENDING')
        get_mock.assert_called_once()
        self.assertIn('wompi-stale-1', get_mock.call_args[0][0])


@override_settings(ROOT_URLCONF='ecommerce.urls', WOMPI_PRIVATE_KEY='prv_test_dummy')
class WompiReconciliationObservabilityTestCase(APITransactionTestCase):
    """
    Cubre la Fase 6 (ADR-001) de reconciliacion mejorada: fallos reales de
    _sync_wompi_status ahora dejan TransactionEvent (antes solo un log de
    texto que se perdia), y las transacciones abandonadas sin wompi_id
    (imposibles de reconciliar por falta de endpoint de busqueda en Wompi)
    quedan marcadas para revision en vez de invisibles para siempre.
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='wompi_reconcile_obs@example.com', password='testpass123',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente ReconcileObs', address_line_1='Calle 7 # 7-7',
            city='Bogota', phone_number='3000000009', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('40000.00'),
        )

    @patch('payment.online.api.views.http_requests.get')
    def test_sync_status_non_200_writes_unprocessed_event(self, get_mock):
        from payment.online.api.views import _sync_wompi_status

        tx = Transaction.objects.create(
            order=self.order, wompi_id='wompi-fail-1', amount_in_cents=4000000,
            status='PENDING', correlation_id='corr-sync-fail-1',
        )
        get_mock.return_value.status_code = 500
        get_mock.return_value.json.return_value = {}

        _sync_wompi_status(tx)

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_API_SYNC)
        self.assertFalse(event.processed)
        self.assertEqual(event.previous_status, 'PENDING')
        self.assertIn('500', event.error_detail)
        self.assertEqual(event.correlation_id, 'corr-sync-fail-1')

    @patch('payment.online.api.views.http_requests.get')
    def test_sync_status_exception_writes_unprocessed_event(self, get_mock):
        from payment.online.api.views import _sync_wompi_status

        tx = Transaction.objects.create(
            order=self.order, wompi_id='wompi-fail-2', amount_in_cents=4000000,
            status='PENDING', correlation_id='corr-sync-fail-2',
        )
        get_mock.side_effect = ConnectionError('timeout de red')

        _sync_wompi_status(tx)

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertFalse(event.processed)
        self.assertIn('timeout de red', event.error_detail)

    def test_reconcile_flags_abandoned_transaction_without_wompi_id(self):
        from payment.tasks import reconcile_pending_wompi_transactions

        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING', correlation_id='corr-abandoned-1',
        )
        Transaction.objects.filter(pk=tx.pk).update(created_at=timezone.now() - timedelta(minutes=45))

        reconcile_pending_wompi_transactions()

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_API_SYNC)
        self.assertFalse(event.processed)
        self.assertIn('abandonada', event.error_detail.lower())
        self.assertEqual(event.correlation_id, 'corr-abandoned-1')
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'PENDING')  # nunca se inventa un estado nuevo

    def test_reconcile_abandoned_transaction_logs_security_event(self):
        """ADR-001 Fase 8: alerta operativa via SecurityEvent, visible en /panel/seguridad."""
        from payment.tasks import reconcile_pending_wompi_transactions

        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING', correlation_id='corr-alert-1',
        )
        Transaction.objects.filter(pk=tx.pk).update(created_at=timezone.now() - timedelta(minutes=45))

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            reconcile_pending_wompi_transactions()

        abandoned_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_TRANSACTION_ABANDONED
        ]
        self.assertEqual(len(abandoned_calls), 1)
        self.assertEqual(abandoned_calls[0].kwargs['severity'], SecurityEvent.SEVERITY_WARNING)
        self.assertEqual(abandoned_calls[0].kwargs['metadata']['transaction_uuid'], str(tx.uuid))
        self.assertEqual(abandoned_calls[0].kwargs['metadata']['correlation_id'], 'corr-alert-1')

    def test_reconcile_does_not_reflag_already_flagged_transaction(self):
        from payment.tasks import reconcile_pending_wompi_transactions

        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING',
        )
        Transaction.objects.filter(pk=tx.pk).update(created_at=timezone.now() - timedelta(minutes=45))

        reconcile_pending_wompi_transactions()
        reconcile_pending_wompi_transactions()  # segunda corrida, mismo estado

        self.assertEqual(TransactionEvent.objects.filter(transaction=tx).count(), 1)

    def test_reconcile_does_not_flag_recent_transaction_without_wompi_id(self):
        from payment.tasks import reconcile_pending_wompi_transactions

        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING',
        )  # created_at = ahora, muy reciente

        reconcile_pending_wompi_transactions()

        self.assertFalse(TransactionEvent.objects.filter(transaction=tx).exists())


def _mock_response(status_code=200, json_data=None, text=''):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = text
    return resp


_ACCEPTANCE_TOKENS_RESPONSE = {
    'data': {
        'presigned_acceptance': {'acceptance_token': 'jwt-acceptance-token'},
        'presigned_personal_data_auth': {'acceptance_token': 'jwt-personal-auth-token'},
    }
}


@override_settings(
    WOMPI_ENVIRONMENT='test', WOMPI_PUBLIC_KEY='pub_test_dummy', WOMPI_PRIVATE_KEY='prv_test_dummy',
)
class WompiApiClientTestCase(TestCase):
    """
    Cubre payment/online/wompi_client.py (Fase 2 de la migracion a integracion API
    propia, ver payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md). Cierra el hueco
    de cobertura senalado en la Fase 0 de esa auditoria: hasta ahora ningun cliente
    HTTP de payment/ (ni siquiera NequiApiClient) tenia tests aislados propios, solo
    se mockeaban como caja negra dentro de tests de integracion mas grandes.
    """

    def setUp(self):
        self.client_ = WompiApiClient()

    @patch('payment.online.wompi_client.requests.request')
    def test_get_acceptance_tokens_parses_both_tokens(self, request_mock):
        request_mock.return_value = _mock_response(200, _ACCEPTANCE_TOKENS_RESPONSE)

        tokens = self.client_.get_acceptance_tokens()

        self.assertEqual(tokens['acceptance_token'], 'jwt-acceptance-token')
        self.assertEqual(tokens['accept_personal_auth'], 'jwt-personal-auth-token')
        called_url = request_mock.call_args[0][1]
        self.assertIn('/merchants/pub_test_dummy', called_url)
        # GET /merchants/{public_key} no lleva Authorization Bearer (llave publica va en la URL).
        self.assertNotIn('headers', request_mock.call_args.kwargs)

    @patch('payment.online.wompi_client.requests.request')
    def test_get_acceptance_tokens_missing_token_raises(self, request_mock):
        request_mock.return_value = _mock_response(200, {'data': {'presigned_acceptance': {}}})

        with self.assertRaises(WompiApiError):
            self.client_.get_acceptance_tokens()

    @patch('payment.online.wompi_client.requests.request')
    def test_create_payment_source_sends_acceptance_tokens_and_returns_id(self, request_mock):
        request_mock.side_effect = [
            _mock_response(200, _ACCEPTANCE_TOKENS_RESPONSE),
            _mock_response(201, {'data': {'id': 3891, 'status': 'AVAILABLE'}}),
        ]

        data = self.client_.create_payment_source(card_token='tok_test_card', customer_email='cliente@sintel.co')

        self.assertEqual(data['id'], 3891)
        self.assertEqual(data['status'], 'AVAILABLE')
        second_call = request_mock.call_args_list[1]
        payload = second_call.kwargs['json']
        self.assertEqual(payload['type'], 'CARD')
        self.assertEqual(payload['token'], 'tok_test_card')
        self.assertEqual(payload['acceptance_token'], 'jwt-acceptance-token')
        self.assertEqual(payload['accept_personal_auth'], 'jwt-personal-auth-token')
        # POST /payment_sources SI lleva Authorization Bearer (llave privada).
        self.assertEqual(second_call.kwargs['headers']['Authorization'], 'Bearer prv_test_dummy')

    @patch('payment.online.wompi_client.requests.request')
    def test_create_transaction_requires_exactly_one_source(self, request_mock):
        with self.assertRaises(ValueError):
            self.client_.create_transaction(
                amount_in_cents=1000000, currency='COP', reference='ref-1',
                customer_email='c@sintel.co', signature='sig',
            )
        with self.assertRaises(ValueError):
            self.client_.create_transaction(
                amount_in_cents=1000000, currency='COP', reference='ref-1',
                customer_email='c@sintel.co', signature='sig',
                payment_source_id=1, card_token='tok_x',
            )
        request_mock.assert_not_called()

    @patch('payment.online.wompi_client.requests.request')
    def test_create_transaction_with_payment_source_id(self, request_mock):
        request_mock.side_effect = [
            _mock_response(200, _ACCEPTANCE_TOKENS_RESPONSE),
            _mock_response(201, {'data': {'id': 'wompi-tx-1', 'status': 'PENDING'}}),
        ]

        data = self.client_.create_transaction(
            amount_in_cents=5000000, currency='COP', reference='ref-source-1',
            customer_email='c@sintel.co', signature='sig-abc', payment_source_id=3891,
        )

        self.assertEqual(data['id'], 'wompi-tx-1')
        payload = request_mock.call_args_list[1].kwargs['json']
        self.assertEqual(payload['payment_source_id'], 3891)
        self.assertEqual(payload['payment_method'], {'installments': 1})
        self.assertNotIn('token', payload['payment_method'])

    @patch('payment.online.wompi_client.requests.request')
    def test_create_transaction_with_card_token(self, request_mock):
        request_mock.side_effect = [
            _mock_response(200, _ACCEPTANCE_TOKENS_RESPONSE),
            _mock_response(201, {'data': {'id': 'wompi-tx-2', 'status': 'PENDING'}}),
        ]

        self.client_.create_transaction(
            amount_in_cents=5000000, currency='COP', reference='ref-token-1',
            customer_email='c@sintel.co', signature='sig-abc', card_token='tok_new_card',
        )

        payload = request_mock.call_args_list[1].kwargs['json']
        self.assertEqual(payload['payment_method'], {'type': 'CARD', 'token': 'tok_new_card', 'installments': 1})

    @patch('payment.online.wompi_client.requests.request')
    def test_create_transaction_duplicate_reference_raises_specific_exception(self, request_mock):
        request_mock.side_effect = [
            _mock_response(200, _ACCEPTANCE_TOKENS_RESPONSE),
            _mock_response(422, text='{"error": {"messages": {"reference": ["must be unique, duplicate found"]}}}'),
        ]

        with self.assertRaises(WompiDuplicateReferenceError):
            self.client_.create_transaction(
                amount_in_cents=5000000, currency='COP', reference='ref-dup-1',
                customer_email='c@sintel.co', signature='sig-abc', payment_source_id=1,
            )

    @patch('payment.online.wompi_client.requests.request')
    def test_5xx_raises_transient_error(self, request_mock):
        request_mock.return_value = _mock_response(503, text='service unavailable')

        with self.assertRaises(WompiApiTransientError):
            self.client_.get_transaction('wompi-tx-x')

    @patch('payment.online.wompi_client.requests.request')
    def test_network_exception_raises_transient_error(self, request_mock):
        request_mock.side_effect = requests_lib.ConnectionError('boom')

        with self.assertRaises(WompiApiTransientError):
            self.client_.get_transaction('wompi-tx-x')

    @patch('payment.online.wompi_client.requests.request')
    def test_get_transaction_uses_private_key_and_returns_data(self, request_mock):
        request_mock.return_value = _mock_response(200, {'data': {'id': 'wompi-tx-9', 'status': 'APPROVED'}})

        data = self.client_.get_transaction('wompi-tx-9')

        self.assertEqual(data['status'], 'APPROVED')
        self.assertIn('/transactions/wompi-tx-9', request_mock.call_args[0][1])
        self.assertEqual(request_mock.call_args.kwargs['headers']['Authorization'], 'Bearer prv_test_dummy')

    @patch('payment.online.wompi_client.requests.request')
    def test_4xx_non_duplicate_raises_generic_api_error(self, request_mock):
        request_mock.return_value = _mock_response(400, text='{"error": {"reason": "INVALID_AMOUNT"}}')

        with self.assertRaises(WompiApiError):
            self.client_.get_transaction('wompi-tx-x')


@override_settings(ROOT_URLCONF='ecommerce.urls')
class WompiSyncTransactionCreationTestCase(APITransactionTestCase):
    """
    Cubre la conexion de WompiApiClient a initialize/ (ADR-001 Sec.4, continuacion
    de Fase 2). El checkout en vivo de hoy NUNCA envia card_token/payment_source_id
    (el frontend todavia abre el Widget completo sin tokenizar antes, eso es
    Fase 3, pendiente) -- el primer test de esta clase es la regresion mas
    importante: confirmar que ese camino, el unico real hoy, sigue exactamente
    igual. El resto cubre la rama nueva (hoy inalcanzable en produccion, lista
    para cuando el frontend empiece a mandar estos campos).
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='wompi_sync_checkout@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer, first_name='Cliente', last_name='SyncTx', user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente SyncTx', address_line_1='Calle 4 # 4-4',
            city='Bogota', phone_number='3000000003', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('50000.00'),
        )

    def test_initialize_without_new_params_keeps_legacy_behavior(self):
        """El unico camino real del checkout en vivo hoy: sin cambios de comportamiento."""
        self.client.force_authenticate(user=self.customer)
        with patch('payment.online.services.commands.WompiApiClient') as client_cls_mock:
            response = self.client.post(
                '/api/v1/payment/payments/initialize/', {'order_uuid': str(self.order.uuid)},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['wompi_id'], None)
        self.assertEqual(response.data['status'], 'PENDING')
        client_cls_mock.assert_not_called()

    @patch('payment.online.services.commands.WompiApiClient')
    def test_initialize_with_card_token_creates_transaction_synchronously(self, client_cls_mock):
        client_cls_mock.return_value.create_transaction.return_value = {
            'id': 'wompi-live-1', 'status': 'PENDING', 'payment_method_type': 'CARD',
        }
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_test_12345'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['wompi_id'], 'wompi-live-1')
        tx = Transaction.objects.get(order=self.order)
        self.assertEqual(tx.wompi_id, 'wompi-live-1')
        self.assertEqual(tx.status, 'PENDING')
        self.assertEqual(tx.payment_method_type, 'CARD')
        call_kwargs = client_cls_mock.return_value.create_transaction.call_args.kwargs
        self.assertEqual(call_kwargs['card_token'], 'tok_test_12345')
        self.assertIsNone(call_kwargs['payment_source_id'])
        self.assertEqual(call_kwargs['reference'], str(tx.uuid))
        self.assertEqual(call_kwargs['customer_email'], self.customer.email)

    @patch('payment.online.services.commands.WompiApiClient')
    def test_initialize_with_payment_source_id_creates_transaction_synchronously(self, client_cls_mock):
        client_cls_mock.return_value.create_transaction.return_value = {
            'id': 'wompi-live-2', 'status': 'PENDING', 'payment_method_type': 'CARD',
        }
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'payment_source_id': 3891},
        )

        self.assertEqual(response.status_code, 200)
        call_kwargs = client_cls_mock.return_value.create_transaction.call_args.kwargs
        self.assertEqual(call_kwargs['payment_source_id'], 3891)
        self.assertIsNone(call_kwargs['card_token'])

    def test_initialize_with_both_card_token_and_payment_source_id_returns_400(self):
        self.client.force_authenticate(user=self.customer)
        with patch('payment.online.services.commands.WompiApiClient') as client_cls_mock:
            response = self.client.post(
                '/api/v1/payment/payments/initialize/',
                {'order_uuid': str(self.order.uuid), 'card_token': 'tok_x', 'payment_source_id': 1},
            )
        self.assertEqual(response.status_code, 400)
        client_cls_mock.assert_not_called()
        self.assertFalse(Transaction.objects.filter(order=self.order).exists())

    @patch('payment.online.services.commands.WompiApiClient')
    def test_initialize_wompi_api_error_marks_transaction_error_and_returns_502(self, client_cls_mock):
        client_cls_mock.return_value.create_transaction.side_effect = WompiApiError('Wompi respondio 400: tarjeta invalida')
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_bad'},
        )

        self.assertEqual(response.status_code, 502)
        tx = Transaction.objects.get(order=self.order)
        self.assertEqual(tx.status, 'ERROR')

    @patch('payment.online.services.commands.PaymentCommands.confirm_payment')
    @patch('payment.online.services.commands.WompiApiClient')
    def test_initialize_approved_synchronously_triggers_confirm_payment(self, client_cls_mock, confirm_mock):
        client_cls_mock.return_value.create_transaction.return_value = {
            'id': 'wompi-live-3', 'status': 'APPROVED', 'payment_method_type': 'CARD',
        }
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_approved'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'APPROVED')
        confirm_mock.assert_called_once()
        called_tx = confirm_mock.call_args[0][0]
        self.assertEqual(called_tx.wompi_id, 'wompi-live-3')


@override_settings(ROOT_URLCONF='ecommerce.urls')
class WompiObservabilityTestCase(APITransactionTestCase):
    """
    Cubre la Fase 4 (observabilidad) de ADR-001: correlation_id propagado end-to-end,
    TransactionEvent como historial append-only en los 3 puntos de contacto con
    Wompi (creacion sincrona, sync por polling, webhook), y SecurityEvent.PAYMENT_APPROVED
    (antes solo existia el caso negativo, PAYMENT_DECLINED).
    """

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='wompi_observability@example.com', password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer, first_name='Cliente', last_name='Obs', user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Obs', address_line_1='Calle 5 # 5-5',
            city='Bogota', phone_number='3000000004', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('40000.00'),
        )

    def test_initialize_response_and_transaction_carry_correlation_id(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/v1/payment/payments/initialize/', {'order_uuid': str(self.order.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        corr = response.data['correlation_id']
        self.assertTrue(corr)
        tx = Transaction.objects.get(order=self.order)
        self.assertEqual(str(tx.correlation_id), corr)

    @patch('payment.online.services.commands.WompiApiClient')
    def test_sync_create_success_writes_transaction_event(self, client_cls_mock):
        client_cls_mock.return_value.create_transaction.return_value = {
            'id': 'wompi-obs-1', 'status': 'PENDING', 'payment_method_type': 'CARD',
        }
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_obs_1'},
        )

        tx = Transaction.objects.get(order=self.order)
        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_API_CREATE)
        self.assertEqual(event.previous_status, 'PENDING')
        self.assertEqual(event.new_status, 'PENDING')
        self.assertTrue(event.processed)
        self.assertEqual(event.correlation_id, response.data['correlation_id'])
        self.assertEqual(event.raw_payload['id'], 'wompi-obs-1')

    @patch('payment.online.services.commands.WompiApiClient')
    def test_sync_create_failure_writes_unprocessed_transaction_event(self, client_cls_mock):
        client_cls_mock.return_value.create_transaction.side_effect = WompiApiError('tarjeta rechazada')
        self.client.force_authenticate(user=self.customer)

        self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_obs_fail'},
        )

        tx = Transaction.objects.get(order=self.order)
        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_API_CREATE)
        self.assertEqual(event.new_status, 'ERROR')
        self.assertFalse(event.processed)
        self.assertIn('tarjeta rechazada', event.error_detail)

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.online.services.commands._has_sufficient_stock', return_value=True)
    @patch('payment.online.services.commands.confirm_order_payment')
    def test_webhook_approved_writes_event_and_security_event(self, confirm_order_mock, *_mocks):
        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING', correlation_id='corr-webhook-1',
        )
        payload = {'data': {'transaction': {'reference': str(tx.uuid), 'status': 'APPROVED', 'id': 'wompi-obs-2'}}}

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            WompiCommands.process_webhook_notification(payload)

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_WEBHOOK)
        self.assertEqual(event.previous_status, 'PENDING')
        self.assertEqual(event.new_status, 'APPROVED')
        self.assertEqual(event.correlation_id, 'corr-webhook-1')
        self.assertTrue(event.processed)

        approved_calls = [
            c for c in log_event_mock.call_args_list if c.args and c.args[0] == SecurityEvent.PAYMENT_APPROVED
        ]
        self.assertEqual(len(approved_calls), 1)
        self.assertEqual(approved_calls[0].kwargs['metadata']['correlation_id'], 'corr-webhook-1')

    def test_duplicate_webhook_writes_unprocessed_event(self):
        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='APPROVED',
            wompi_id='wompi-obs-3', correlation_id='corr-dup-1',
        )
        payload = {'data': {'transaction': {'reference': str(tx.uuid), 'status': 'APPROVED', 'id': 'wompi-obs-3'}}}

        WompiCommands.process_webhook_notification(payload)

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_WEBHOOK)
        self.assertFalse(event.processed)
        self.assertIn('duplicado', event.error_detail.lower())

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.online.services.commands._has_sufficient_stock', return_value=True)
    @patch('payment.online.services.commands.confirm_order_payment')
    @patch('payment.online.api.views.http_requests.get')
    def test_sync_status_change_writes_transaction_event(self, get_mock, *_mocks):
        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='PENDING',
            wompi_id='wompi-obs-4', correlation_id='corr-sync-1',
        )
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {'data': {'status': 'APPROVED', 'payment_method_type': 'CARD'}}

        self.client.force_authenticate(user=self.customer)
        self.client.get(f'/api/v1/payment/payments/transaction-status/?tx={tx.uuid}')

        event = TransactionEvent.objects.get(transaction=tx)
        self.assertEqual(event.source, TransactionEvent.SOURCE_API_SYNC)
        self.assertEqual(event.previous_status, 'PENDING')
        self.assertEqual(event.new_status, 'APPROVED')
        self.assertEqual(event.correlation_id, 'corr-sync-1')

    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.online.services.commands._has_sufficient_stock', return_value=True)
    @patch('payment.online.services.commands.confirm_order_payment')
    def test_confirm_payment_order_path_logs_payment_approved(self, confirm_order_mock, *_mocks):
        tx = Transaction.objects.create(
            order=self.order, amount_in_cents=4000000, status='APPROVED',
            wompi_id='wompi-obs-5', correlation_id='corr-approve-1',
        )
        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            PaymentCommands.confirm_payment(tx)

        confirm_order_mock.assert_called_once()
        approved_calls = [
            c for c in log_event_mock.call_args_list if c.args and c.args[0] == SecurityEvent.PAYMENT_APPROVED
        ]
        self.assertEqual(len(approved_calls), 1)
        self.assertEqual(approved_calls[0].kwargs['user'], self.customer)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class PaymentFeatureFlagsTestCase(APITransactionTestCase):
    """
    Cubre la Fase 5 (migracion gradual) de ADR-001: PaymentFeatureFlags como
    kill-switch real -- no solo una senal de UI, tambien aplicado en el
    backend, para que desactivarlo desde /admin/ tenga efecto inmediato sin
    deploy, incluso si alguien llama a initialize/ directamente.
    """

    def setUp(self):
        cache.clear()
        PaymentFeatureFlags.objects.all().delete()
        self.customer = User.objects.create_user(
            email='wompi_flags@example.com', password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer, first_name='Cliente', last_name='Flags', user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Flags', address_line_1='Calle 6 # 6-6',
            city='Bogota', phone_number='3000000005', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('30000.00'),
        )

    def test_get_active_creates_default_enabled_singleton_if_none_exists(self):
        self.assertEqual(PaymentFeatureFlags.objects.count(), 0)
        flags = PaymentFeatureFlags.get_active()
        self.assertTrue(flags.card_api_flow_enabled)
        self.assertEqual(PaymentFeatureFlags.objects.count(), 1)

    def test_saving_new_active_row_deactivates_previous_one(self):
        first = PaymentFeatureFlags.objects.create(card_api_flow_enabled=True)
        second = PaymentFeatureFlags.objects.create(card_api_flow_enabled=False)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(PaymentFeatureFlags.get_active().pk, second.pk)

    def test_feature_flags_endpoint_is_public_and_reflects_default(self):
        response = self.client.get('/api/v1/payment/payments/feature-flags/')  # sin autenticar
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['card_api_flow_enabled'])

    def test_feature_flags_endpoint_reflects_disabled_state(self):
        PaymentFeatureFlags.objects.create(card_api_flow_enabled=False)
        response = self.client.get('/api/v1/payment/payments/feature-flags/')
        self.assertFalse(response.data['card_api_flow_enabled'])

    @patch('payment.online.services.commands.WompiApiClient')
    def test_initialize_with_card_token_blocked_when_flag_disabled(self, client_cls_mock):
        PaymentFeatureFlags.objects.create(card_api_flow_enabled=False)
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/',
            {'order_uuid': str(self.order.uuid), 'card_token': 'tok_should_be_blocked'},
        )

        self.assertEqual(response.status_code, 403)
        client_cls_mock.return_value.create_transaction.assert_not_called()
        self.assertFalse(Transaction.objects.filter(order=self.order).exists())

    def test_initialize_without_card_token_unaffected_by_disabled_flag(self):
        """PSE/Otros (sin card_token/payment_source_id) nunca debe verse afectado por el flag."""
        PaymentFeatureFlags.objects.create(card_api_flow_enabled=False)
        self.client.force_authenticate(user=self.customer)

        response = self.client.post(
            '/api/v1/payment/payments/initialize/', {'order_uuid': str(self.order.uuid)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Transaction.objects.filter(order=self.order).exists())


@override_settings(ROOT_URLCONF='ecommerce.urls')
class PaymentAdminPanelTestCase(APITransactionTestCase):
    """
    Cubre la Fase 7 (ADR-001) de panel administrativo con acciones reales:
    resync manual, historial de TransactionEvent, y toggle de
    PaymentFeatureFlags -- todo expuesto en /api/v1/dashboard/payment-transactions/.
    Antes de esta fase el panel era 100% de solo lectura (hallazgo de Fase 0).
    """

    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(email='wompi_panel_admin@example.com', password='testpass123')
        self.customer = User.objects.create_user(email='wompi_panel_customer@example.com', password='testpass123')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='P', user_type='CUSTOMER')
        self.address = ShippingAddress.objects.create(
            user=self.customer, full_name='Cliente Panel', address_line_1='Calle 8 # 8-8',
            city='Bogota', phone_number='3000000010', is_default=True,
        )
        self.order = Order.objects.create(
            user=self.customer, shipping_address=self.address, status=Order.STATUS_PENDING_PAYMENT,
            payment_method='WOMPI', total_amount=Decimal('40000.00'),
        )

    def _url(self, tx_uuid, action):
        return f'/api/v1/dashboard/payment-transactions/{tx_uuid}/{action}/'

    @override_settings(WOMPI_PRIVATE_KEY='prv_test_dummy')
    @_PATCH_NOTIFICATION_COMMANDS
    @_PATCH_OPERATION_COMMANDS
    @_PATCH_SERVICE_COMMANDS
    @patch('payment.online.api.views.http_requests.get')
    def test_resync_updates_pending_transaction_with_known_wompi_id(self, get_mock, *_mocks):
        tx = Transaction.objects.create(
            order=self.order, wompi_id='wompi-panel-1', amount_in_cents=4000000, status='PENDING',
        )
        get_mock.return_value.status_code = 200
        get_mock.return_value.json.return_value = {'data': {'status': 'APPROVED', 'payment_method_type': 'CARD'}}

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self._url(tx.uuid, 'resync'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'APPROVED')
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'APPROVED')

    def test_resync_without_wompi_id_returns_409_without_calling_wompi(self):
        tx = Transaction.objects.create(order=self.order, amount_in_cents=4000000, status='PENDING')

        self.client.force_authenticate(user=self.admin)
        with patch('payment.online.api.views.http_requests.get') as get_mock:
            response = self.client.post(self._url(tx.uuid, 'resync'))
            get_mock.assert_not_called()

        self.assertEqual(response.status_code, 409)
        self.assertIn('detail', response.data)

    def test_resync_nonexistent_transaction_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(self._url('00000000-0000-0000-0000-000000000000', 'resync'))
        self.assertEqual(response.status_code, 404)

    def test_events_lists_transaction_history_newest_first(self):
        tx = Transaction.objects.create(order=self.order, amount_in_cents=4000000, status='PENDING')
        older = TransactionEvent.objects.create(
            transaction=tx, source=TransactionEvent.SOURCE_API_CREATE,
            previous_status='', new_status='PENDING', processed=True,
        )
        TransactionEvent.objects.filter(pk=older.pk).update(created_at=timezone.now() - timedelta(minutes=10))
        newer = TransactionEvent.objects.create(
            transaction=tx, source=TransactionEvent.SOURCE_WEBHOOK,
            previous_status='PENDING', new_status='APPROVED', processed=True,
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self._url(tx.uuid, 'events'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['uuid'], str(newer.uuid))
        self.assertEqual(response.data[1]['uuid'], str(older.uuid))

    def test_events_nonexistent_transaction_returns_404(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self._url('00000000-0000-0000-0000-000000000000', 'events'))
        self.assertEqual(response.status_code, 404)

    def test_feature_flags_get_and_patch(self):
        self.client.force_authenticate(user=self.admin)

        get_response = self.client.get('/api/v1/dashboard/payment-transactions/feature-flags/')
        self.assertEqual(get_response.status_code, 200)
        self.assertTrue(get_response.data['card_api_flow_enabled'])

        patch_response = self.client.patch(
            '/api/v1/dashboard/payment-transactions/feature-flags/', {'card_api_flow_enabled': False},
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertFalse(patch_response.data['card_api_flow_enabled'])
        self.assertFalse(PaymentFeatureFlags.get_active().card_api_flow_enabled)

    def test_feature_flags_patch_without_field_returns_400(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch('/api/v1/dashboard/payment-transactions/feature-flags/', {})
        self.assertEqual(response.status_code, 400)

    def test_feature_flags_patch_changed_value_logs_security_event(self):
        """ADR-001 Fase 8: togglear el kill-switch queda auditado (quien/desde donde)."""
        self.client.force_authenticate(user=self.admin)

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            self.client.patch(
                '/api/v1/dashboard/payment-transactions/feature-flags/', {'card_api_flow_enabled': False},
            )

        changed_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
        ]
        self.assertEqual(len(changed_calls), 1)
        self.assertEqual(changed_calls[0].kwargs['user'], self.admin)
        self.assertEqual(changed_calls[0].kwargs['metadata']['previous_value'], True)
        self.assertEqual(changed_calls[0].kwargs['metadata']['new_value'], False)
        self.assertEqual(changed_calls[0].kwargs['metadata']['source'], 'panel_admin')

    def test_feature_flags_patch_same_value_does_not_log_security_event(self):
        """Sin cambio real de valor, no hay nada operativamente significativo que auditar."""
        self.client.force_authenticate(user=self.admin)

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            self.client.patch(
                '/api/v1/dashboard/payment-transactions/feature-flags/', {'card_api_flow_enabled': True},
            )  # ya estaba en True por defecto -- sin cambio real

        changed_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
        ]
        self.assertEqual(len(changed_calls), 0)

    def test_non_admin_cannot_access_admin_payment_actions(self):
        tx = Transaction.objects.create(order=self.order, amount_in_cents=4000000, status='PENDING')
        self.client.force_authenticate(user=self.customer)

        self.assertEqual(self.client.post(self._url(tx.uuid, 'resync')).status_code, 403)
        self.assertEqual(self.client.get(self._url(tx.uuid, 'events')).status_code, 403)
        self.assertEqual(
            self.client.get('/api/v1/dashboard/payment-transactions/feature-flags/').status_code, 403,
        )


class PaymentFeatureFlagsAdminSaveModelTestCase(TestCase):
    """
    Cubre la Fase 8 (ADR-001) para el camino de Django /admin/: el mismo
    evento de auditoria que dispara el panel Vue tambien debe dispararse
    aqui, ya que /admin/ sigue siendo un camino real y documentado para
    togglear el kill-switch (Fase 5).
    """

    def setUp(self):
        from django.contrib.admin.sites import AdminSite
        from payment.admin import PaymentFeatureFlagsAdmin

        self.admin_user = User.objects.create_superuser(email='django_admin_flags@example.com', password='testpass123')
        self.model_admin = PaymentFeatureFlagsAdmin(PaymentFeatureFlags, AdminSite())
        self.fake_request = type('FakeRequest', (), {'user': self.admin_user})()

    def test_save_model_logs_security_event_on_real_change(self):
        flags = PaymentFeatureFlags.objects.create(card_api_flow_enabled=True)
        flags.card_api_flow_enabled = False

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            self.model_admin.save_model(self.fake_request, flags, form=None, change=True)

        changed_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
        ]
        self.assertEqual(len(changed_calls), 1)
        self.assertEqual(changed_calls[0].kwargs['metadata']['source'], 'django_admin')
        self.assertEqual(changed_calls[0].kwargs['metadata']['previous_value'], True)
        self.assertEqual(changed_calls[0].kwargs['metadata']['new_value'], False)
        self.assertFalse(PaymentFeatureFlags.get_active().card_api_flow_enabled)

    def test_save_model_without_real_change_does_not_log(self):
        flags = PaymentFeatureFlags.objects.create(card_api_flow_enabled=True)
        # No se muta card_api_flow_enabled -- simula guardar el formulario sin tocar el campo.

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            self.model_admin.save_model(self.fake_request, flags, form=None, change=True)

        changed_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
        ]
        self.assertEqual(len(changed_calls), 0)

    def test_save_model_on_creation_does_not_log(self):
        """change=False (alta nueva, no edicion) -- no hay 'valor anterior' que comparar."""
        flags = PaymentFeatureFlags(card_api_flow_enabled=True)

        with patch('security.services.commands.SecurityCommands.log_event') as log_event_mock:
            self.model_admin.save_model(self.fake_request, flags, form=None, change=False)

        changed_calls = [
            c for c in log_event_mock.call_args_list
            if c.args and c.args[0] == SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
        ]
        self.assertEqual(len(changed_calls), 0)
