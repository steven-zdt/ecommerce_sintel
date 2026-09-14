from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from operations.models import DispatcherProfile, OperationAssignment, OperationTicket
from operations.services.commands import DispatcherCommands, OperationCommands
from orders.models import Order, OrderItem
from shop.models import Category, Product, ProductVariant
from technical_services.models import ServiceCategory, ServiceVariant, TechnicalService
from users.models import User


class OperationPipelineTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer@example.com', 'secret123')
        UserProfile.objects.create(user=self.customer, user_type=UserProfile.CUSTOMER)
        self.transporter = User.objects.create_user('driver@example.com', 'secret123')
        UserProfile.objects.create(user=self.transporter, user_type=UserProfile.TRANSPORTER)
        self.dispatcher = DispatcherProfile.objects.create(
            user=self.transporter,
            dispatcher_type=DispatcherProfile.DRIVER,
        )
        self.order = Order.objects.create(
            user=self.customer,
            status='paid',
            total_amount=Decimal('200.00'),
        )

    def _add_mixed_items(self):
        category = Category.objects.create(name='Hardware', slug='hardware')
        product = Product.objects.create(
            vendor=self.customer,
            category=category,
            name='Router',
            slug='router',
        )
        product_variant = ProductVariant.objects.create(
            product=product,
            sku='PRODUCT-1',
            price=Decimal('100.00'),
        )
        service_category = ServiceCategory.objects.create(name='Redes', slug='redes')
        service = TechnicalService.objects.create(
            vendor=self.customer,
            category=service_category,
            name='Instalacion',
            slug='instalacion',
            description='Instalacion de red.',
        )
        service_variant = ServiceVariant.objects.create(
            service=service,
            sku='SERVICE-1',
            fixed_price=Decimal('100.00'),
            pricing_strategy=ServiceVariant.FIXED,
        )
        OrderItem.objects.create(
            order=self.order,
            variant=product_variant,
            item_name='Router',
            sku='PRODUCT-1',
            quantity=1,
            price=Decimal('100.00'),
        )
        OrderItem.objects.create(
            order=self.order,
            service_variant=service_variant,
            item_name='Instalacion',
            sku='SERVICE-1',
            quantity=1,
            price=Decimal('100.00'),
        )

    def test_mixed_order_creates_one_idempotent_ticket_per_type(self):
        self._add_mixed_items()

        first = OperationCommands.ensure_tickets_for_order(self.order)
        second = OperationCommands.ensure_tickets_for_order(self.order)

        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertSetEqual(
            set(self.order.operation_tickets.values_list('operation_type', flat=True)),
            {OperationTicket.SHOP_DELIVERY, OperationTicket.SERVICE},
        )
        self.assertEqual(self.order.operation_tickets.count(), 2)

    def test_assignment_marks_transporter_busy_and_completion_releases_it(self):
        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]
        OperationCommands.assign_resource(
            ticket=ticket,
            assignee=self.transporter,
            role=OperationAssignment.ROLE_TRANSPORTER,
        )
        self.dispatcher.refresh_from_db()
        self.assertFalse(self.dispatcher.is_available)

        OperationCommands.schedule(ticket, '2026-07-01', '08:00', '10:00')
        OperationCommands.transition_status(ticket, OperationTicket.STATUS_EN_ROUTE)
        OperationCommands.transition_status(ticket, OperationTicket.STATUS_IN_PROGRESS)
        OperationCommands.transition_status(ticket, OperationTicket.STATUS_COMPLETED)

        self.dispatcher.refresh_from_db()
        self.assertTrue(self.dispatcher.is_available)
        self.assertEqual(
            ticket.assignments.get().status,
            OperationAssignment.STATUS_RELEASED,
        )

    def test_operational_tasks_are_scoped_to_assignee(self):
        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]
        OperationCommands.assign_resource(
            ticket=ticket,
            assignee=self.transporter,
            role=OperationAssignment.ROLE_TRANSPORTER,
        )
        client = APIClient()
        client.force_authenticate(self.transporter)

        response = client.get('/api/v1/operations/tasks/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['uuid'], str(ticket.uuid))

        client.force_authenticate(self.customer)
        forbidden = client.get('/api/v1/operations/tasks/')
        self.assertEqual(forbidden.status_code, 403)

    def test_assign_resource_service_ticket_delegates_to_service_operation(self):
        """
        Cross-domain audit FASE B (2026-08-14): assign_resource() para tickets
        SERVICE debe delegar en ServiceOperationCommands.assign_technician()
        -- no limitarse a escribir TechnicianProfile.is_available de forma
        aislada (el hallazgo critico de la auditoria: eso dejaba al tecnico
        marcado ocupado sin ninguna ServiceOperation que lo explicara). Ver
        technical_services/.AGENT/CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md.
        """
        self._add_mixed_items()
        technician_user = User.objects.create_user('tech-cross-b@example.com', 'secret123')
        # UserProfile(user_type=TECHNICIAN) autocrea TechnicianProfile via signal
        # (ver technical_services.tests.TechnicianAssignmentTestCase.
        # test_technician_profile_autocreation) -- no crearlo aqui de nuevo.
        UserProfile.objects.create(user=technician_user, user_type=UserProfile.TECHNICIAN)

        tickets = OperationCommands.ensure_tickets_for_order(self.order)
        service_ticket = next(t for t in tickets if t.operation_type == OperationTicket.SERVICE)

        OperationCommands.assign_resource(
            ticket=service_ticket, assignee=technician_user,
            role=OperationAssignment.ROLE_TECHNICIAN,
        )

        from technical_services.models import ServiceOperation
        service_operation = ServiceOperation.objects.get(order=self.order)
        self.assertEqual(service_operation.technician_id, technician_user.id)
        from accounts.models import TechnicianProfile
        technician_profile = TechnicianProfile.objects.get(user=technician_user)
        self.assertFalse(technician_profile.is_available)

    def test_assign_resource_shop_delivery_ticket_delegates_to_shipment(self):
        """Mismo hallazgo, para tickets SHOP_DELIVERY con Shipment real
        (orden con item de producto fisico) delegando en
        orders.FulfillmentCommands.assign_dispatcher()."""
        self._add_mixed_items()
        tickets = OperationCommands.ensure_tickets_for_order(self.order)
        delivery_ticket = next(t for t in tickets if t.operation_type == OperationTicket.SHOP_DELIVERY)

        OperationCommands.assign_resource(
            ticket=delivery_ticket, assignee=self.transporter,
            role=OperationAssignment.ROLE_TRANSPORTER,
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.shipment.assigned_dispatcher_id, self.dispatcher.id)
        self.dispatcher.refresh_from_db()
        self.assertFalse(self.dispatcher.is_available)

    def test_assign_resource_shop_delivery_without_shipment_falls_back_to_direct_flag(self):
        """Orden sin items de producto fisico -> ensure_tickets_for_order()
        cae al fallback SHOP_DELIVERY pero no existe (ni puede crearse) un
        Shipment real -- debe conservar el comportamiento anterior a esta
        migracion (escritura directa de is_available), no romper."""
        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]
        self.assertEqual(ticket.operation_type, OperationTicket.SHOP_DELIVERY)

        OperationCommands.assign_resource(
            ticket=ticket, assignee=self.transporter, role=OperationAssignment.ROLE_TRANSPORTER,
        )

        self.dispatcher.refresh_from_db()
        self.assertFalse(self.dispatcher.is_available)

    def test_assign_resource_rental_ticket_delegates_to_rental_operation(self):
        """Mismo hallazgo que el test anterior, para tickets RENTAL delegando
        en RentalOperationCommands.assign_dispatcher()."""
        from datetime import date, timedelta
        from renting.models import RentingCategory, Equipment, EquipmentVariant, RentalRequest

        category = RentingCategory.objects.create(name='Audit Category', slug='audit-category')
        equipment = Equipment.objects.create(
            vendor=self.customer, category=category, name='Audit Equipment', slug='audit-equipment',
        )
        variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='AUDIT-001', rental_price_per_day=Decimal('50000'), stock=1,
        )
        rental_request = RentalRequest.objects.create(
            user=self.customer, equipment_variant=variant,
            status=RentalRequest.STATUS_PAID, priority=RentalRequest.PRIORITY_LOW,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=6),
            quantity=1, grand_total=Decimal('150000'), location_address='Calle Test',
        )
        ticket = OperationCommands.ensure_ticket_for_rental(rental_request)

        OperationCommands.assign_resource(
            ticket=ticket, assignee=self.transporter, role=OperationAssignment.ROLE_DISPATCHER,
        )

        from renting.models import RentalOperation
        rental_operation = RentalOperation.objects.get(rental_request=rental_request)
        self.assertEqual(rental_operation.assigned_dispatcher_id, self.dispatcher.id)
        self.dispatcher.refresh_from_db()
        self.assertFalse(self.dispatcher.is_available)


class DispatcherProfileCrossDomainFixTests(TestCase):
    """
    Fase fundacional de arquitectura de perfiles (2026-07-05):
    DispatcherCommands.create() ya no muta accounts.UserProfile.user_type, y
    assign_resource(ROLE_CONTRACTOR) valida un dispatcher FIELD_OPS directamente
    contra DispatcherProfile en vez de depender de esa mutacion.
    """

    def setUp(self):
        self.customer = User.objects.create_user('fieldops_customer@example.com', 'secret123')
        UserProfile.objects.create(user=self.customer, user_type=UserProfile.CUSTOMER)
        self.order = Order.objects.create(
            user=self.customer, status='paid', total_amount=Decimal('100.00'),
        )
        service_category = ServiceCategory.objects.create(name='Redes FieldOps', slug='redes-fieldops')
        service = TechnicalService.objects.create(
            vendor=self.customer, category=service_category,
            name='Instalacion FieldOps', slug='instalacion-fieldops',
            description='Instalacion de red.',
        )
        service_variant = ServiceVariant.objects.create(
            service=service, sku='SERVICE-FIELDOPS', fixed_price=Decimal('100.00'),
            pricing_strategy=ServiceVariant.FIXED,
        )
        OrderItem.objects.create(
            order=self.order, service_variant=service_variant,
            item_name='Instalacion FieldOps', sku='SERVICE-FIELDOPS',
            quantity=1, price=Decimal('100.00'),
        )
        # user_type=TECHNICIAN deliberadamente: NO esta en CONTRACTOR_ASSIGNABLE_TYPES, para
        # aislar que la elegibilidad como ROLE_CONTRACTOR viene del DispatcherProfile FIELD_OPS,
        # no de un user_type "parecido a contratista".
        self.field_ops_user = User.objects.create_user('fieldops_worker@example.com', 'secret123')
        UserProfile.objects.create(user=self.field_ops_user, user_type=UserProfile.TECHNICIAN)

    def test_create_does_not_mutate_user_profile_user_type(self):
        original_type = self.field_ops_user.profile.user_type
        DispatcherCommands.create(self.field_ops_user, DispatcherProfile.FIELD_OPS)
        self.field_ops_user.profile.refresh_from_db()
        self.assertEqual(self.field_ops_user.profile.user_type, original_type)

    def test_field_ops_dispatcher_is_assignable_as_contractor(self):
        DispatcherCommands.create(self.field_ops_user, DispatcherProfile.FIELD_OPS)
        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]

        assignment = OperationCommands.assign_resource(
            ticket=ticket,
            assignee=self.field_ops_user,
            role=OperationAssignment.ROLE_CONTRACTOR,
        )
        self.assertEqual(assignment.assignee, self.field_ops_user)
        self.assertEqual(assignment.role, OperationAssignment.ROLE_CONTRACTOR)

    def test_non_contractor_non_dispatcher_rejected(self):
        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]
        with self.assertRaises(ValueError):
            OperationCommands.assign_resource(
                ticket=ticket,
                assignee=self.customer,
                role=OperationAssignment.ROLE_CONTRACTOR,
            )


class NotifyStaleOperationTicketsTests(TestCase):
    """
    Fase 14 (AUDITORIA/28_AUDITORIA_OPERATIONS.md, 2026-08-03): antes OperationTicket no tenia
    NINGUNA alerta de estancamiento -- un ticket podia quedar indefinidamente en
    ASSIGNED/SCHEDULED/EN_ROUTE sin que nadie se enterara. Ahora se notifica al asignado activo
    tras 48h sin avance (updated_at), deduplicado por NotificationLog.
    """

    def setUp(self):
        self.customer = User.objects.create_user('stale_customer@example.com', 'secret123')
        UserProfile.objects.create(user=self.customer, user_type=UserProfile.CUSTOMER)
        self.transporter = User.objects.create_user('stale_driver@example.com', 'secret123')
        UserProfile.objects.create(user=self.transporter, user_type=UserProfile.TRANSPORTER)
        DispatcherProfile.objects.create(
            user=self.transporter, dispatcher_type=DispatcherProfile.DRIVER,
            is_available=True, is_active=True,
        )
        self.order = Order.objects.create(
            user=self.customer, status='paid', total_amount=Decimal('200.00'),
        )

    def _make_stale_ticket(self, *, hours_ago, status):
        from django.utils import timezone as tz
        from datetime import timedelta

        ticket = OperationCommands.ensure_tickets_for_order(self.order)[0]
        OperationCommands.assign_resource(
            ticket=ticket, assignee=self.transporter, role=OperationAssignment.ROLE_TRANSPORTER,
        )
        # Bypass deliberado de la FSM -- este test cubre la query del periodic task, no las
        # transiciones de estado (ya cubiertas por OperationPipelineTests).
        OperationTicket.objects.filter(pk=ticket.pk).update(
            status=status, updated_at=tz.now() - timedelta(hours=hours_ago),
        )
        return OperationTicket.objects.get(pk=ticket.pk)

    def test_notifica_al_transportista_asignado_si_no_hay_avance(self):
        from notifications.models import NotificationLog
        from operations.tasks import notify_stale_operation_tickets

        self._make_stale_ticket(hours_ago=49, status=OperationTicket.STATUS_ASSIGNED)

        notify_stale_operation_tickets()

        self.assertTrue(
            NotificationLog.objects.filter(
                user=self.transporter, template_slug='operacion_estancada',
            ).exists()
        )

    def test_no_notifica_dentro_del_umbral(self):
        from notifications.models import NotificationLog
        from operations.tasks import notify_stale_operation_tickets

        self._make_stale_ticket(hours_ago=10, status=OperationTicket.STATUS_ASSIGNED)

        notify_stale_operation_tickets()

        self.assertFalse(NotificationLog.objects.filter(template_slug='operacion_estancada').exists())

    def test_no_notifica_dos_veces_el_mismo_ticket(self):
        from notifications.models import NotificationLog
        from operations.tasks import notify_stale_operation_tickets

        self._make_stale_ticket(hours_ago=49, status=OperationTicket.STATUS_EN_ROUTE)

        notify_stale_operation_tickets()
        notify_stale_operation_tickets()

        self.assertEqual(
            NotificationLog.objects.filter(
                template_slug='operacion_estancada', channel='',
            ).count(),
            1,
        )

    def test_no_notifica_tickets_completados(self):
        from notifications.models import NotificationLog
        from operations.tasks import notify_stale_operation_tickets

        self._make_stale_ticket(hours_ago=100, status=OperationTicket.STATUS_COMPLETED)

        notify_stale_operation_tickets()

        self.assertFalse(NotificationLog.objects.filter(template_slug='operacion_estancada').exists())
