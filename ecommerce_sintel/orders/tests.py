from decimal import Decimal
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from rest_framework.test import APITestCase

from payment.shared.commands import confirm_order_payment
from payment.models import CodTransaction
from users.models import User
from accounts.models import UserProfile
from orders.models import Order, ShippingAddress, DispatchCenter, Carrier, DeliveryDriver
from orders.services.commands import OrderCommands
from cart.models import Cart, CartItem
from shop.models import Category, Product, ProductVariant
from inventory.models import StockRecord
from inventory.services.commands import InventoryCommands
from inventory.services.dtos import StockAdjustmentDTO


@override_settings(ROOT_URLCONF='ecommerce.urls')
class OrderFulfillmentAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin_orders@example.com',
            password='adminpassword123',
        )
        UserProfile.objects.create(
            user=self.admin_user,
            first_name='Admin',
            last_name='Orders',
            user_type='ADMIN',
        )

        self.customer = User.objects.create_user(
            email='customer_orders@example.com',
            password='customerpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Customer',
            last_name='Orders',
            user_type='CUSTOMER',
        )

        self.address = ShippingAddress.objects.create(
            user=self.customer,
            full_name='Cliente Prueba',
            address_line_1='Calle 100 #10-20',
            city='Bogotá',
            state='Bogotá',
            postal_code='110111',
            country='Colombia',
            phone_number='3001234567',
            is_default=True,
        )

        self.order = Order.objects.create(
            user=self.customer,
            shipping_address=self.address,
            status=Order.STATUS_PAID,
            payment_method='WOMPI',
            total_amount=Decimal('95000.00'),
            discount_amount=Decimal('0.00'),
        )

        self.dispatch_center = DispatchCenter.objects.create(
            name='Centro Bogotá',
            city='Bogotá',
            department='Cundinamarca',
            address='Av. Carrera 15 #100-25',
            hours='08:00-18:00',
            daily_capacity=50,
            is_active=True,
            responsible=self.admin_user,
        )
        self.carrier = Carrier.objects.create(
            name='Transportes Seguro',
            contact_phone='3101234567',
            contact_email='contacto@seguro.com',
            active=True,
        )
        self.driver = DeliveryDriver.objects.create(
            name='Juan Repartidor',
            phone_number='3007654321',
            driver_type=DeliveryDriver.EMPLOYEE,
            vehicle='Moto 125cc',
            plate='ABC123',
            active=True,
            carrier=self.carrier,
        )

    def test_list_orders_has_no_n_plus_1(self):
        """
        Cubre un bug de rendimiento real detectado el 2026-07-03 (Fase 6, auditoria de BD):
        OrderSelector.list_for_user()/list_all_for_admin() no traian select_related/prefetch_related
        para las relaciones que OrderSerializer siempre serializa (items, shipping_address, shipment
        + shipment.dispatch_center/carrier/driver). Listar 2 ordenes tomaba 19 queries (escalaba
        linealmente con N); con el fix, 3 queries constantes sin importar cuantas ordenes haya.
        """
        from orders.models import OrderItem, Shipment

        OrderItem.objects.create(order=self.order, item_name='Item 1', sku='SKU-1', quantity=1, price=Decimal('10000'))
        OrderItem.objects.create(order=self.order, item_name='Item 2', sku='SKU-2', quantity=2, price=Decimal('20000'))
        Shipment.objects.create(
            order=self.order, shipment_number='SHP-TEST-1',
            dispatch_center=self.dispatch_center, carrier=self.carrier, driver=self.driver,
        )
        second_order = Order.objects.create(
            user=self.customer, shipping_address=self.address,
            status=Order.STATUS_PAID, payment_method='COD', total_amount=Decimal('50000.00'),
        )
        OrderItem.objects.create(order=second_order, item_name='Item 3', sku='SKU-3', quantity=1, price=Decimal('50000'))

        self.client.force_authenticate(user=self.customer)
        with self.assertNumQueries(3):
            response = self.client.get('/api/v1/orders/orders/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)

    def test_order_fulfillment_workflow(self):
        self.client.force_authenticate(user=self.admin_user)

        url_prefix = f'/api/v1/orders/orders/{self.order.uuid}'

        response = self.client.post(f'{url_prefix}/prepare/', {'comment': 'Iniciar preparación'})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PREPARING)

        response = self.client.post(f'{url_prefix}/pack/', {'comment': 'Empaque completado'})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_READY_FOR_DISPATCH)

        response = self.client.post(
            f'{url_prefix}/assign-dispatch-center/',
            {'dispatch_center_uuid': str(self.dispatch_center.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_READY_FOR_DISPATCH)

        response = self.client.post(
            f'{url_prefix}/assign-carrier/',
            {'carrier_uuid': str(self.carrier.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_ASSIGNED)

        response = self.client.post(
            f'{url_prefix}/assign-driver/',
            {'driver_uuid': str(self.driver.uuid)},
        )
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_ASSIGNED)

        response = self.client.post(f'{url_prefix}/dispatch/', {'comment': 'Pedido pickup'})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PICKED_UP)

        response = self.client.post(f'{url_prefix}/in-transit/', {'comment': 'Transporte en camino'})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_IN_TRANSIT)

        response = self.client.post(f'{url_prefix}/deliver/', {'comment': 'Entrega exitosa'})
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_DELIVERED)

        response = self.client.get(f'{url_prefix}/timeline/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 5)

        response = self.client.post(
            f'{url_prefix}/add-tracking-point/',
            {'lat': '4.7110', 'lng': '-74.0721', 'accuracy': '3.4'},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['order'], self.order.id)

        response = self.client.get(f'{url_prefix}/tracking/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    @patch('notifications.services.commands.NotificationCommands.dispatch_notification')
    @patch('operations.services.commands.OperationCommands.ensure_tickets_for_order')
    @patch('technical_services.services.commands.ServiceCommands.confirm_slot_on_payment')
    def test_pending_payment_to_paid_then_prepare(
        self,
        confirm_slot_on_payment_mock,
        ensure_tickets_mock,
        dispatch_notification_mock,
    ):
        self.order.status = Order.STATUS_PENDING_PAYMENT
        self.order.save(update_fields=['status', 'updated_at'])

        confirm_order_payment(self.order, reference='test-payment-001')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)

        self.client.force_authenticate(user=self.admin_user)
        url_prefix = f'/api/v1/orders/orders/{self.order.uuid}'
        response = self.client.post(f'{url_prefix}/prepare/', {'comment': 'Iniciar preparación tras pago'})
        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PREPARING)

        response = self.client.get(f'{url_prefix}/timeline/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class CodCheckoutEndToEndTestCase(APITestCase):
    """
    Cubre el bug detectado el 2026-07-03: create_from_cart() con
    payment_method='COD' creaba la orden pero nunca llamaba a
    CodCommands.confirm_order() -- ninguna orden COD del checkout normal de
    tienda/servicios quedaba confirmada (sin CodTransaction, sin descuento de
    inventario, atascada en STATUS_PENDING_PAYMENT para siempre).
    """

    def setUp(self):
        self.customer = User.objects.create_user(
            email='cod_checkout_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='COD',
            user_type='CUSTOMER',
        )
        self.address = ShippingAddress.objects.create(
            user=self.customer,
            full_name='Cliente COD',
            address_line_1='Calle 4 # 4-4',
            city='Bogota',
            phone_number='3000000003',
            is_default=True,
        )

        category = Category.objects.create(name='Categoria COD', slug='categoria-cod-test')
        product = Product.objects.create(
            vendor=self.customer,
            category=category,
            name='Producto COD Test',
            slug='producto-cod-test',
        )
        self.variant = ProductVariant.objects.create(
            product=product,
            sku='COD-TEST-SKU-1',
            price=Decimal('40000.00'),
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
            reference='Stock inicial para test de checkout COD',
        ))

        cart = Cart.objects.create(user=self.customer)
        CartItem.objects.create(cart=cart, variant=self.variant, quantity=3)

    @patch('notifications.services.commands.NotificationCommands.dispatch_notification')
    @patch('operations.services.commands.OperationCommands.ensure_tickets_for_order')
    def test_create_from_cart_with_cod_confirms_order_and_deducts_stock(self, *_mocks):
        order = OrderCommands.create_from_cart(
            user=self.customer,
            shipping_address=self.address,
            payment_method='COD',
        )

        order.refresh_from_db()
        self.stock_record.refresh_from_db()

        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertTrue(CodTransaction.objects.filter(order=order).exists())
        self.assertEqual(self.stock_record.stock, 7)

    @patch('notifications.services.commands.NotificationCommands.dispatch_notification')
    @patch('operations.services.commands.OperationCommands.ensure_tickets_for_order')
    def test_create_from_cart_with_cod_via_api_confirms_order(self, *_mocks):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            '/api/v1/orders/orders/create_from_cart/',
            {
                'shipping_address_uuid': str(self.address.uuid),
                'payment_method': 'COD',
            },
        )

        self.assertEqual(response.status_code, 201)
        order = Order.objects.get(uuid=response.data['uuid'])
        self.stock_record.refresh_from_db()

        self.assertEqual(order.status, Order.STATUS_PAID)
        self.assertTrue(CodTransaction.objects.filter(order=order).exists())
        self.assertEqual(self.stock_record.stock, 7)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ServiceOrderConfirmCodTestCase(APITestCase):
    """
    Cubre un tercer caso del mismo bug (2026-07-03): ServiceOrderViewSet.confirm_cod
    comparaba order.status contra el string legacy 'pending', pero las ordenes se
    crean con Order.STATUS_PENDING_PAYMENT -- confirmar un pago COD en sitio para un
    servicio tecnico siempre devolvia 400.
    """

    def setUp(self):
        from technical_services.models import OrderServiceDetail

        self.customer = User.objects.create_user(
            email='service_cod_customer@example.com',
            password='testpassword123',
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name='Cliente',
            last_name='ServicioCOD',
            user_type='CUSTOMER',
        )
        self.order = Order.objects.create(
            user=self.customer,
            status=Order.STATUS_PENDING_PAYMENT,
            payment_method='COD',
            total_amount=Decimal('80000.00'),
        )
        OrderServiceDetail.objects.create(
            order=self.order,
            description='Instalacion de aire acondicionado',
            address='Calle 5 # 5-5, Bogota',
        )

    @patch('notifications.services.commands.NotificationCommands.dispatch_notification')
    @patch('operations.services.commands.OperationCommands.ensure_tickets_for_order')
    @patch('technical_services.services.commands.ServiceCommands.confirm_slot_on_payment')
    def test_confirm_cod_accepts_order_in_pending_payment_status(self, *_mocks):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/api/v1/orders/service-orders/{self.order.uuid}/confirm-cod/'
        )

        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.STATUS_PAID)


class ShippingAddressBookTestCase(APITestCase):
    """
    'Mis Direcciones': antes el frontend llamaba a orders/shipping-addresses/
    (404 -- el path real registrado es orders/addresses/) y ShippingAddressViewSet
    no garantizaba unicidad del is_default. Cubre ambos fixes + el endpoint
    set-default nuevo.
    """

    def setUp(self):
        self.customer = User.objects.create_user(email='addr_customer@example.com', password='Pass123!')
        UserProfile.objects.create(user=self.customer, first_name='Addr', last_name='Customer', user_type=UserProfile.CUSTOMER)
        self.client.force_authenticate(self.customer)

    def test_addresses_endpoint_is_at_the_registered_path(self):
        response = self.client.get('/api/v1/orders/addresses/')
        self.assertEqual(response.status_code, 200)

    def test_first_address_created_is_automatically_default(self):
        response = self.client.post('/api/v1/orders/addresses/', {
            'label': 'Casa', 'full_name': 'Addr Customer', 'address_line_1': 'Calle 1 # 2-3',
            'city': 'Bogota', 'phone_number': '3001234567',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_default'])

    def test_set_default_unsets_the_previous_default(self):
        first = ShippingAddress.objects.create(
            user=self.customer, label='Casa', full_name='Addr Customer',
            address_line_1='Calle 1 # 2-3', city='Bogota', phone_number='3001234567', is_default=True,
        )
        second = ShippingAddress.objects.create(
            user=self.customer, label='Oficina', full_name='Addr Customer',
            address_line_1='Calle 5 # 6-7', city='Bogota', phone_number='3007654321', is_default=False,
        )

        response = self.client.post(f'/api/v1/orders/addresses/{second.uuid}/set-default/')
        self.assertEqual(response.status_code, 200)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertTrue(second.is_default)

    def test_update_with_is_default_true_unsets_other_addresses(self):
        first = ShippingAddress.objects.create(
            user=self.customer, full_name='Addr Customer', address_line_1='Calle 1 # 2-3',
            city='Bogota', phone_number='3001234567', is_default=True,
        )
        second = ShippingAddress.objects.create(
            user=self.customer, full_name='Addr Customer', address_line_1='Calle 5 # 6-7',
            city='Bogota', phone_number='3007654321', is_default=False,
        )
        response = self.client.patch(f'/api/v1/orders/addresses/{second.uuid}/', {'is_default': True}, format='json')
        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        self.assertFalse(first.is_default)


class RegistrationCreatesDefaultShippingAddressTestCase(APITestCase):
    """
    SSoT: la direccion estructurada capturada en /register (kyc_data['profile_extra']
    ['address'], armada por el constructor colombiano de PersonalInfoFields.vue) debe
    convertirse automaticamente en la primera ShippingAddress (is_default=True) del
    usuario -- nunca se le vuelve a pedir en 'Mis Direcciones'.
    """

    def test_create_from_verified_payload_creates_default_address(self):
        from accounts.services.commands import AccountCommands

        payload = {
            'email': 'addr_register@example.com',
            'password_hash': 'pbkdf2_sha256$dummy$hash$value',
            'phone_number': '+573001112233',
            'primer_nombre': 'Ana', 'segundo_nombre': '', 'primer_apellido': 'Lopez', 'segundo_apellido': '',
            'fecha_nacimiento': '1995-05-05', 'sexo': 'F', 'nacionalidad': 'Colombiana',
            'pais': 'Colombia', 'ciudad': 'Bogota',
            'direccion': 'Calle 31 Bis # 68 I - 38',
            'tipo_documento': 'CC', 'numero_documento': '1000000001',
            'fecha_expedicion_documento': None, 'lugar_expedicion_documento': 'Bogota',
            'acepta_politica_tratamiento_datos': True,
            'acepta_autorizacion_tratamiento_datos': True,
            'acepta_terminos_condiciones': True,
        }
        user = AccountCommands.create_from_verified_payload(payload)

        address = ShippingAddress.objects.get(user=user)
        self.assertTrue(address.is_default)
        self.assertEqual(address.address_line_1, 'Calle 31 Bis # 68 I - 38')
        self.assertEqual(address.city, 'Bogota')
        self.assertEqual(address.country, 'Colombia')
        self.assertEqual(address.label, 'Principal')
        self.assertEqual(address.phone_number, '3001112233')
