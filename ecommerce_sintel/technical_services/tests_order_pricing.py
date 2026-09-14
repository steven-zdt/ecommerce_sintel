"""
technical_services/tests_order_pricing.py

Plan "Manual Pricing Engine" (2026-08-13) FASE 18-19 -- estado del precio
comercial de una orden YA CREADA (OrderPricingCommands) + su exposicion en
/panel/servicios/operaciones (ServiceOperationViewSet.confirm-price/
override-price). Archivo separado, mismo criterio que tests_operations.py/
tests_packages.py -- domino propio, no mezclar con tests.py.

Decision confirmada con el usuario antes de escribir este codigo: estos
comandos NUNCA modifican Order.total_amount/OrderItem.price -- ver
test_override_price_never_touches_order_total_amount, la prueba mas
importante de este archivo.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from accounts.models import UserProfile
from orders.models import Order
from technical_services.models import (
    OrderPriceAdjustment, OrderServiceDetail, ServiceCategory, ServiceVariant,
    TechnicalService,
)
from technical_services.services.commands import OrderPricingCommands, ServiceCommands
from technical_services.services.operations import ServiceOperationCommands

User = get_user_model()


class OrderPricingCommandsTestCase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='order_pricing_customer@example.com', password='x')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.admin = User.objects.create_superuser(email='order_pricing_admin@example.com', password='x')

        self.category = ServiceCategory.objects.create(name='Cat Order Pricing', slug='cat-order-pricing')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Order Pricing', slug='servicio-order-pricing',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='ORDPRICE-001', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('200000.00'),
        )
        self.order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Orden de prueba', 'address': 'Calle 1'},
        )
        self.detail = self.order.service_detail

    def test_new_order_starts_estimated(self):
        self.assertEqual(self.detail.price_status, OrderServiceDetail.PRICE_STATUS_ESTIMATED)
        self.assertIsNone(self.detail.confirmed_total)

    def test_confirm_price_sets_confirmed_total_from_order_total(self):
        OrderPricingCommands.confirm_price(self.detail, changed_by=self.admin)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.price_status, OrderServiceDetail.PRICE_STATUS_CONFIRMED)
        self.assertEqual(self.detail.confirmed_total, self.order.total_amount)

    def test_override_price_requires_non_empty_reason(self):
        with self.assertRaises(ValueError):
            OrderPricingCommands.override_price(self.detail, new_total=Decimal('250000'), reason='', changed_by=self.admin)
        with self.assertRaises(ValueError):
            OrderPricingCommands.override_price(self.detail, new_total=Decimal('250000'), reason='   ', changed_by=self.admin)

    def test_override_price_rejects_negative_total(self):
        with self.assertRaises(ValueError):
            OrderPricingCommands.override_price(
                self.detail, new_total=Decimal('-1'), reason='Ajuste', changed_by=self.admin,
            )

    def test_override_price_creates_adjustment_with_old_and_new_total(self):
        original_total = self.order.total_amount
        OrderPricingCommands.override_price(
            self.detail, new_total=Decimal('250000.00'), reason='Trabajo en altura', changed_by=self.admin,
        )
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.price_status, OrderServiceDetail.PRICE_STATUS_OVERRIDDEN)
        self.assertEqual(self.detail.confirmed_total, Decimal('250000.00'))

        adjustment = OrderPriceAdjustment.objects.get(order_service_detail=self.detail)
        self.assertEqual(adjustment.old_total, original_total)
        self.assertEqual(adjustment.new_total, Decimal('250000.00'))
        self.assertEqual(adjustment.reason, 'Trabajo en altura')
        self.assertEqual(adjustment.changed_by, self.admin)

    def test_second_override_uses_previous_confirmed_total_as_old_total(self):
        OrderPricingCommands.override_price(self.detail, new_total=Decimal('250000'), reason='Primer ajuste', changed_by=self.admin)
        self.detail.refresh_from_db()
        OrderPricingCommands.override_price(self.detail, new_total=Decimal('300000'), reason='Segundo ajuste', changed_by=self.admin)
        self.detail.refresh_from_db()

        second_adjustment = OrderPriceAdjustment.objects.filter(order_service_detail=self.detail).order_by('created_at').last()
        self.assertEqual(second_adjustment.old_total, Decimal('250000'))
        self.assertEqual(second_adjustment.new_total, Decimal('300000'))
        self.assertEqual(self.detail.confirmed_total, Decimal('300000'))

    def test_override_price_never_touches_order_total_amount(self):
        """La prueba mas importante de este archivo -- confirma la decision de
        alcance tomada explicitamente con el usuario antes de escribir este
        codigo: el override queda auditado, pero Order.total_amount (lo que
        Wompi ya cobro o va a cobrar) NUNCA cambia."""
        original_total = self.order.total_amount
        OrderPricingCommands.override_price(
            self.detail, new_total=Decimal('999999.00'), reason='Cambio grande', changed_by=self.admin,
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_amount, original_total)
        self.assertNotEqual(self.order.total_amount, Decimal('999999.00'))

    def test_lock_price_prevents_confirm_and_override(self):
        OrderPricingCommands.lock_price(self.detail)
        self.detail.refresh_from_db()
        self.assertEqual(self.detail.price_status, OrderServiceDetail.PRICE_STATUS_LOCKED)

        with self.assertRaises(ValueError):
            OrderPricingCommands.confirm_price(self.detail, changed_by=self.admin)
        with self.assertRaises(ValueError):
            OrderPricingCommands.override_price(self.detail, new_total=Decimal('1'), reason='x', changed_by=self.admin)


class ServiceOperationPriceAPITestCase(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='order_pricing_api_customer@example.com', password='x')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.admin = User.objects.create_superuser(email='order_pricing_api_admin@example.com', password='x')

        self.category = ServiceCategory.objects.create(name='Cat Order Pricing API', slug='cat-order-pricing-api')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Order Pricing API', slug='servicio-order-pricing-api',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='ORDPRICEAPI-001', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('180000.00'),
        )
        self.order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Orden API', 'address': 'Calle 2'},
        )
        self.operation = ServiceOperationCommands.ensure_for_order(self.order, self.admin)

    def _url(self, action):
        return f'/api/v1/service-operations/{self.operation.uuid}/{action}/'

    def test_confirm_price_requires_admin(self):
        resp = self.client.post(self._url('confirm-price'))
        self.assertEqual(resp.status_code, 401)
        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(self._url('confirm-price'))
        self.assertEqual(resp.status_code, 403)

    def test_confirm_price_success_exposes_new_fields_in_quotation_block(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url('confirm-price'))
        self.assertEqual(resp.status_code, 200)
        quotation = resp.data['order']['quotation']
        self.assertEqual(quotation['price_status'], 'CONFIRMED')
        self.assertEqual(Decimal(quotation['confirmed_total']), self.order.total_amount)

    def test_override_price_requires_reason(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url('override-price'), {'new_total': '200000.00'})
        self.assertEqual(resp.status_code, 400)

    def test_override_price_success(self):
        # total_amount real incluye IVA (quotation['total_price'], no fixed_price
        # crudo) -- se captura antes del override para comparar contra el mismo
        # valor despues, no un numero hardcodeado que asuma la formula de IVA.
        original_total = self.order.total_amount

        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url('override-price'), {
            'new_total': '220000.00', 'reason': 'Dificultad especial detectada en sitio',
        })
        self.assertEqual(resp.status_code, 200)
        quotation = resp.data['order']['quotation']
        self.assertEqual(quotation['price_status'], 'OVERRIDDEN')
        self.assertEqual(quotation['confirmed_total'], '220000.00')

        # Order.total_amount real -- confirmado sin cambios tambien a nivel API.
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_amount, original_total)

    def test_override_price_on_locked_order_returns_400(self):
        from technical_services.services.commands import OrderPricingCommands
        OrderPricingCommands.lock_price(self.order.service_detail)
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url('override-price'), {'new_total': '1', 'reason': 'x'})
        self.assertEqual(resp.status_code, 400)
