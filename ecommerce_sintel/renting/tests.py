import threading
from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import override_settings, TransactionTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from notifications.models import NotificationTemplate
from renting.models import (
    RentingCategory, RentalLabor, Equipment, EquipmentVariant, RentalPeriod, RentalRequest,
    RentalOperation, RentalOperationEvent, EquipmentBlock, EquipmentReturnInspection,
)
from renting.services.commands import (
    RentalRequestCommands, EquipmentBlockCommands, EquipmentReturnInspectionCommands,
)
from renting.services.operations import RentalOperationCommands
from operations.models import DispatcherProfile

User = get_user_model()


class RentalOperationLifecycleTestCase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email='rental-ops-customer@example.com', password='testpass123',
        )
        self.admin = User.objects.create_superuser(
            email='rental-ops-admin@example.com', password='testpass123',
        )
        driver_user = User.objects.create_user(
            email='rental-ops-driver@example.com', password='testpass123',
        )
        self.dispatcher = DispatcherProfile.objects.create(
            user=driver_user, vehicle_plate='ABC123', is_available=True,
        )
        category = RentingCategory.objects.create(name='Ops Category', slug='ops-category')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Ops Equipment', slug='ops-equipment',
        )
        variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='OPS-001', rental_price_per_day=Decimal('100000'), stock=1,
        )
        self.request = RentalRequest.objects.create(
            user=self.customer, equipment_variant=variant,
            status=RentalRequest.STATUS_PAID, priority=RentalRequest.PRIORITY_HIGH,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=6),
            quantity=1, grand_total=Decimal('300000'), location_address='Calle 1',
        )
        RentalPeriod.objects.create(
            rental_request=self.request, equipment_variant=variant,
            start_date=self.request.start_date, end_date=self.request.end_date,
            status=RentalPeriod.STATUS_SCHEDULED,
        )
        self.operation = RentalOperationCommands.ensure_for_request(self.request, self.admin)

    def test_operation_is_idempotent_and_starts_ready_for_scheduling(self):
        same = RentalOperationCommands.ensure_for_request(self.request, self.admin)
        self.assertEqual(same.pk, self.operation.pk)
        self.assertEqual(self.operation.status, RentalOperation.READY_FOR_SCHEDULING)
        self.assertEqual(
            RentalOperationEvent.objects.filter(
                operation=self.operation, event_type='OPERATION_CREATED'
            ).count(), 1,
        )

    def test_full_lifecycle_updates_rental_request_and_period(self):
        operation = RentalOperationCommands.schedule(
            self.operation,
            delivery_date=self.request.start_date, delivery_time=time(8, 0),
            pickup_date=self.request.end_date, pickup_time=time(16, 0),
            route='Ruta norte', actor=self.admin,
        )
        operation = RentalOperationCommands.assign_dispatcher(
            operation, dispatcher=self.dispatcher, actor=self.admin,
        )
        for target in (
            RentalOperation.READY_FOR_DELIVERY, RentalOperation.DELIVERED,
            RentalOperation.IN_OPERATION, RentalOperation.READY_FOR_PICKUP,
            RentalOperation.PICKED_UP, RentalOperation.RETURN_INSPECTION,
            RentalOperation.COMPLETED,
        ):
            operation = RentalOperationCommands.transition(operation, target, self.admin)

        self.request.refresh_from_db()
        period = self.request.periods.get()
        self.assertEqual(operation.status, RentalOperation.COMPLETED)
        self.assertEqual(self.request.status, RentalRequest.STATUS_FINISHED)
        self.assertEqual(period.status, RentalPeriod.STATUS_COMPLETED)

    def test_schedule_can_override_priority(self):
        self.assertEqual(self.operation.priority, RentalRequest.PRIORITY_HIGH)
        operation = RentalOperationCommands.schedule(
            self.operation,
            delivery_date=self.request.start_date, delivery_time=time(8, 0),
            pickup_date=self.request.end_date, pickup_time=time(16, 0),
            priority=RentalRequest.PRIORITY_LOW, actor=self.admin,
        )
        self.assertEqual(operation.priority, RentalRequest.PRIORITY_LOW)

    def test_can_pre_assign_dispatcher_before_scheduling(self):
        """Cross-domain audit FASE B (2026-08-14): assign_dispatcher() ya no
        exige programacion previa (mismo patron que
        ServiceOperationCommands.assign_technician(), FASE 2 de la migracion
        de autoridad de tecnico). Sin fecha, el transportista queda
        'pre-asignado' (status no avanza) hasta que schedule() completa la
        asignacion."""
        operation = RentalOperationCommands.assign_dispatcher(
            self.operation, dispatcher=self.dispatcher, actor=self.admin,
        )
        self.assertEqual(operation.status, RentalOperation.READY_FOR_SCHEDULING)
        self.assertEqual(operation.assigned_dispatcher_id, self.dispatcher.id)
        self.dispatcher.refresh_from_db()
        self.assertFalse(self.dispatcher.is_available)

        operation = RentalOperationCommands.schedule(
            operation,
            delivery_date=self.request.start_date, delivery_time=time(8, 0),
            pickup_date=self.request.end_date, pickup_time=time(16, 0),
            actor=self.admin,
        )
        self.assertEqual(operation.status, RentalOperation.TRANSPORT_ASSIGNED)
        self.assertEqual(operation.assigned_dispatcher_id, self.dispatcher.id)

    def test_cannot_assign_dispatcher_invalid_operation_status(self):
        operation = RentalOperationCommands.schedule(
            self.operation,
            delivery_date=self.request.start_date, delivery_time=time(8, 0),
            pickup_date=self.request.end_date, pickup_time=time(16, 0),
            actor=self.admin,
        )
        operation = RentalOperationCommands.assign_dispatcher(
            operation, dispatcher=self.dispatcher, actor=self.admin,
        )
        for target in (
            RentalOperation.READY_FOR_DELIVERY, RentalOperation.DELIVERED,
            RentalOperation.IN_OPERATION, RentalOperation.READY_FOR_PICKUP,
            RentalOperation.PICKED_UP, RentalOperation.RETURN_INSPECTION,
            RentalOperation.COMPLETED,
        ):
            operation = RentalOperationCommands.transition(operation, target, self.admin)
        with self.assertRaisesMessage(ValueError, 'programacion'):
            RentalOperationCommands.assign_dispatcher(
                operation, dispatcher=self.dispatcher, actor=self.admin,
            )

    def test_cannot_skip_transition(self):
        with self.assertRaisesMessage(ValueError, 'Transicion invalida'):
            RentalOperationCommands.transition(
                self.operation, RentalOperation.DELIVERED, self.admin,
            )

    def test_report_and_resolve_incident(self):
        operation = RentalOperationCommands.report_incident(
            self.operation, notes='Equipo con golpe en la carcasa.', actor=self.admin,
        )
        self.assertTrue(operation.has_incident)
        self.assertEqual(operation.incident_notes, 'Equipo con golpe en la carcasa.')
        self.assertTrue(
            RentalOperationEvent.objects.filter(
                operation=operation, event_type='INCIDENT_REPORTED'
            ).exists()
        )

        operation = RentalOperationCommands.resolve_incident(operation, actor=self.admin)
        self.assertFalse(operation.has_incident)
        self.assertEqual(operation.incident_notes, '')
        self.assertTrue(
            RentalOperationEvent.objects.filter(
                operation=operation, event_type='INCIDENT_RESOLVED'
            ).exists()
        )

    def test_resolve_incident_without_active_incident_raises(self):
        with self.assertRaisesMessage(ValueError, 'no tiene una incidencia activa'):
            RentalOperationCommands.resolve_incident(self.operation, actor=self.admin)

    def test_report_incident_on_completed_operation_raises(self):
        operation = RentalOperationCommands.schedule(
            self.operation,
            delivery_date=self.request.start_date, delivery_time=time(8, 0),
            pickup_date=self.request.end_date, pickup_time=time(16, 0),
            actor=self.admin,
        )
        operation = RentalOperationCommands.assign_dispatcher(
            operation, dispatcher=self.dispatcher, actor=self.admin,
        )
        for target in (
            RentalOperation.READY_FOR_DELIVERY, RentalOperation.DELIVERED,
            RentalOperation.IN_OPERATION, RentalOperation.READY_FOR_PICKUP,
            RentalOperation.PICKED_UP, RentalOperation.RETURN_INSPECTION,
            RentalOperation.COMPLETED,
        ):
            operation = RentalOperationCommands.transition(operation, target, self.admin)
        with self.assertRaisesMessage(ValueError, 'completada'):
            RentalOperationCommands.report_incident(operation, notes='Tarde', actor=self.admin)


class RentalOperationDashboardMetricsTestCase(TestCase):
    def setUp(self):
        from renting.services.operations import RentalOperationSelector
        self.selector = RentalOperationSelector
        self.customer = User.objects.create_user(
            email='rental-ops-dash-customer@example.com', password='testpass123',
        )
        category = RentingCategory.objects.create(name='Dash Category', slug='dash-category')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Dash Equipment', slug='dash-equipment',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='DASH-001', rental_price_per_day=Decimal('50000'), stock=5,
        )

    def _make_operation(self, *, status, delivery_date=None, pickup_date=None, has_incident=False):
        request = RentalRequest.objects.create(
            user=self.customer, equipment_variant=self.variant,
            status=RentalRequest.STATUS_PAID,
            start_date=date.today(), end_date=date.today() + timedelta(days=3),
            quantity=1, grand_total=Decimal('150000'), location_address='Calle 1',
        )
        return RentalOperation.objects.create(
            rental_request=request, status=status,
            delivery_date=delivery_date, pickup_date=pickup_date, has_incident=has_incident,
        )

    def test_dashboard_metrics_counts_each_bucket(self):
        today = date.today()
        self._make_operation(status=RentalOperation.READY_FOR_SCHEDULING)
        self._make_operation(status=RentalOperation.SCHEDULED)
        self._make_operation(
            status=RentalOperation.TRANSPORT_ASSIGNED, delivery_date=today,
        )
        self._make_operation(
            status=RentalOperation.IN_OPERATION, pickup_date=today,
        )
        self._make_operation(
            status=RentalOperation.IN_OPERATION,
            pickup_date=today + timedelta(days=2),
        )
        self._make_operation(
            status=RentalOperation.READY_FOR_DELIVERY,
            delivery_date=today - timedelta(days=1),
        )
        self._make_operation(status=RentalOperation.IN_OPERATION, has_incident=True)

        metrics = self.selector.dashboard_metrics()
        self.assertEqual(metrics['pending_scheduling'], 1)
        self.assertEqual(metrics['pending_dispatcher'], 1)
        self.assertEqual(metrics['deliveries_today'], 1)
        self.assertEqual(metrics['pickups_today'], 1)
        self.assertEqual(metrics['in_operation'], 3)
        self.assertEqual(metrics['upcoming_returns'], 2)
        self.assertEqual(metrics['delayed'], 1)
        self.assertEqual(metrics['incidents'], 1)


@override_settings(ROOT_URLCONF='ecommerce.urls')
class RentalOperationApiEndpointsTestCase(APITestCase):
    """
    Cubre el flujo HTTP completo del ViewSet, no solo los comandos. Un metodo de
    accion llamado 'dispatch' sobreescribia silenciosamente View.dispatch() (el
    metodo interno que DRF usa para enrutar TODA solicitud): cualquier request al
    ViewSet, incluido dashboard/list/schedule, terminaba ejecutando la logica de
    esa accion en vez de la solicitada. Los tests a nivel de comando no lo detectaban
    porque invocan RentalOperationCommands directamente, sin pasar por el ViewSet.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='rental-ops-api-admin@example.com', password='testpass123',
        )
        self.customer = User.objects.create_user(
            email='rental-ops-api-customer@example.com', password='testpass123',
        )
        driver_user = User.objects.create_user(
            email='rental-ops-api-driver@example.com', password='testpass123',
        )
        self.dispatcher = DispatcherProfile.objects.create(
            user=driver_user, vehicle_plate='XYZ987', is_available=True,
        )
        category = RentingCategory.objects.create(name='Api Category', slug='api-category')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Api Equipment', slug='api-equipment',
        )
        variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='API-001', rental_price_per_day=Decimal('100000'), stock=1,
        )
        self.request = RentalRequest.objects.create(
            user=self.customer, equipment_variant=variant,
            status=RentalRequest.STATUS_PAID,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=6),
            quantity=1, grand_total=Decimal('300000'), location_address='Calle 1',
        )
        self.operation = RentalOperationCommands.ensure_for_request(self.request, self.admin)
        self.client.force_authenticate(user=self.admin)

    def test_list_returns_operation(self):
        response = self.client.get('/api/v1/renting/operations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)

    def test_dashboard_returns_metrics_not_a_transition(self):
        response = self.client.get('/api/v1/renting/operations/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['pending_scheduling'], 1)
        self.operation.refresh_from_db()
        self.assertEqual(self.operation.status, RentalOperation.READY_FOR_SCHEDULING)

    def test_full_http_lifecycle_including_dispatch_action(self):
        detail_url = f'/api/v1/renting/operations/{self.operation.uuid}/'

        response = self.client.post(f'{detail_url}schedule/', {
            'delivery_date': str(self.request.start_date), 'delivery_time': '08:00',
            'pickup_date': str(self.request.end_date), 'pickup_time': '16:00',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], RentalOperation.SCHEDULED)

        response = self.client.post(f'{detail_url}assign-dispatcher/', {
            'dispatcher_uuid': str(self.dispatcher.uuid),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], RentalOperation.TRANSPORT_ASSIGNED)

        for endpoint, expected_status in [
            ('dispatch', RentalOperation.READY_FOR_DELIVERY),
            ('deliver', RentalOperation.DELIVERED),
            ('start-operation', RentalOperation.IN_OPERATION),
            ('ready-pickup', RentalOperation.READY_FOR_PICKUP),
            ('pickup', RentalOperation.PICKED_UP),
            ('inspect-return', RentalOperation.RETURN_INSPECTION),
            ('complete', RentalOperation.COMPLETED),
        ]:
            response = self.client.post(f'{detail_url}{endpoint}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK, (endpoint, response.data))
            self.assertEqual(response.data['status'], expected_status)

    def test_report_and_resolve_incident_via_api(self):
        detail_url = f'/api/v1/renting/operations/{self.operation.uuid}/'
        response = self.client.post(f'{detail_url}report-incident/', {'notes': 'Acceso restringido en zona.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data['has_incident'])

        response = self.client.post(f'{detail_url}resolve-incident/')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data['has_incident'])


@override_settings(ROOT_URLCONF='ecommerce.urls')
class RentingPublicCatalogPermissionsTestCase(APITestCase):
    """
    Cubre el gap detectado el 2026-07-03: RentingCategoryViewSet, RentingBrandViewSet y
    RentalLaborViewSet no declaraban permission_classes -- caian al default del proyecto
    (IsAuthenticated), contradiciendo sus propios docstrings de "lectura publica". Ademas,
    RentingCategoryViewSet/RentalLaborViewSet usaban los selectores "_for_admin" (sin filtro
    is_active), exponiendo categorias/mano de obra inactivas a cualquier usuario anonimo.
    """

    def setUp(self):
        self.active_category = RentingCategory.objects.create(
            name='Categoria Activa', slug='categoria-activa', is_active=True,
        )
        self.inactive_category = RentingCategory.objects.create(
            name='Categoria Inactiva', slug='categoria-inactiva', is_active=False,
        )
        self.active_labor = RentalLabor.objects.create(
            name='Operador Activo', price_per_hour=Decimal('50000.00'), is_active=True,
        )
        self.inactive_labor = RentalLabor.objects.create(
            name='Operador Inactivo', price_per_hour=Decimal('50000.00'), is_active=False,
        )

    def test_categories_list_is_public(self):
        response = self.client.get('/api/v1/renting/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_categories_list_excludes_inactive(self):
        response = self.client.get('/api/v1/renting/categories/')
        names = [c['name'] for c in response.data['results']] if 'results' in response.data else [c['name'] for c in response.data]
        self.assertIn('Categoria Activa', names)
        self.assertNotIn('Categoria Inactiva', names)

    def test_inactive_category_detail_not_found(self):
        response = self.client.get(f'/api/v1/renting/categories/{self.inactive_category.uuid}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_brands_list_is_public(self):
        response = self.client.get('/api/v1/renting/brands/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_labor_list_is_public(self):
        response = self.client.get('/api/v1/renting/labor/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_labor_list_excludes_inactive(self):
        response = self.client.get('/api/v1/renting/labor/')
        names = [l['name'] for l in response.data['results']] if 'results' in response.data else [l['name'] for l in response.data]
        self.assertIn('Operador Activo', names)
        self.assertNotIn('Operador Inactivo', names)


class RentalRequestConfirmPaymentOverbookingTestCase(TransactionTestCase):
    """
    Cubre la Fase 1 del Plan Maestro de Renting (2026-07-07): pending_payment ya NO
    bloquea el calendario, asi que create_request() dejo de tomar el lock de
    concurrencia (dos solicitudes solapadas ahora se crean ambas sin problema). El
    lock se movio a confirm_payment(), el punto autoritativo donde efectivamente se
    crea el RentalPeriod. Reemplaza a la vieja RentalRequestOverbookingTestCase, que
    probaba el lock en create_request() (ya no existe alli).
    """

    def setUp(self):
        self.user_a = User.objects.create_user(email='rental_race_a@example.com', password='testpass123')
        self.user_b = User.objects.create_user(email='rental_race_b@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Race', slug='cat-race-test')
        equipment = Equipment.objects.create(
            vendor=self.user_a, category=category, name='Equipo Race', slug='equipo-race-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='RACE-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def _create_request(self, user):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        return RentalRequestCommands.create_request(user, {
            'equipment_variant': self.variant,
            'start_date': start,
            'end_date': end,
            'quantity': 1,
            'rental_mode': 'days',
            'contact_full_name': f'Test {user.email}',
            'contact_email': user.email,
            'terms_accepted': True,
        })

    def test_both_overlapping_requests_are_created_without_conflict(self):
        # pending_payment nunca bloquea agenda: ambas creaciones deben tener exito.
        request_a = self._create_request(self.user_a)
        request_b = self._create_request(self.user_b)
        self.assertEqual(request_a.status, RentalRequest.STATUS_PENDING_PAYMENT)
        self.assertEqual(request_b.status, RentalRequest.STATUS_PENDING_PAYMENT)
        self.assertEqual(RentalPeriod.objects.count(), 0)

    def test_concurrent_confirm_payment_for_single_unit_do_not_overbook(self):
        request_a = self._create_request(self.user_a)
        request_b = self._create_request(self.user_b)

        outcomes = {}

        def worker(rental_request, key):
            try:
                RentalRequestCommands.confirm_payment(rental_request)
                outcomes[key] = 'done'
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=(request_a, 'a'))
        t2 = threading.Thread(target=worker, args=(request_b, 'b'))
        t1.start()
        t2.start()
        t1.join(timeout=15)
        t2.join(timeout=15)

        request_a.refresh_from_db()
        request_b.refresh_from_db()

        statuses = sorted([request_a.status, request_b.status])
        self.assertEqual(
            statuses, sorted([RentalRequest.STATUS_PAID, RentalRequest.STATUS_PAYMENT_CONFLICT])
        )

        conflicted = request_a if request_a.status == RentalRequest.STATUS_PAYMENT_CONFLICT else request_b
        self.assertTrue(conflicted.refund_required)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=conflicted).count(), 0)

        self.assertEqual(
            RentalPeriod.objects.filter(
                equipment_variant=self.variant,
                status__in=[RentalPeriod.STATUS_SCHEDULED, RentalPeriod.STATUS_ACTIVE],
            ).count(),
            1,
        )


class RentalRequestLifecycleTestCase(TestCase):
    """Cubre las nuevas transiciones de estado de la Fase 1 del Plan Maestro de Renting."""

    def setUp(self):
        self.user_a = User.objects.create_user(email='rental_lifecycle_a@example.com', password='testpass123')
        self.user_b = User.objects.create_user(email='rental_lifecycle_b@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Lifecycle', slug='cat-lifecycle-test')
        equipment = Equipment.objects.create(
            vendor=self.user_a, category=category, name='Equipo Lifecycle', slug='equipo-lifecycle-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='LIFECYCLE-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def _create_and_select_cod(self, user):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        rr = RentalRequestCommands.create_request(user, {
            'equipment_variant': self.variant,
            'start_date': start, 'end_date': end, 'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': f'Test {user.email}', 'contact_email': user.email, 'terms_accepted': True,
        })
        RentalRequestCommands.process_payment_selection(rr, RentalRequest.PAYMENT_COD)
        rr.refresh_from_db()
        return rr

    def test_process_payment_selection_cod_goes_to_pending_validation_without_period(self):
        rr = self._create_and_select_cod(self.user_a)
        self.assertEqual(rr.status, RentalRequest.STATUS_PENDING_VALIDATION)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=rr).count(), 0)

    def test_approve_manual_validation_conflict_flags_second_request(self):
        rr_a = self._create_and_select_cod(self.user_a)
        rr_b = self._create_and_select_cod(self.user_b)

        RentalRequestCommands.approve_manual_validation(rr_a)
        RentalRequestCommands.approve_manual_validation(rr_b)

        rr_a.refresh_from_db()
        rr_b.refresh_from_db()
        self.assertEqual(rr_a.status, RentalRequest.STATUS_CONFIRMED)
        self.assertEqual(rr_b.status, RentalRequest.STATUS_PAYMENT_CONFLICT)
        self.assertFalse(rr_b.refund_required)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=rr_b).count(), 0)

    def test_reject_request_cancels_without_period(self):
        rr = self._create_and_select_cod(self.user_a)
        RentalRequestCommands.reject_request(rr, reason='Cliente no cumple requisitos')
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_CANCELLED)
        self.assertIn('Cliente no cumple requisitos', rr.admin_notes)
        self.assertEqual(RentalPeriod.objects.filter(rental_request=rr).count(), 0)

    def test_activate_and_complete_period_idempotent(self):
        rr = self._create_and_select_cod(self.user_a)
        RentalRequestCommands.approve_manual_validation(rr)
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_CONFIRMED)

        RentalRequestCommands.activate_period(rr)
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_IN_OPERATION)
        self.assertEqual(RentalPeriod.objects.get(rental_request=rr).status, RentalPeriod.STATUS_ACTIVE)

        RentalRequestCommands.activate_period(rr)  # idempotente
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_IN_OPERATION)

        RentalRequestCommands.complete_period(rr)
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_FINISHED)
        self.assertEqual(RentalPeriod.objects.get(rental_request=rr).status, RentalPeriod.STATUS_COMPLETED)

        RentalRequestCommands.complete_period(rr)  # idempotente
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_FINISHED)

    def test_approve_manual_validation_notifies_with_ticket_number(self):
        """
        Cubre el hallazgo de 2026-07-07: ensure_ticket_for_rental() devolvia el ticket
        pero el valor se descartaba, asi que el correo de confirmacion nunca podia
        resaltar el numero de ticket de servicio. Tambien confirma que la plantilla
        'rental_cod_confirmed' quedo sembrada en BD (migracion 0014) y activa.
        """
        self.assertTrue(
            NotificationTemplate.objects.filter(slug='rental_cod_confirmed', is_active=True).exists()
        )
        rr = self._create_and_select_cod(self.user_a)

        with patch('notifications.services.commands.NotificationCommands.dispatch_notification') as mock_dispatch:
            with self.captureOnCommitCallbacks(execute=True):
                RentalRequestCommands.approve_manual_validation(rr)

        from operations.models import OperationTicket
        ticket = OperationTicket.objects.get(source_rental_request=rr)

        # ensure_ticket_for_rental() tambien dispara su propia notificacion
        # ('operation_created'), asi que se busca especificamente la llamada de
        # confirmacion de renta entre todas las que dispatch_notification recibio.
        matching = [
            call.kwargs for call in mock_dispatch.call_args_list
            if call.kwargs.get('template_slug') == 'rental_cod_confirmed'
        ]
        self.assertEqual(len(matching), 1)
        context = matching[0]['context']
        self.assertEqual(context['ticket_number'], ticket.ticket_number)
        self.assertEqual(context['start_date'], str(rr.start_date))
        self.assertEqual(context['end_date'], str(rr.end_date))


class RentalRequestExtendPeriodTestCase(TestCase):
    """Roadmap item: extension de renta (admin-only, sin cobro automatico)."""

    def setUp(self):
        self.user = User.objects.create_user(email='extend_user@example.com', password='testpass123')
        self.admin = User.objects.create_user(
            email='extend_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        category = RentingCategory.objects.create(name='Cat Extend', slug='cat-extend-test')
        equipment = Equipment.objects.create(
            vendor=self.user, category=category, name='Equipo Extend', slug='equipo-extend-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='EXTEND-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def _confirmed_request(self, start_date, end_date):
        rr = RentalRequestCommands.create_request(self.user, {
            'equipment_variant': self.variant,
            'start_date': start_date, 'end_date': end_date,
            'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': 'Cliente Extend', 'contact_email': self.user.email,
            'terms_accepted': True,
        })
        RentalRequestCommands.process_payment_selection(rr, RentalRequest.PAYMENT_COD)
        rr.refresh_from_db()
        RentalRequestCommands.approve_manual_validation(rr)
        rr.refresh_from_db()
        return rr

    def test_extend_recalculates_total_and_period(self):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        rr = self._confirmed_request(start, end)
        original_total = rr.grand_total

        new_end = end + timedelta(days=2)
        extended = RentalRequestCommands.extend_period(rr, new_end, admin_user=self.admin, reason='Cliente pidio mas dias')

        self.assertEqual(extended.end_date, new_end)
        self.assertEqual(extended.total_rental_days, (new_end - start).days)
        self.assertGreater(extended.grand_total, original_total)
        period = RentalPeriod.objects.get(rental_request=rr, status=RentalPeriod.STATUS_SCHEDULED)
        self.assertEqual(period.end_date, new_end)

    def test_extend_rejects_when_conflicting_request_exists(self):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        rr = self._confirmed_request(start, end)

        blocker = EquipmentVariant.objects.get(pk=self.variant.pk)
        RentalPeriod.objects.create(
            rental_request=RentalRequest.objects.create(
                user=self.user, equipment_variant=blocker, status=RentalRequest.STATUS_PAID,
                start_date=end, end_date=end + timedelta(days=5), contact_email=self.user.email,
            ),
            equipment_variant=blocker, start_date=end, end_date=end + timedelta(days=5),
            status=RentalPeriod.STATUS_SCHEDULED,
        )

        with self.assertRaises(ValueError):
            RentalRequestCommands.extend_period(rr, end + timedelta(days=2), admin_user=self.admin)

    def test_extend_rejects_non_extendable_status(self):
        rr = RentalRequestCommands.create_request(self.user, {
            'equipment_variant': self.variant,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=13),
            'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': 'Cliente Extend', 'contact_email': self.user.email,
            'terms_accepted': True,
        })
        with self.assertRaises(ValueError):
            RentalRequestCommands.extend_period(rr, rr.end_date + timedelta(days=2), admin_user=self.admin)

    def test_extend_rejects_earlier_or_equal_end_date(self):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        rr = self._confirmed_request(start, end)
        with self.assertRaises(ValueError):
            RentalRequestCommands.extend_period(rr, end, admin_user=self.admin)


class EquipmentBlockCommandsTestCase(TestCase):
    """Bloqueo manual de equipos por mantenimiento/daño/inventario (no atado a RentalRequest)."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email='block_cmd_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        category = RentingCategory.objects.create(name='Cat Block Cmd', slug='cat-block-cmd-test')
        equipment = Equipment.objects.create(
            vendor=self.admin, category=category, name='Equipo Block Cmd', slug='equipo-block-cmd-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='BLOCK-CMD-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def test_create_block_records_creator_and_reason(self):
        block = EquipmentBlockCommands.create_block(
            equipment_variant=self.variant, block_type=EquipmentBlock.TYPE_MAINTENANCE,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
            reason='Revision programada', admin_user=self.admin,
        )
        self.assertEqual(block.status, EquipmentBlock.STATUS_ACTIVE)
        self.assertEqual(block.created_by, self.admin)
        self.assertEqual(block.reason, 'Revision programada')

    def test_create_block_rejects_end_before_start(self):
        with self.assertRaises(ValueError):
            EquipmentBlockCommands.create_block(
                equipment_variant=self.variant, block_type=EquipmentBlock.TYPE_DAMAGE,
                start_date=date(2026, 8, 5), end_date=date(2026, 8, 1),
                reason='Fecha invalida', admin_user=self.admin,
            )

    def test_create_block_rejects_zero_quantity(self):
        with self.assertRaises(ValueError):
            EquipmentBlockCommands.create_block(
                equipment_variant=self.variant, block_type=EquipmentBlock.TYPE_DAMAGE,
                start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
                reason='Cantidad invalida', quantity=0, admin_user=self.admin,
            )

    def test_release_block_records_releaser_and_timestamp(self):
        block = EquipmentBlockCommands.create_block(
            equipment_variant=self.variant, block_type=EquipmentBlock.TYPE_INVENTORY,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
            reason='Conteo anual', admin_user=self.admin,
        )
        released = EquipmentBlockCommands.release_block(block, admin_user=self.admin, reason='Conteo finalizado')
        self.assertEqual(released.status, EquipmentBlock.STATUS_RELEASED)
        self.assertEqual(released.released_by, self.admin)
        self.assertEqual(released.release_reason, 'Conteo finalizado')
        self.assertIsNotNone(released.released_at)

    def test_release_block_is_idempotent(self):
        block = EquipmentBlockCommands.create_block(
            equipment_variant=self.variant, block_type=EquipmentBlock.TYPE_OTHER,
            start_date=date(2026, 8, 1), end_date=date(2026, 8, 5),
            reason='Prueba', admin_user=self.admin,
        )
        first = EquipmentBlockCommands.release_block(block, admin_user=self.admin, reason='primera')
        second = EquipmentBlockCommands.release_block(block, admin_user=self.admin, reason='segunda')
        self.assertEqual(first.release_reason, 'primera')
        self.assertEqual(second.release_reason, 'primera')


class ExpireAbandonedPendingPaymentTaskTestCase(TestCase):
    """Roadmap item: limpieza periodica de RentalRequest abandonadas en pending_payment."""

    def setUp(self):
        self.user = User.objects.create_user(email='expire_task_user@example.com', password='testpass123')
        category = RentingCategory.objects.create(name='Cat Expire', slug='cat-expire-test')
        equipment = Equipment.objects.create(
            vendor=self.user, category=category, name='Equipo Expire', slug='equipo-expire-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='EXPIRE-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def _create_pending_payment(self, hours_old):
        rr = RentalRequestCommands.create_request(self.user, {
            'equipment_variant': self.variant,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=13),
            'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': 'Cliente Expire', 'contact_email': self.user.email,
            'terms_accepted': True,
        })
        self.assertEqual(rr.status, RentalRequest.STATUS_PENDING_PAYMENT)
        backdated = timezone.now() - timedelta(hours=hours_old)
        RentalRequest.objects.filter(pk=rr.pk).update(created_at=backdated)
        rr.refresh_from_db()
        return rr

    def test_cancels_requests_older_than_threshold(self):
        from renting.tasks import expire_abandoned_pending_payment_requests

        old_rr = self._create_pending_payment(hours_old=49)
        expire_abandoned_pending_payment_requests()
        old_rr.refresh_from_db()
        self.assertEqual(old_rr.status, RentalRequest.STATUS_CANCELLED)

    def test_does_not_touch_recent_requests(self):
        from renting.tasks import expire_abandoned_pending_payment_requests

        recent_rr = self._create_pending_payment(hours_old=1)
        expire_abandoned_pending_payment_requests()
        recent_rr.refresh_from_db()
        self.assertEqual(recent_rr.status, RentalRequest.STATUS_PENDING_PAYMENT)

    def test_does_not_touch_resolved_statuses(self):
        from renting.tasks import expire_abandoned_pending_payment_requests

        rr = self._create_pending_payment(hours_old=49)
        rr.status = RentalRequest.STATUS_PENDING_VALIDATION
        rr.save(update_fields=['status'])

        expire_abandoned_pending_payment_requests()
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_PENDING_VALIDATION)

    def test_task_is_idempotent(self):
        from renting.tasks import expire_abandoned_pending_payment_requests

        old_rr = self._create_pending_payment(hours_old=49)
        expire_abandoned_pending_payment_requests()
        expire_abandoned_pending_payment_requests()
        old_rr.refresh_from_db()
        self.assertEqual(old_rr.status, RentalRequest.STATUS_CANCELLED)


class EquipmentReturnInspectionCommandsTestCase(TestCase):
    """Roadmap item: inspeccion de devolucion (opcional/aparte, no gatea mark-returned)."""

    def setUp(self):
        self.user = User.objects.create_user(email='inspection_user@example.com', password='testpass123')
        self.admin = User.objects.create_user(
            email='inspection_admin@example.com', password='testpass123',
            is_staff=True, is_superuser=True,
        )
        category = RentingCategory.objects.create(name='Cat Inspection', slug='cat-inspection-test')
        equipment = Equipment.objects.create(
            vendor=self.user, category=category, name='Equipo Inspection', slug='equipo-inspection-test',
        )
        self.variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='INSPECTION-SKU-1', rental_price_per_day=Decimal('100000.00'), stock=1,
        )

    def _finished_request(self):
        start = date.today() + timedelta(days=10)
        end = start + timedelta(days=3)
        rr = RentalRequestCommands.create_request(self.user, {
            'equipment_variant': self.variant,
            'start_date': start, 'end_date': end, 'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': 'Cliente Inspection', 'contact_email': self.user.email,
            'terms_accepted': True,
        })
        RentalRequestCommands.process_payment_selection(rr, RentalRequest.PAYMENT_COD)
        rr.refresh_from_db()
        RentalRequestCommands.approve_manual_validation(rr)
        RentalRequestCommands.activate_period(rr)
        RentalRequestCommands.complete_period(rr)
        rr.refresh_from_db()
        self.assertEqual(rr.status, RentalRequest.STATUS_FINISHED)
        return rr

    def test_create_inspection_without_damage(self):
        rr = self._finished_request()
        inspection = EquipmentReturnInspectionCommands.create_inspection(
            rr, has_damage=False, condition_notes='Equipo en buen estado', admin_user=self.admin,
        )
        self.assertFalse(inspection.has_damage)
        self.assertIsNone(inspection.resulting_block)
        self.assertEqual(inspection.inspected_by, self.admin)

    def test_create_inspection_with_damage_auto_creates_block(self):
        rr = self._finished_request()
        inspection = EquipmentReturnInspectionCommands.create_inspection(
            rr, has_damage=True, condition_notes='Carcasa rota', admin_user=self.admin,
        )
        self.assertTrue(inspection.has_damage)
        self.assertIsNotNone(inspection.resulting_block)
        self.assertEqual(inspection.resulting_block.block_type, EquipmentBlock.TYPE_DAMAGE)
        self.assertEqual(inspection.resulting_block.status, EquipmentBlock.STATUS_ACTIVE)
        self.assertEqual(inspection.resulting_block.equipment_variant, self.variant)

    def test_rejects_when_request_not_finished(self):
        rr = RentalRequestCommands.create_request(self.user, {
            'equipment_variant': self.variant,
            'start_date': date.today() + timedelta(days=10),
            'end_date': date.today() + timedelta(days=13),
            'quantity': 1, 'rental_mode': 'days',
            'contact_full_name': 'Cliente Inspection', 'contact_email': self.user.email,
            'terms_accepted': True,
        })
        with self.assertRaises(ValueError):
            EquipmentReturnInspectionCommands.create_inspection(rr, has_damage=False, admin_user=self.admin)

    def test_rejects_duplicate_inspection(self):
        rr = self._finished_request()
        EquipmentReturnInspectionCommands.create_inspection(rr, has_damage=False, admin_user=self.admin)
        with self.assertRaises(ValueError):
            EquipmentReturnInspectionCommands.create_inspection(rr, has_damage=False, admin_user=self.admin)

    def test_mark_returned_not_gated_by_inspection(self):
        """No gatea mark-returned/complete_period -- ya se completo sin inspeccion previa."""
        rr = self._finished_request()
        self.assertFalse(EquipmentReturnInspection.objects.filter(rental_request=rr).exists())
        self.assertEqual(rr.status, RentalRequest.STATUS_FINISHED)
