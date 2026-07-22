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
