"""
Tests del FSM de ServiceOperation (services/operations.py::ServiceOperationCommands).
Escrito como pre-requisito de la unificacion BaseOperationFSM (DUP-B2/DT-L8): antes de
este archivo, ServiceOperation.transition()/close() no tenian ninguna cobertura directa
(solo se ejercitaba ensure_for_order/try_auto_assign_via_engine via
tests_technician_availability.py) -- espeja la profundidad de
renting/tests.py::RentalOperationLifecycleTestCase para poder refactorizar con red de
seguridad real, no solo un build check.
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from orders.models import Order
from technical_services.models import ServiceOperation, ServiceOperationEvent
from technical_services.services.operations import ServiceOperationCommands

User = get_user_model()


class ServiceOperationLifecycleTestCase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            email='service-ops-customer@example.com', password='testpass123',
        )
        self.admin = User.objects.create_superuser(
            email='service-ops-admin@example.com', password='testpass123',
        )
        self.technician = User.objects.create_user(
            email='service-ops-tech@example.com', password='testpass123',
        )
        UserProfile.objects.create(user=self.technician)  # default user_type=TECHNICIAN
        self.order = Order.objects.create(user=self.customer, total_amount=Decimal('150000'))
        self.operation = ServiceOperationCommands.ensure_for_order(self.order, self.admin)

    def test_operation_is_idempotent_and_starts_ready_for_planning(self):
        same = ServiceOperationCommands.ensure_for_order(self.order, self.admin)
        self.assertEqual(same.pk, self.operation.pk)
        self.assertEqual(self.operation.status, ServiceOperation.READY_FOR_PLANNING)
        self.assertEqual(
            ServiceOperationEvent.objects.filter(
                operation=self.operation, event_type='OPERATION_CREATED',
            ).count(), 1,
        )

    def test_full_lifecycle_sets_timestamps_and_closes(self):
        operation = ServiceOperationCommands.plan(
            self.operation,
            scheduled_date=date.today() + timedelta(days=1), scheduled_time=time(9, 0),
            actor=self.admin,
        )
        operation = ServiceOperationCommands.assign_technician(
            operation, technician=self.technician, actor=self.admin,
        )
        operation = ServiceOperationCommands.notify_client(operation, actor=self.admin)
        self.assertIsNone(operation.arrived_at)
        self.assertIsNone(operation.started_at)
        self.assertIsNone(operation.completed_at)

        for target in (
            ServiceOperation.READY_TO_VISIT, ServiceOperation.ON_THE_WAY,
            ServiceOperation.ARRIVED, ServiceOperation.IN_PROGRESS, ServiceOperation.COMPLETED,
        ):
            operation = ServiceOperationCommands.transition(operation, target, self.admin)

        self.assertEqual(operation.status, ServiceOperation.COMPLETED)
        self.assertIsNotNone(operation.arrived_at)
        self.assertIsNotNone(operation.started_at)
        self.assertIsNotNone(operation.completed_at)

        operation = ServiceOperationCommands.close(operation, actor=self.admin)
        self.assertEqual(operation.status, ServiceOperation.CLOSED)
        self.assertEqual(operation.closure_status, ServiceOperation.CLOSURE_CONFIRMED)

    def test_can_pre_assign_technician_before_planning(self):
        """Migracion 'autoridad unica de tecnico' FASE 2 (2026-08-14): assign_technician()
        ya no exige fecha/hora previa (preserva el flujo legacy de
        TechnicianAssignmentBoard.vue, que asigna tecnico sin planeacion previa). Sin
        fecha, el tecnico queda 'pre-asignado' (status no avanza, sin slot reservado)
        hasta que plan() completa la reserva real."""
        operation = ServiceOperationCommands.assign_technician(
            self.operation, technician=self.technician, actor=self.admin,
        )
        self.assertEqual(operation.status, ServiceOperation.READY_FOR_PLANNING)
        self.assertEqual(operation.technician_id, self.technician.id)
        self.assertIsNone(operation.availability_slot_id)

        operation = ServiceOperationCommands.plan(
            operation,
            scheduled_date=date.today() + timedelta(days=1), scheduled_time=time(9, 0),
            actor=self.admin,
        )
        self.assertEqual(operation.status, ServiceOperation.TECHNICIAN_ASSIGNED)
        self.assertEqual(operation.technician_id, self.technician.id)
        self.assertIsNotNone(operation.availability_slot_id)

    def test_unassign_before_planning_reverts_to_ready_for_planning(self):
        operation = ServiceOperationCommands.assign_technician(
            self.operation, technician=self.technician, actor=self.admin,
        )
        operation = ServiceOperationCommands.unassign_technician(operation, actor=self.admin)
        self.assertEqual(operation.status, ServiceOperation.READY_FOR_PLANNING)
        self.assertIsNone(operation.technician_id)
        self.assertIsNone(operation.availability_slot_id)

    def test_cannot_assign_invalid_operation_status(self):
        operation = ServiceOperationCommands.plan(
            self.operation,
            scheduled_date=date.today() + timedelta(days=1), scheduled_time=time(9, 0),
            actor=self.admin,
        )
        operation = ServiceOperationCommands.assign_technician(
            operation, technician=self.technician, actor=self.admin,
        )
        operation = ServiceOperationCommands.notify_client(operation, actor=self.admin)
        for target in (
            ServiceOperation.READY_TO_VISIT, ServiceOperation.ON_THE_WAY,
            ServiceOperation.ARRIVED, ServiceOperation.IN_PROGRESS, ServiceOperation.COMPLETED,
        ):
            operation = ServiceOperationCommands.transition(operation, target, self.admin)
        operation = ServiceOperationCommands.close(operation, actor=self.admin)
        with self.assertRaisesMessage(ValueError, 'planeacion'):
            ServiceOperationCommands.assign_technician(
                operation, technician=self.technician, actor=self.admin,
            )

    def test_cannot_skip_transition(self):
        with self.assertRaisesMessage(ValueError, 'Transicion invalida'):
            ServiceOperationCommands.transition(
                self.operation, ServiceOperation.ARRIVED, self.admin,
            )

    def test_cannot_close_before_completed(self):
        with self.assertRaisesMessage(ValueError, 'completada'):
            ServiceOperationCommands.close(self.operation, actor=self.admin)

    def test_report_and_resolve_incident(self):
        operation = ServiceOperationCommands.report_incident(
            self.operation, notes='Cliente ausente en la visita.', actor=self.admin,
        )
        self.assertTrue(operation.has_incident)
        self.assertEqual(operation.incident_notes, 'Cliente ausente en la visita.')
        self.assertTrue(
            ServiceOperationEvent.objects.filter(
                operation=operation, event_type='INCIDENT_REPORTED',
            ).exists()
        )

        operation = ServiceOperationCommands.resolve_incident(operation, actor=self.admin)
        self.assertFalse(operation.has_incident)
        self.assertEqual(operation.incident_notes, '')
        self.assertTrue(
            ServiceOperationEvent.objects.filter(
                operation=operation, event_type='INCIDENT_RESOLVED',
            ).exists()
        )

    def test_resolve_incident_without_active_incident_raises(self):
        with self.assertRaisesMessage(ValueError, 'no tiene una incidencia activa'):
            ServiceOperationCommands.resolve_incident(self.operation, actor=self.admin)

    def test_report_incident_on_closed_operation_raises(self):
        operation = ServiceOperationCommands.plan(
            self.operation,
            scheduled_date=date.today() + timedelta(days=1), scheduled_time=time(9, 0),
            actor=self.admin,
        )
        operation = ServiceOperationCommands.assign_technician(
            operation, technician=self.technician, actor=self.admin,
        )
        operation = ServiceOperationCommands.notify_client(operation, actor=self.admin)
        for target in (
            ServiceOperation.READY_TO_VISIT, ServiceOperation.ON_THE_WAY,
            ServiceOperation.ARRIVED, ServiceOperation.IN_PROGRESS, ServiceOperation.COMPLETED,
        ):
            operation = ServiceOperationCommands.transition(operation, target, self.admin)
        operation = ServiceOperationCommands.close(operation, actor=self.admin)
        with self.assertRaisesMessage(ValueError, 'cerrada'):
            ServiceOperationCommands.report_incident(operation, notes='Tarde', actor=self.admin)
