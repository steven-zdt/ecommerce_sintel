"""
Tests del dominio de Paquetes de Servicio (2026-07-16): ServicePackage,
PackageIncludedItem, PackageAdditionalCost, PackagePriceCalculator, y su
integracion aditiva con ServiceCommands.request_service.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from technical_services.models import (
    ServiceCategory, TechnicalService, ServiceVariant,
    ServicePackage, PackageIncludedItem, PackageAdditionalCost,
    ServiceRequestPackage, ServiceRequestAdditionalCost, ServiceOperation,
)
from technical_services.services import (
    ServicePackageCommands, PackageIncludedItemCommands, PackageAdditionalCostCommands,
    PackagePriceCalculator, ServiceCommands,
)

User = get_user_model()


class PackageModelsTestCase(APITestCase):
    """Commands de servicio: create/update/delete/toggle/duplicate/reorder."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_pkg@example.com', password='testpass123')
        self.category = ServiceCategory.objects.create(name='Cat Pkg', slug='cat-pkg-test')
        self.service = TechnicalService.objects.create(
            vendor=self.vendor, category=self.category, name='Servicio Pkg Test', slug='servicio-pkg-test',
            description='desc',
        )

    def test_package_crud_toggle_duplicate_reorder(self):
        pkg1 = ServicePackageCommands.create(self.service, name='4 Camaras', base_price=Decimal('150000'))
        pkg2 = ServicePackageCommands.create(self.service, name='8 Camaras', base_price=Decimal('250000'))

        ServicePackageCommands.update(pkg1, name='4 Camaras Actualizado')
        pkg1.refresh_from_db()
        self.assertEqual(pkg1.name, '4 Camaras Actualizado')

        toggled = ServicePackageCommands.toggle_active(pkg1)
        self.assertFalse(toggled.is_active)
        ServicePackageCommands.toggle_active(pkg1)

        dup = ServicePackageCommands.duplicate(pkg2)
        self.assertNotEqual(dup.uuid, pkg2.uuid)
        self.assertIn('copia', dup.name)

        ServicePackageCommands.reorder(self.service.id, [str(pkg2.uuid), str(pkg1.uuid)])
        pkg1.refresh_from_db()
        pkg2.refresh_from_db()
        self.assertEqual(pkg2.position, 0)
        self.assertEqual(pkg1.position, 1)

        ServicePackageCommands.delete(pkg2)
        self.assertTrue(ServicePackage.objects.get(pk=pkg2.pk).is_deleted)

    def test_package_default_flag_is_exclusive(self):
        pkg1 = ServicePackageCommands.create(self.service, name='A', base_price=Decimal('1'), is_default=True)
        pkg2 = ServicePackageCommands.create(self.service, name='B', base_price=Decimal('1'), is_default=True)
        pkg1.refresh_from_db()
        self.assertFalse(pkg1.is_default)
        self.assertTrue(pkg2.is_default)

    def test_included_item_and_additional_cost_crud(self):
        pkg = ServicePackageCommands.create(self.service, name='8 Camaras', base_price=Decimal('250000'))
        item = PackageIncludedItemCommands.create(pkg, title='Limpieza', icon='bi-droplet')
        self.assertEqual(PackageIncludedItem.objects.filter(package=pkg, is_deleted=False).count(), 1)
        PackageIncludedItemCommands.delete(item)
        self.assertEqual(PackageIncludedItem.objects.filter(package=pkg, is_deleted=False).count(), 0)

        cost = PackageAdditionalCostCommands.create(
            pkg, name='Escalera', cost_type=PackageAdditionalCost.TYPE_LADDER,
            price=Decimal('45000'), unit=PackageAdditionalCost.UNIT_FIXED,
        )
        self.assertEqual(cost.get_unit_display(), 'Fijo')
        toggled = PackageAdditionalCostCommands.toggle_active(cost)
        self.assertFalse(toggled.is_active)


class PackagePriceCalculatorTestCase(APITestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_calc@example.com', password='testpass123')
        self.category = ServiceCategory.objects.create(name='Cat Calc', slug='cat-calc-test')
        self.service = TechnicalService.objects.create(
            vendor=self.vendor, category=self.category, name='Servicio Calc Test', slug='servicio-calc-test',
            description='desc',
        )
        self.package = ServicePackageCommands.create(self.service, name='8 Camaras', base_price=Decimal('250000'))
        self.ladder = PackageAdditionalCostCommands.create(
            self.package, name='Escalera', cost_type='ESCALERA', price=Decimal('45000'), unit='FIJO',
        )
        self.operator = PackageAdditionalCostCommands.create(
            self.package, name='Operario', cost_type='OPERARIO', price=Decimal('60000'), unit='PERSONA',
        )

    def test_calculate_without_additional_costs(self):
        breakdown = PackagePriceCalculator.calculate(self.package)
        self.assertEqual(breakdown['package_price'], Decimal('250000.00'))
        self.assertEqual(breakdown['additional_costs_total'], Decimal('0.00'))
        self.assertEqual(breakdown['subtotal'], Decimal('250000.00'))
        # IVA default 19%
        self.assertEqual(breakdown['iva_amount'], Decimal('47500.00'))
        self.assertEqual(breakdown['total'], Decimal('297500.00'))

    def test_calculate_with_additional_costs_and_quantities(self):
        breakdown = PackagePriceCalculator.calculate(
            self.package,
            additional_cost_selections=[
                {'additional_cost': self.ladder, 'quantity': 1},
                {'additional_cost': self.operator, 'quantity': 2},
            ],
        )
        # 45000 + (60000*2) = 165000
        self.assertEqual(breakdown['additional_costs_total'], Decimal('165000.00'))
        self.assertEqual(breakdown['subtotal'], Decimal('415000.00'))
        self.assertEqual(breakdown['total'], Decimal('415000.00') * Decimal('1.19'))

    def test_calculate_with_extra_base_and_discount(self):
        breakdown = PackagePriceCalculator.calculate(
            self.package, extra_base=Decimal('20000'), discount_pct=Decimal('10'),
        )
        subtotal = Decimal('250000.00') + Decimal('20000.00')
        self.assertEqual(breakdown['subtotal'], subtotal)
        expected_discount = (subtotal * Decimal('10') / Decimal('100')).quantize(Decimal('0.01'))
        self.assertEqual(breakdown['discount_amount'], expected_discount)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class ServiceCommandsPackageIntegrationTestCase(APITestCase):
    """Integracion con ServiceCommands.request_service, ServiceOperation y compatibilidad."""

    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_int@example.com', password='testpass123')
        self.customer = User.objects.create_user(email='customer_int@example.com', password='testpass123')
        self.category = ServiceCategory.objects.create(name='Cat Int', slug='cat-int-test')
        self.service = TechnicalService.objects.create(
            vendor=self.vendor, category=self.category, name='Servicio Int Test', slug='servicio-int-test',
            description='desc',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='INT-FIXED', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('100000'),
        )
        self.package = ServicePackageCommands.create(self.service, name='8 Camaras', base_price=Decimal('250000'))
        self.ladder = PackageAdditionalCostCommands.create(
            self.package, name='Escalera', cost_type='ESCALERA', price=Decimal('45000'), unit='FIJO',
        )

    def _service_detail_data(self):
        return {
            'priority': 'medium',
            'description': 'Mantenimiento de 8 camaras',
            'address': 'Calle 123',
            'contact_person': {
                'full_name': 'Juan Perez', 'document_type': 'CC', 'document_number': '123',
                'cargo': 'Gerente', 'email': 'juan@example.com', 'phone': '3001234567',
            },
        }

    def test_request_service_without_package_is_unaffected(self):
        """Compatibilidad hacia atras: sin package, el comportamiento es identico al anterior."""
        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data=self._service_detail_data(),
        )
        self.assertEqual(order.total_amount, Decimal('100000.00') * Decimal('1.19'))
        self.assertFalse(ServiceRequestPackage.objects.filter(order=order).exists())
        # ServiceOperation sigue creandose igual (compatibilidad con Operations)
        self.assertTrue(ServiceOperation.objects.filter(order=order).exists())

    def test_request_service_with_package_combines_totals(self):
        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data=self._service_detail_data(),
            package=self.package,
            additional_cost_selections=[{'additional_cost': self.ladder, 'quantity': 1}],
        )
        # subtotal = variant(100000) + package(250000) + ladder(45000) = 395000
        expected_total = (Decimal('395000.00') * Decimal('1.19')).quantize(Decimal('0.01'))
        self.assertEqual(order.total_amount, expected_total)

        request_package = ServiceRequestPackage.objects.get(order=order)
        self.assertEqual(request_package.package_price_snapshot, Decimal('250000.00'))
        self.assertEqual(
            ServiceRequestAdditionalCost.objects.filter(request_package=request_package).count(), 1,
        )
        # ServiceOperation (dominio operativo) sigue intacto con package
        self.assertTrue(ServiceOperation.objects.filter(order=order).exists())

    def test_request_service_rejects_package_from_other_service(self):
        other_category = ServiceCategory.objects.create(name='Cat Otro Pkg', slug='cat-otro-pkg-test')
        other_service = TechnicalService.objects.create(
            vendor=self.vendor, category=other_category, name='Otro Servicio', slug='otro-servicio-pkg-test',
            description='desc',
        )
        other_package = ServicePackageCommands.create(other_service, name='Otro Paquete', base_price=Decimal('1'))

        with self.assertRaises(ValueError):
            ServiceCommands.request_service(
                user=self.customer, variant=self.variant, quantity=1,
                service_detail_data=self._service_detail_data(),
                package=other_package,
            )

    def test_endpoint_lists_packages_with_nested_items(self):
        PackageIncludedItemCommands.create(self.package, title='Limpieza', icon='bi-droplet')
        url = f'/api/v1/services/services/{self.service.uuid}/packages/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], '8 Camaras')
        self.assertEqual(len(response.data[0]['included_items']), 1)
        self.assertEqual(len(response.data[0]['additional_costs']), 1)

    def test_endpoint_quote_package_matches_order_total(self):
        url = f'/api/v1/services/services/{self.service.uuid}/quote-package/'
        response = self.client.post(url, {
            'package_uuid': str(self.package.uuid),
            'variant_uuid': str(self.variant.uuid),
            'additional_costs': [{'additional_cost_uuid': str(self.ladder.uuid), 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data=self._service_detail_data(),
            package=self.package,
            additional_cost_selections=[{'additional_cost': self.ladder, 'quantity': 1}],
        )
        self.assertEqual(Decimal(str(response.data['total'])), order.total_amount)

    def test_endpoint_create_order_with_package_via_api(self):
        self.client.force_authenticate(user=self.customer)
        payload = {
            'variant_uuid': str(self.variant.uuid),
            'quantity': 1,
            'package_uuid': str(self.package.uuid),
            'additional_costs': [{'additional_cost_uuid': str(self.ladder.uuid), 'quantity': 1}],
            'description': 'Mantenimiento de 8 camaras',
            'address': 'Calle 123',
            'contact_person': {
                'full_name': 'Juan Perez', 'document_type': 'CC', 'document_number': '123',
                'cargo': 'Gerente', 'email': 'juan@example.com', 'phone': '3001234567',
            },
        }
        response = self.client.post('/api/v1/orders/service-orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['request_package'])
        self.assertEqual(response.data['request_package']['package_name_snapshot'], '8 Camaras')

    def test_package_price_change_does_not_affect_existing_orders(self):
        """No modificar datos historicos: si el admin cambia el precio, ordenes viejas conservan su snapshot."""
        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data=self._service_detail_data(),
            package=self.package,
        )
        request_package = ServiceRequestPackage.objects.get(order=order)
        original_snapshot = request_package.package_price_snapshot

        ServicePackageCommands.update(self.package, base_price=Decimal('999999'))

        request_package.refresh_from_db()
        self.assertEqual(request_package.package_price_snapshot, original_snapshot)
        self.assertNotEqual(request_package.package_price_snapshot, Decimal('999999.00'))
