from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from renting.models import (
    Equipment, EquipmentVariant, RentalPeriod, RentalRequest, RentingCategory, EquipmentBlock,
)
from renting.services.commands import RentalRequestCommands

User = get_user_model()


@override_settings(ROOT_URLCONF='ecommerce.urls')
class EquipmentAvailabilityEndpointsTestCase(APITestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(email='vendor_endpoint@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Endpoint', slug='cat-endpoint-test')
        self.equipment = Equipment.objects.create(
            vendor=self.vendor, category=category, name='Equipo Endpoint', slug='equipo-endpoint-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=self.equipment, sku='ENDPOINT-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )
        self.period = RentalPeriod.objects.create(
            rental_request=RentalRequest.objects.create(
                user=self.vendor, equipment_variant=self.variant, status=RentalRequest.STATUS_PAID,
                start_date=date(2026, 8, 1), end_date=date(2026, 8, 5), contact_email=self.vendor.email,
            ),
            equipment_variant=self.variant,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
            status=RentalPeriod.STATUS_SCHEDULED,
        )

    def test_availability_endpoint_reports_unavailable_and_next_slot(self):
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/availability/'
        response = self.client.get(url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-02',
            'end_date': '2026-08-04',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['available'])
        self.assertEqual(response.data['next_available_date'], '2026-08-05')
        self.assertTrue(len(response.data['occupied_slots']) >= 1)

    def test_availability_endpoint_reports_available_outside_range(self):
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/availability/'
        response = self.client.get(url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-09-01',
            'end_date': '2026-09-05',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['available'])

    def test_check_availability_endpoint_still_backward_compatible(self):
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/check-availability/'
        response = self.client.get(url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-02',
            'end_date': '2026-08-04',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['available'])
        self.assertEqual(response.data['start_date'], '2026-08-02')
        self.assertEqual(response.data['end_date'], '2026-08-04')
        # Campos nuevos aditivos, no rompen el contrato original
        self.assertIn('next_available_date', response.data)
        self.assertIn('occupied_slots', response.data)

    def test_calendar_endpoint_marks_full_days(self):
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/calendar/'
        response = self.client.get(url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-01',
            'end_date': '2026-08-06',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        days_by_date = {d['date']: d for d in response.data['days']}
        self.assertEqual(days_by_date['2026-08-01']['status'], 'full')
        self.assertEqual(days_by_date['2026-08-05']['status'], 'available')  # checkout day, libre

    def test_timeline_endpoint_includes_all_statuses(self):
        cancelled_request = RentalRequest.objects.create(
            user=self.vendor, equipment_variant=self.variant, status=RentalRequest.STATUS_CANCELLED,
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 3), contact_email=self.vendor.email,
        )
        RentalPeriod.objects.create(
            rental_request=cancelled_request, equipment_variant=self.variant,
            start_date=date(2026, 7, 1), end_date=date(2026, 7, 3), status=RentalPeriod.STATUS_CANCELLED,
        )
        url = f'/api/v1/renting/equipment/{self.equipment.uuid}/timeline/'
        response = self.client.get(url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-07-01',
            'end_date': '2026-08-10',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {p['status'] for p in response.data['periods']}
        self.assertIn(RentalPeriod.STATUS_SCHEDULED, statuses)
        self.assertIn(RentalPeriod.STATUS_CANCELLED, statuses)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class RentalRequestAdminActionsTestCase(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='admin_actions_customer@example.com', password='testpass123')
        self.admin = User.objects.create_user(
            email='admin_actions_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        category = RentingCategory.objects.create(name='Cat Admin Actions', slug='cat-admin-actions-test')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Equipo Admin Actions', slug='equipo-admin-actions-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='ADMIN-ACTIONS-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )
        self.rental_request = RentalRequestCommands.create_request(self.customer, {
            'equipment_variant': self.variant,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=13),
            'quantity': 1,
            'rental_mode': 'days',
            'contact_full_name': 'Cliente Admin Actions',
            'contact_email': self.customer.email,
            'terms_accepted': True,
        })
        RentalRequestCommands.process_payment_selection(self.rental_request, RentalRequest.PAYMENT_COD)
        self.rental_request.refresh_from_db()

    def test_non_admin_cannot_approve(self):
        self.client.force_authenticate(user=self.customer)
        url = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_approve_creates_blocking_period(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}/approve/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RentalRequest.STATUS_CONFIRMED)
        self.assertEqual(
            RentalPeriod.objects.filter(rental_request=self.rental_request, status=RentalPeriod.STATUS_SCHEDULED).count(), 1,
        )

    def test_admin_reject_cancels_without_period(self):
        self.client.force_authenticate(user=self.admin)
        url = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}/reject/'
        response = self.client.post(url, {'reason': 'No cumple requisitos'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RentalRequest.STATUS_CANCELLED)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=self.rental_request).count(), 0)

    def test_admin_full_lifecycle_delivered_returned_and_release(self):
        self.client.force_authenticate(user=self.admin)
        base = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}'

        approve_response = self.client.post(f'{base}/approve/')
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)

        delivered_response = self.client.post(f'{base}/mark-delivered/')
        self.assertEqual(delivered_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delivered_response.data['status'], RentalRequest.STATUS_IN_OPERATION)

        returned_response = self.client.post(f'{base}/mark-returned/')
        self.assertEqual(returned_response.status_code, status.HTTP_200_OK)
        self.assertEqual(returned_response.data['status'], RentalRequest.STATUS_FINISHED)
        self.assertEqual(
            RentalPeriod.objects.get(rental_request=self.rental_request).status, RentalPeriod.STATUS_COMPLETED,
        )

    def test_admin_release_period_frees_agenda_without_cancelling_request(self):
        self.client.force_authenticate(user=self.admin)
        base = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}'
        self.client.post(f'{base}/approve/')

        response = self.client.post(f'{base}/release-period/', {'reason': 'Unidad danada'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], RentalRequest.STATUS_CONFIRMED)
        self.assertEqual(
            RentalPeriod.objects.filter(
                rental_request=self.rental_request,
                status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
            ).count(),
            0,
        )

    def test_admin_extends_confirmed_request(self):
        self.client.force_authenticate(user=self.admin)
        base = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}'
        self.client.post(f'{base}/approve/')

        new_end = (self.rental_request.end_date + timedelta(days=2)).isoformat()
        response = self.client.post(f'{base}/extend/', {'new_end_date': new_end, 'reason': 'Cliente pidio mas tiempo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['end_date'], new_end)

    def test_non_admin_cannot_extend(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/api/v1/renting/rental-requests/{self.rental_request.uuid}/extend/',
            {'new_end_date': (date.today() + timedelta(days=30)).isoformat()},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_registers_return_inspection_with_damage(self):
        self.client.force_authenticate(user=self.admin)
        base = f'/api/v1/renting/rental-requests/{self.rental_request.uuid}'
        self.client.post(f'{base}/approve/')
        self.client.post(f'{base}/mark-delivered/')
        self.client.post(f'{base}/mark-returned/')

        response = self.client.post(f'{base}/return-inspection/', {
            'has_damage': True, 'condition_notes': 'Carcasa rota',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['has_damage'])
        self.assertIsNotNone(response.data['resulting_block_uuid'])

        detail = self.client.get(base + '/')
        self.assertIsNotNone(detail.data['return_inspection'])
        self.assertTrue(detail.data['return_inspection']['has_damage'])

    def test_non_admin_cannot_register_inspection(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(
            f'/api/v1/renting/rental-requests/{self.rental_request.uuid}/return-inspection/', {'has_damage': False},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class EquipmentBlockEndpointsTestCase(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='block_customer@example.com', password='testpass123')
        self.admin = User.objects.create_user(
            email='block_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        category = RentingCategory.objects.create(name='Cat Block', slug='cat-block-test')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Equipo Block', slug='equipo-block-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='BLOCK-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def test_non_admin_cannot_list_or_create(self):
        self.client.force_authenticate(user=self.customer)
        response = self.client.get('/api/v1/renting/equipment-blocks/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post('/api/v1/renting/equipment-blocks/', {
            'equipment_variant': str(self.variant.uuid),
            'block_type': EquipmentBlock.TYPE_MAINTENANCE,
            'start_date': '2026-08-01',
            'end_date': '2026-08-05',
            'reason': 'Mantenimiento',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_creates_block_and_it_blocks_availability(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post('/api/v1/renting/equipment-blocks/', {
            'equipment_variant': str(self.variant.uuid),
            'block_type': EquipmentBlock.TYPE_MAINTENANCE,
            'start_date': '2026-08-01',
            'end_date': '2026-08-05',
            'reason': 'Mantenimiento preventivo',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], EquipmentBlock.STATUS_ACTIVE)
        self.assertEqual(EquipmentBlock.objects.filter(equipment_variant=self.variant).count(), 1)

        availability_url = f'/api/v1/renting/equipment/{self.variant.equipment.uuid}/availability/'
        availability_response = self.client.get(availability_url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-02',
            'end_date': '2026-08-04',
        })
        self.assertFalse(availability_response.data['available'])

    def test_admin_creates_block_does_not_leak_reason_on_public_calendar(self):
        self.client.force_authenticate(user=self.admin)
        self.client.post('/api/v1/renting/equipment-blocks/', {
            'equipment_variant': str(self.variant.uuid),
            'block_type': EquipmentBlock.TYPE_DAMAGE,
            'start_date': '2026-08-01',
            'end_date': '2026-08-05',
            'reason': 'Motor danado -- informacion sensible',
        })
        self.client.logout()

        calendar_url = f'/api/v1/renting/equipment/{self.variant.equipment.uuid}/calendar/'
        response = self.client.get(calendar_url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-01',
            'end_date': '2026-08-06',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('Motor danado', response.content.decode())
        full_days = [d for d in response.data['days'] if d['status'] == 'full']
        self.assertTrue(len(full_days) >= 1)

    def test_admin_release_block_frees_availability(self):
        self.client.force_authenticate(user=self.admin)
        create_response = self.client.post('/api/v1/renting/equipment-blocks/', {
            'equipment_variant': str(self.variant.uuid),
            'block_type': EquipmentBlock.TYPE_INVENTORY,
            'start_date': '2026-08-01',
            'end_date': '2026-08-05',
            'reason': 'Conteo anual',
        })
        block_uuid = create_response.data['uuid']

        release_response = self.client.post(
            f'/api/v1/renting/equipment-blocks/{block_uuid}/release/', {'reason': 'Conteo finalizado'},
        )
        self.assertEqual(release_response.status_code, status.HTTP_200_OK)
        self.assertEqual(release_response.data['status'], EquipmentBlock.STATUS_RELEASED)

        availability_url = f'/api/v1/renting/equipment/{self.variant.equipment.uuid}/availability/'
        availability_response = self.client.get(availability_url, {
            'variant': str(self.variant.uuid),
            'start_date': '2026-08-02',
            'end_date': '2026-08-04',
        })
        self.assertTrue(availability_response.data['available'])

    def test_release_is_idempotent(self):
        self.client.force_authenticate(user=self.admin)
        create_response = self.client.post('/api/v1/renting/equipment-blocks/', {
            'equipment_variant': str(self.variant.uuid),
            'block_type': EquipmentBlock.TYPE_OTHER,
            'start_date': '2026-08-01',
            'end_date': '2026-08-05',
            'reason': 'Prueba',
        })
        block_uuid = create_response.data['uuid']
        url = f'/api/v1/renting/equipment-blocks/{block_uuid}/release/'
        first = self.client.post(url, {'reason': 'primera liberacion'})
        second = self.client.post(url, {'reason': 'segunda liberacion'})
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data['status'], EquipmentBlock.STATUS_RELEASED)
        # No debe sobreescribir la primera liberacion (idempotente)
        self.assertEqual(second.data['release_reason'], 'primera liberacion')
