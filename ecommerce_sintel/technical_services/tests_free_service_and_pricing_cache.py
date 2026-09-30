"""
technical_services/tests_free_service_and_pricing_cache.py

Dos cambios de 2026-09-30:

1. Servicios sin costo (visita diagnostica / levantamiento de informacion para
   cotizar): ServiceCommands.request_service() confirma la orden al crearla
   (payment.shared.commands.confirm_order_payment) cuando el total es 0. Un servicio
   con precio debe seguir en PENDING_PAYMENT esperando el pago.
2. Optimizacion (plan de optimizacion del CRUD de Servicios): ServiceVariantSerializer
   calcula la cotizacion UNA sola vez por variante (antes calculated_price y
   price_info la calculaban cada uno) sin alterar el resultado.
"""
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from orders.models import Order
from technical_services.api.serializers import ServiceVariantSerializer
from technical_services.models import ServiceCategory, ServiceVariant, TechnicalService
from technical_services.services import ServiceSelector
from technical_services.services.commands import ServiceCommands

User = get_user_model()

DETAIL = {'priority': 'medium', 'description': 'Prueba', 'address': 'Calle 1'}


class _Base(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='free_svc_customer@example.com', password='x')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.admin = User.objects.create_superuser(email='free_svc_admin@example.com', password='x')
        self.category = ServiceCategory.objects.create(name='Cat Free Svc', slug='cat-free-svc')

    def make_variant(self, slug, price):
        service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name=f'Servicio {slug}', slug=slug,
        )
        return ServiceVariant.objects.create(
            service=service, sku=f'SKU-{slug}', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal(price),
        )


class FreeServiceOrderTestCase(_Base):
    def test_zero_total_order_is_confirmed_without_payment(self):
        variant = self.make_variant('visita-gratis', '0.00')
        order = ServiceCommands.request_service(
            user=self.customer, variant=variant, quantity=1, service_detail_data=dict(DETAIL),
        )
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal('0.00'))
        self.assertEqual(order.status, Order.STATUS_PAID)

    def test_priced_order_still_waits_for_payment(self):
        variant = self.make_variant('servicio-pago', '1000.00')
        order = ServiceCommands.request_service(
            user=self.customer, variant=variant, quantity=1, service_detail_data=dict(DETAIL),
        )
        order.refresh_from_db()
        self.assertGreater(order.total_amount, Decimal('0'))
        self.assertEqual(order.status, Order.STATUS_PENDING_PAYMENT)


class VariantQuotationComputedOnceTestCase(_Base):
    def test_quotation_computed_once_per_variant_and_values_unchanged(self):
        variants = [self.make_variant('cache-a', '50000.00'), self.make_variant('cache-b', '80000.00')]
        with mock.patch.object(
            ServiceSelector, 'get_variant_quotation', wraps=ServiceSelector.get_variant_quotation
        ) as spy:
            data = ServiceVariantSerializer(variants, many=True).data
        # Una llamada por variante (antes: dos, una por campo).
        self.assertEqual(spy.call_count, len(variants))
        for row in data:
            # Ambos campos salen de la misma cotizacion.
            self.assertEqual(row['calculated_price'], row['price_info']['total_price'])
            self.assertIsNotNone(row['price_info'])
        # 50000 + 19% IVA
        self.assertEqual(data[0]['calculated_price'], 59500.0)
