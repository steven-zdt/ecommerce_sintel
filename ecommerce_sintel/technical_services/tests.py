from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from technical_services.models import (
    TechnicalService, ServiceVariant, ServiceCategory, ServiceLevel, ServiceConfiguration, ServiceCostRule
)
from technical_services.services.calculator import LaborCostCalculator
from technical_services.services.selectors import ServiceSelector

User = get_user_model()

class TechnicalServicesPricingTestCase(TransactionTestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="testuser_ts@example.com",
            password="testpassword"
        )
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            user_type="VENDOR"
        )
        
        # Create category
        self.category = ServiceCategory.objects.create(
            name="Test Category",
            slug="test-category-ts"
        )
        
        # Create level
        self.level = ServiceLevel.objects.create(
            name="Intermediate",
            slug="intermediate-ts"
        )
        
        # Create service
        self.service = TechnicalService.objects.create(
            vendor=self.user,
            category=self.category,
            level=self.level,
            name="Installation Service",
            slug="installation-service-ts"
        )
        
        # Create configuration
        self.config = ServiceConfiguration.objects.create(
            name="Test Config",
            smlv=Decimal('1300000.00'),
            transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'),
            indirect_costs_rate=Decimal('15.00'),
            is_active=True
        )

    def test_hourly_rate_calculation(self):
        calculated_rate = LaborCostCalculator.calculate_hourly_rate(self.config)
        expected_rate = Decimal('10313.1041667')
        self.assertAlmostEqual(float(calculated_rate), float(expected_rate), places=4)

    def test_pricing_strategy_hourly(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-HRLY-001",
            estimated_hours=Decimal('4.00'),
            complexity_factor=Decimal('1.50'),
            pricing_strategy=ServiceVariant.HOURLY
        )
        
        # Without duration parameter (uses default estimated_hours)
        cost = LaborCostCalculator.calculate_variant_labor_cost(variant)
        self.assertAlmostEqual(float(cost), 61878.625, places=2)
        
        # With duration parameter
        cost_with_duration = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=6.0)
        self.assertAlmostEqual(float(cost_with_duration), 92817.9375, places=2)

    def test_pricing_strategy_hourly_with_bounds(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-HRLY-002",
            estimated_hours=Decimal('5.00'),
            complexity_factor=Decimal('1.00'),
            pricing_strategy=ServiceVariant.HOURLY,
            min_duration=Decimal('2.00'),
            max_duration=Decimal('8.00')
        )
        
        # Duration below minimum
        cost_min = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=1.0)
        self.assertAlmostEqual(float(cost_min), 20626.2083, places=2)
        
        # Duration above maximum
        cost_max = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=10.0)
        self.assertAlmostEqual(float(cost_max), 82504.8333, places=2)

    def test_pricing_strategy_daily(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-DLY-001",
            estimated_hours=Decimal('2.00'),
            complexity_factor=Decimal('1.20'),
            pricing_strategy=ServiceVariant.DAILY
        )
        
        # Daily rate = Hourly rate * 8 = 10313.1041667 * 8 = 82504.8333
        # Cost = Daily rate * 2 * 1.2 = 198011.60
        cost = LaborCostCalculator.calculate_variant_labor_cost(variant)
        self.assertAlmostEqual(float(cost), 198011.60, places=1)
        
        # With duration parameter = 3.0 days
        cost_with_duration = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=3.0)
        self.assertAlmostEqual(float(cost_with_duration), 297017.40, places=1)

    def test_pricing_strategy_daily_with_bounds(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-DLY-002",
            estimated_hours=Decimal('5.00'),
            complexity_factor=Decimal('1.00'),
            pricing_strategy=ServiceVariant.DAILY,
            min_duration=Decimal('3.00'),
            max_duration=Decimal('10.00')
        )
        
        # Below min
        cost_min = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=2.0)
        self.assertAlmostEqual(float(cost_min), 247514.50, places=1)
        
        # Above max
        cost_max = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=15.0)
        self.assertAlmostEqual(float(cost_max), 825048.33, places=1)

    def test_pricing_strategy_fixed(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-FXD-001",
            fixed_price=Decimal('500000.00'),
            pricing_strategy=ServiceVariant.FIXED
        )
        
        cost = LaborCostCalculator.calculate_variant_labor_cost(variant)
        self.assertEqual(cost, Decimal('500000.00'))
        
        cost_with_duration = LaborCostCalculator.calculate_variant_labor_cost(variant, duration=5.0)
        self.assertEqual(cost_with_duration, Decimal('500000.00'))

    def test_service_selector_get_quotation(self):
        variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-QUOTE-001",
            estimated_hours=Decimal('3.00'),
            complexity_factor=Decimal('1.00'),
            pricing_strategy=ServiceVariant.HOURLY,
            min_duration=Decimal('1.00'),
            max_duration=Decimal('5.00')
        )
        
        # Call selector with duration=4.0
        quotation = ServiceSelector.get_variant_quotation(variant, duration=4.0)
        
        self.assertEqual(quotation['labor_cost'], Decimal('41252.42'))
        self.assertEqual(quotation['breakdown']['pricing_strategy'], ServiceVariant.HOURLY)
        self.assertEqual(quotation['breakdown']['duration'], 4.0)
        self.assertEqual(quotation['breakdown']['min_duration'], 1.0)
        self.assertEqual(quotation['breakdown']['max_duration'], 5.0)


from rest_framework.test import APITestCase
from users.models import User
from accounts.models import TechnicianProfile
from technical_services.models import OrderServiceDetail, OrderServiceTimeline
from orders.models import Order
from technical_services.services.commands import ServiceAssignmentCommands, ServiceTimelineCommands
from technical_services.services.selectors import TechnicianSelector
from technical_services.api.serializers import ServiceRequestInputSerializer

class ServiceRequestSerializerTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='customer@example.com', password='password123')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='Customer', last_name='User', user_type='CUSTOMER')

        self.category = ServiceCategory.objects.create(name='Support', slug='support')
        self.level = ServiceLevel.objects.create(name='Basic', slug='basic')
        self.service = TechnicalService.objects.create(
            vendor=self.user,
            category=self.category,
            level=self.level,
            name='Support Visit',
            slug='support-visit',
            is_purchasable=True,
            is_active=True,
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku='SV-001',
            estimated_hours=Decimal('2.00'),
            pricing_strategy=ServiceVariant.HOURLY,
            is_active=True,
        )

    def test_serializer_accepts_richer_request_metadata(self):
        from django.utils import timezone
        from datetime import date, time, timedelta

        payload = {
            'variant_uuid': self.variant.uuid,
            'quantity': 1,
            'priority': 'high',
            'description': 'Necesito apoyo técnico',
            'address': 'Calle 10 # 20-30',
            'scheduled_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'preferred_date': '2026-08-15',
            'preferred_time': '14:30',
            'location_reference': 'Porteria principal',
            'neighborhood': 'Laureles',
            'service_notes': 'Requiere acceso al cuarto de servidores',
            'allow_schedule_changes': True,
            'contact_person': {
                'full_name': 'Ana Gomez',
                'document_type': 'CC',
                'document_number': '1234567890',
                'cargo': 'Coordinadora',
                'email': 'ana@example.com',
                'phone': '3001234567',
            },
        }

        serializer = ServiceRequestInputSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['preferred_date'], date(2026, 8, 15))
        self.assertEqual(serializer.validated_data['preferred_time'], time(14, 30))
        self.assertTrue(serializer.validated_data['allow_schedule_changes'])


class TechnicianAssignmentTestCase(APITestCase):
    def setUp(self):
        # Create categories for specialties
        self.parent_cat = ServiceCategory.objects.create(name="Parent Category", slug="parent-cat")
        self.child_cat = ServiceCategory.objects.create(name="Child Category", slug="child-cat", parent=self.parent_cat)
        
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            email="admin_ts@example.com",
            password="adminpassword",
        )
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=self.admin_user,
            first_name="Admin",
            last_name="User",
            user_type="ADMIN"
        )
        
        # Create a customer user
        self.customer = User.objects.create_user(
            email="customer_ts@example.com",
            password="customerpassword",
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name="Customer",
            last_name="User",
            user_type="CUSTOMER"
        )
        
        # Create technician 1 (specialized in child_cat, available)
        from accounts.services.commands import AccountCommands
        self.tech1 = AccountCommands.register_user({
            "email": "tech1@example.com",
            "password": "techpassword",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Tech",
            "last_name": "One"
        })
        self.tech1_profile = self.tech1.technician_profile
        self.tech1_profile.specialties.add(self.child_cat)
        
        # Create technician 2 (specialized in parent_cat, available)
        self.tech2 = AccountCommands.register_user({
            "email": "tech2@example.com",
            "password": "techpassword",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Tech",
            "last_name": "Two"
        })
        self.tech2_profile = self.tech2.technician_profile
        self.tech2_profile.specialties.add(self.parent_cat)

        # Create level & service & variant
        self.level = ServiceLevel.objects.create(name="Base Level", slug="base-level")
        self.service = TechnicalService.objects.create(
            vendor=self.admin_user,
            category=self.child_cat,
            level=self.level,
            name="Service child",
            slug="service-child"
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-VAR-001",
            estimated_hours=Decimal('2.00'),
            pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('100000.00')
        )
        from django.contrib.contenttypes.models import ContentType
        from inventory.models import StockRecord, InventoryTransaction
        ct = ContentType.objects.get_for_model(ServiceVariant)
        self.stock_record = StockRecord.objects.create(
            content_type=ct,
            object_id=self.variant.uuid,
            sku=self.variant.sku,
            stock=10,
            is_active=True
        )
        InventoryTransaction.objects.create(
            stock_record=self.stock_record,
            movement_type='ENTRY',
            quantity=10,
            balance_after=10
        )
        self.config = ServiceConfiguration.objects.create(
            name="Test Config",
            smlv=Decimal('1300000.00'),
            transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'),
            indirect_costs_rate=Decimal('15.00'),
            is_active=True
        )

        # Request an order
        from technical_services.services.commands import ServiceCommands
        self.order = ServiceCommands.request_service(
            user=self.customer,
            variant=self.variant,
            quantity=1,
            service_detail_data={
                'priority': 'medium',
                'description': 'Test service description',
                'address': 'Calle 123'
            }
        )

    def test_technician_profile_autocreation(self):
        """
        Verify that a TechnicianProfile is automatically created when registering a TECHNICIAN.
        """
        self.assertIsNotNone(self.tech1.technician_profile)
        self.assertTrue(self.tech1.technician_profile.is_available)
        from accounts.models import UserProfile
        self.assertEqual(self.tech1.profile.user_type, UserProfile.TECHNICIAN)

    def test_request_service_with_preselected_technician_sets_professional_type_snapshot(self):
        """
        Regresion: request_service() con selected_technician + service_detail_data hacia
        `technician_profile.professional_type` -- campo inexistente en TechnicianProfile,
        AttributeError garantizado. Ahora usa ProfileResolver.get_type() (UserProfile.user_type).
        """
        from technical_services.services.commands import ServiceCommands
        from accounts.models import UserProfile

        order = ServiceCommands.request_service(
            user=self.customer,
            variant=self.variant,
            quantity=1,
            service_detail_data={
                'priority': 'medium',
                'description': 'Servicio con tecnico preseleccionado',
                'address': 'Calle 456',
            },
            selected_technician=self.tech1,
        )

        self.assertEqual(order.service_detail.professional_type_snapshot, UserProfile.TECHNICIAN)
        self.assertEqual(order.service_detail.technician, self.tech1)

    def test_manual_assignment(self):
        """
        Verify manual assignment works, changes availability, and logs timeline event.
        """
        detail = ServiceAssignmentCommands.assign_technician(
            order=self.order,
            technician=self.tech1,
            notes="Assigning Tech One",
            assigned_by=self.admin_user
        )
        
        self.assertEqual(detail.technician, self.tech1)
        self.tech1_profile.refresh_from_db()
        self.assertFalse(self.tech1_profile.is_available)
        
        # Verify timeline event was logged
        timeline_events = self.order.timeline.filter(status='assigned')
        self.assertTrue(timeline_events.exists())
        self.assertIn("Assigning Tech One", timeline_events.first().notes)

    def test_manual_assignment_errors(self):
        """
        Verify assigning a non-technician or unavailable technician raises ValueError.
        """
        # 1. Non-technician
        with self.assertRaises(ValueError):
            ServiceAssignmentCommands.assign_technician(self.order, self.customer)
            
        # 2. Make tech1 unavailable and try to assign
        self.tech1_profile.is_available = False
        self.tech1_profile.save()
        
        with self.assertRaises(ValueError):
            ServiceAssignmentCommands.assign_technician(self.order, self.tech1)

    def test_auto_assignment_exact_match(self):
        """
        Verify auto-assignment picks the tech with exact specialty match.
        """
        detail = ServiceAssignmentCommands.auto_assign_technician(
            order=self.order,
            assigned_by=self.admin_user
        )
        self.assertEqual(detail.technician, self.tech1)
        self.tech1_profile.refresh_from_db()
        self.assertFalse(self.tech1_profile.is_available)

    def test_auto_assignment_parent_match(self):
        """
        Verify auto-assignment falls back to parent category specialty if no child category tech is available.
        """
        # Make tech1 unavailable
        self.tech1_profile.is_available = False
        self.tech1_profile.save()
        
        detail = ServiceAssignmentCommands.auto_assign_technician(
            order=self.order,
            assigned_by=self.admin_user
        )
        self.assertEqual(detail.technician, self.tech2)

    def test_auto_assignment_no_one_available(self):
        """
        Verify auto-assignment raises ValueError when no qualified technicians are available.
        """
        self.tech1_profile.is_available = False
        self.tech1_profile.save()
        self.tech2_profile.is_available = False
        self.tech2_profile.save()
        
        with self.assertRaises(ValueError):
            ServiceAssignmentCommands.auto_assign_technician(self.order)

    def test_release_technician_on_status_change(self):
        """
        Verify technician is released (is_available=True) when order is completed or cancelled.
        """
        # Assign technician
        ServiceAssignmentCommands.assign_technician(self.order, self.tech1)
        self.tech1_profile.refresh_from_db()
        self.assertFalse(self.tech1_profile.is_available)
        
        # Complete the order
        ServiceTimelineCommands.add_timeline_event(
            order=self.order,
            status='completed',
            notes="Job done",
            created_by=self.admin_user
        )
        
        self.tech1_profile.refresh_from_db()
        self.assertTrue(self.tech1_profile.is_available)

    def test_api_endpoints_permissions(self):
        """
        Verify that manual and auto assign API endpoints require IsAdminUser (role=ADMIN, is_staff=True).
        """
        url_assign = f"/api/v1/orders/service-orders/{self.order.uuid}/assign-technician/"
        
        # 1. Anonymous user
        response = self.client.post(url_assign, {'technician_uuid': str(self.tech1.uuid)})
        self.assertEqual(response.status_code, 401)
        
        # 2. Customer user
        self.client.force_authenticate(user=self.customer)
        response = self.client.post(url_assign, {'technician_uuid': str(self.tech1.uuid)})
        self.assertEqual(response.status_code, 403)
        
        # 3. Admin user
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url_assign, {'technician_uuid': str(self.tech1.uuid), 'notes': 'Test notes'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['technician']['uuid'], str(self.tech1.uuid))

    def test_api_auto_assign_endpoint(self):
        """
        Verify auto-assign endpoint successfully runs and assigns a tech.
        """
        url_auto = f"/api/v1/orders/service-orders/{self.order.uuid}/auto-assign/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url_auto)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['technician']['uuid'], str(self.tech1.uuid))

    def test_unassign_technician(self):
        """ServiceAssignmentCommands.unassign_technician libera al tecnico y vuelve el detalle a pending."""
        ServiceAssignmentCommands.assign_technician(self.order, self.tech1, assigned_by=self.admin_user)
        self.tech1_profile.refresh_from_db()
        self.assertFalse(self.tech1_profile.is_available)

        detail = ServiceAssignmentCommands.unassign_technician(self.order, unassigned_by=self.admin_user)
        self.assertIsNone(detail.technician)
        self.tech1_profile.refresh_from_db()
        self.assertTrue(self.tech1_profile.is_available)
        self.assertTrue(self.order.timeline.filter(status='pending').exists())

    def test_unassign_technician_without_assignment_raises(self):
        with self.assertRaises(ValueError):
            ServiceAssignmentCommands.unassign_technician(self.order, unassigned_by=self.admin_user)

    def test_change_priority(self):
        detail = ServiceAssignmentCommands.change_priority(self.order, 'high', changed_by=self.admin_user)
        self.assertEqual(detail.priority, 'high')

    def test_change_priority_invalid_raises(self):
        with self.assertRaises(ValueError):
            ServiceAssignmentCommands.change_priority(self.order, 'not-a-priority')

    def test_get_candidates_for_order(self):
        candidates = TechnicianSelector.get_candidates_for_order(self.order)
        self.assertIn(self.tech1, list(candidates))

    def test_api_unassign_endpoint(self):
        ServiceAssignmentCommands.assign_technician(self.order, self.tech1, assigned_by=self.admin_user)
        url = f"/api/v1/orders/service-orders/{self.order.uuid}/unassign-technician/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['technician'])

    def test_api_change_priority_endpoint(self):
        url = f"/api/v1/orders/service-orders/{self.order.uuid}/change-priority/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, {'priority': 'critical'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['priority'], 'critical')

    def test_api_change_priority_endpoint_invalid_priority(self):
        url = f"/api/v1/orders/service-orders/{self.order.uuid}/change-priority/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(url, {'priority': 'not-a-priority'})
        self.assertEqual(response.status_code, 400)

    def test_api_available_technicians_endpoint(self):
        url = f"/api/v1/orders/service-orders/{self.order.uuid}/available-technicians/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        uuids = [c['uuid'] for c in response.data]
        self.assertIn(str(self.tech1.uuid), uuids)

    def test_api_assignment_queue_endpoint(self):
        url = "/api/v1/orders/service-orders/assignment-queue/"
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        results = response.data.get('results', response.data)
        uuids = [item['uuid'] for item in results]
        self.assertIn(str(self.order.uuid), uuids)

    def test_get_assigned_technician_prefers_service_operation(self):
        """
        Migracion "autoridad unica de tecnico" FASE 8 (2026-08-14):
        ServiceTechnicianReconciliationSelector.get_assigned_technician() debe
        leer ServiceOperation.technician (fuente real), no el snapshot legacy,
        incluso si divergen (caso B de find_divergent_assignments()).
        """
        from technical_services.services.selectors import ServiceTechnicianReconciliationSelector
        from technical_services.services.operations import ServiceOperationCommands

        ServiceAssignmentCommands.assign_technician(self.order, self.tech1, assigned_by=self.admin_user)
        operation = ServiceOperationCommands.ensure_for_order(self.order)
        ServiceOperationCommands.assign_technician(operation, technician=self.tech2, actor=self.admin_user)

        self.order.refresh_from_db()
        detail = self.order.service_detail
        detail.refresh_from_db()
        self.assertEqual(detail.technician, self.tech1)  # snapshot legacy, no sincronizado

        resolved = ServiceTechnicianReconciliationSelector.get_assigned_technician(self.order)
        self.assertEqual(resolved, self.tech2)  # fuente real gana

    def test_find_divergent_assignments_classifies_conflict_and_operation_only(self):
        """
        FASE 6-7 (2026-08-14): find_divergent_assignments() debe detectar el caso
        B (conflicto real, ambos asignados a tecnicos distintos) y el caso C
        (asignado solo via ServiceOperation, esperado desde FASE 4 para
        asignaciones hechas fuera del panel legacy de Orders).
        """
        from technical_services.services.selectors import ServiceTechnicianReconciliationSelector
        from technical_services.services.operations import ServiceOperationCommands

        # Orden 1 (self.order): conflicto real (caso B).
        ServiceAssignmentCommands.assign_technician(self.order, self.tech1, assigned_by=self.admin_user)
        operation1 = ServiceOperationCommands.ensure_for_order(self.order)
        ServiceOperationCommands.assign_technician(operation1, technician=self.tech2, actor=self.admin_user)

        # Orden 2: asignada solo via ServiceOperation (caso C, panel de Servicios/fachada).
        from technical_services.services.commands import ServiceCommands
        order2 = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Orden 2', 'address': 'Calle 2'},
        )
        operation2 = ServiceOperationCommands.ensure_for_order(order2)
        ServiceOperationCommands.assign_technician(operation2, technician=self.tech2, actor=self.admin_user)

        result = ServiceTechnicianReconciliationSelector.find_divergent_assignments()
        self.assertIn(str(self.order.uuid), result['B_conflict'])
        self.assertIn(str(order2.uuid), result['C_operation_only'])
        self.assertNotIn(str(self.order.uuid), result['C_operation_only'])
        self.assertNotIn(str(order2.uuid), result['B_conflict'])


class ServicePriceAuditingTestCase(APITestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_superuser(
            email="admin_audit@example.com",
            password="adminpassword",
        )
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=self.admin_user,
            first_name="Admin",
            last_name="User",
            user_type="ADMIN"
        )
        
        self.customer = User.objects.create_user(
            email="customer_audit@example.com",
            password="customerpassword"
        )
        UserProfile.objects.create(
            user=self.customer,
            first_name="Customer",
            last_name="User",
            user_type="CLIENT"
        )

        # Create category, level, service
        self.category = ServiceCategory.objects.create(
            name="Audit Category",
            slug="audit-category"
        )
        self.level = ServiceLevel.objects.create(
            name="Audit Level",
            slug="audit-level"
        )
        self.service = TechnicalService.objects.create(
            vendor=self.admin_user,
            category=self.category,
            level=self.level,
            name="Audit Service",
            slug="audit-service"
        )
        
        # Create service variant
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-AUDIT-001",
            fixed_price=Decimal('100000.00'),
            pricing_strategy=ServiceVariant.FIXED
        )

    def test_price_history_generation_on_update(self):
        """
        Verify ServicePriceHistory is generated only when fixed_price is updated.
        """
        from technical_services.services.commands import ServiceVariantCommands
        from technical_services.models import ServicePriceHistory

        # Check initial history is empty
        self.assertEqual(ServicePriceHistory.objects.filter(variant=self.variant).count(), 0)

        # Update complexity factor but not price
        self.variant = ServiceVariantCommands.update_variant(
            self.variant,
            {'complexity_factor': Decimal('2.00')},
            updated_by=self.admin_user
        )
        self.assertEqual(ServicePriceHistory.objects.filter(variant=self.variant).count(), 0)

        # Update fixed_price
        self.variant = ServiceVariantCommands.update_variant(
            self.variant,
            {'fixed_price': Decimal('150000.00')},
            updated_by=self.admin_user
        )
        
        history = ServicePriceHistory.objects.filter(variant=self.variant)
        self.assertEqual(history.count(), 1)
        record = history.first()
        self.assertEqual(record.old_price, Decimal('100000.00'))
        self.assertEqual(record.new_price, Decimal('150000.00'))
        self.assertEqual(record.changed_by, self.admin_user)

    def test_api_endpoints_permissions_and_response(self):
        """
        Verify core and dashboard price history endpoints require IsAdminUser and return correct data.
        """
        from technical_services.services.commands import ServiceVariantCommands
        
        # Update price to generate a history record
        self.variant = ServiceVariantCommands.update_variant(
            self.variant,
            {'fixed_price': Decimal('120000.00')},
            updated_by=self.admin_user
        )

        url_core = f"/api/v1/services/variants/{self.variant.uuid}/price_history/"
        url_dash = f"/api/v1/dashboard/service-variants/{self.variant.uuid}/price_history/"

        # Test Core API permissions
        # Anonymous
        self.client.force_authenticate(user=None)
        response = self.client.get(url_core)
        self.assertEqual(response.status_code, 401)
        # Client
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(url_core)
        self.assertEqual(response.status_code, 403)
        # Admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url_core)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['old_price'], '100000.00')
        self.assertEqual(response.data[0]['new_price'], '120000.00')
        self.assertEqual(response.data[0]['changed_by_email'], self.admin_user.email)

        # Test Dashboard BFF API permissions
        # Anonymous
        self.client.force_authenticate(user=None)
        response = self.client.get(url_dash)
        self.assertEqual(response.status_code, 401)
        # Client
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(url_dash)
        self.assertEqual(response.status_code, 403)
        # Admin
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(url_dash)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['old_price'], '100000.00')
        self.assertEqual(response.data[0]['new_price'], '120000.00')
        self.assertEqual(response.data[0]['changed_by_email'], self.admin_user.email)


class OrderServiceDetailCommercialSnapshotTestCase(APITestCase):
    """Plan 'Manual Pricing Engine' FASE 2 -- snapshot comercial ampliado en
    OrderServiceDetail. Motor sigue siendo 100% AUTOMATIC (FASE 3/4 no existen
    todavia) -- este test cubre lo que request_service() puede poblar HOY."""

    def setUp(self):
        self.customer = User.objects.create_user(email='snapshot_customer@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.category = ServiceCategory.objects.create(name='Cat Snap', slug='cat-snap')
        self.service = TechnicalService.objects.create(
            vendor=self.customer, category=self.category, name='Servicio Snap', slug='servicio-snap',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='SNAP-001', pricing_strategy=ServiceVariant.HOURLY,
            estimated_hours=Decimal('4.00'),
        )
        ServiceConfiguration.objects.create(
            name='Config Snap', smlv=Decimal('1300000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'), is_active=True,
        )

    def test_snapshot_fields_populated_on_request_service(self):
        from technical_services.services.commands import ServiceCommands

        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Prueba snapshot', 'address': 'Calle 1'},
        )
        detail = order.service_detail
        self.assertEqual(detail.pricing_source_snapshot, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertEqual(detail.pricing_mode_snapshot, ServiceVariant.HOURLY)
        self.assertIsNotNone(detail.unit_price_snapshot)
        self.assertIsNone(detail.project_price_snapshot)
        self.assertEqual(detail.duration_snapshot, Decimal('4.00'))
        self.assertIsNotNone(detail.quotation_snapshot)
        self.assertEqual(detail.quotation_snapshot['pricing_strategy'], ServiceVariant.HOURLY)
        self.assertIn('total_price', detail.quotation_snapshot)
        self.assertIn('breakdown', detail.quotation_snapshot)

    def test_snapshot_survives_later_config_change(self):
        """Mismo principio ya probado para applied_rate_amount: el snapshot queda
        congelado, un cambio posterior en SMLV/variant no debe alterar ordenes ya
        creadas."""
        from technical_services.services.commands import ServiceCommands
        from technical_services.services.calculator import LaborCostCalculator

        order = ServiceCommands.request_service(
            user=self.customer, variant=self.variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Prueba snapshot 2', 'address': 'Calle 2'},
        )
        original_unit_price = order.service_detail.unit_price_snapshot

        ServiceConfiguration.objects.filter(is_active=True).update(is_active=False)
        ServiceConfiguration.objects.create(
            name='Config Nueva', smlv=Decimal('2000000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'), is_active=True,
        )
        LaborCostCalculator.invalidate_config_cache()

        order.service_detail.refresh_from_db()
        self.assertEqual(order.service_detail.unit_price_snapshot, original_unit_price)


class ServiceCostRulePricingTestCase(TransactionTestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            email="testuser_costrules@example.com",
            password="testpassword"
        )
        from accounts.models import UserProfile
        UserProfile.objects.create(
            user=self.user,
            first_name="Test",
            last_name="User",
            user_type="VENDOR"
        )
        
        # Create category
        self.category = ServiceCategory.objects.create(
            name="CostRules Category",
            slug="costrules-category"
        )
        
        # Create level
        self.level = ServiceLevel.objects.create(
            name="Intermediate",
            slug="intermediate-ts-costrules"
        )
        
        # Create service
        self.service = TechnicalService.objects.create(
            vendor=self.user,
            category=self.category,
            level=self.level,
            name="Installation Service Rules",
            slug="installation-service-rules"
        )
        
        # Create variant
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-RULES-001",
            estimated_hours=Decimal('3.00'),
            complexity_factor=Decimal('1.00'),
            pricing_strategy=ServiceVariant.HOURLY,
            min_duration=Decimal('1.00'),
            max_duration=Decimal('5.00')
        )

        # Create configurations
        self.config = ServiceConfiguration.objects.create(
            name="Test Config Rules",
            smlv=Decimal('1300000.00'),
            transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'),
            indirect_costs_rate=Decimal('15.00'),
            iva_rate=Decimal('19.00'),
            is_active=True
        )

    def test_global_rules_applied_automatically(self):
        from technical_services.services.pricing import ServiceCostRuleCommands
        
        # Create a global setup cost (fixed amount)
        global_setup_rule = ServiceCostRuleCommands.create_rule(
            name="Global Setup Fee",
            cost_type=ServiceCostRule.TYPE_FIXED,
            context=ServiceCostRule.CTX_SETUP,
            value=Decimal('25000.00'),
            applies_globally=True,
            is_active=True
        )

        # Create a global discount (percentage)
        global_discount_rule = ServiceCostRuleCommands.create_rule(
            name="Global Promo Discount",
            cost_type=ServiceCostRule.TYPE_PERCENTAGE,
            context=ServiceCostRule.CTX_DISCOUNT,
            value=Decimal('10.00'),
            applies_globally=True,
            is_active=True
        )

        # Get quotient via ServiceSelector
        quotation = ServiceSelector.get_variant_quotation(self.variant, duration=3.0)

        self.assertEqual(len(quotation['breakdown']['cost_rules']), 2)
        
        # Verify specific values
        subtotal_after_rules = Decimal(str(quotation['breakdown']['subtotal_after_rules']))
        total_price = Decimal(str(quotation['total_price']))
        
        self.assertAlmostEqual(float(subtotal_after_rules), 52845.38, places=1)
        self.assertAlmostEqual(float(total_price), 62886.00, places=1)

    def test_variant_specific_rule_applied_only_when_assigned(self):
        from technical_services.services.pricing import ServiceCostRuleCommands
        
        # Create a variant-specific operational cost rule
        variant_rule = ServiceCostRuleCommands.create_rule(
            name="Special Tech Support",
            cost_type=ServiceCostRule.TYPE_FIXED,
            context=ServiceCostRule.CTX_OPERATIONAL,
            value=Decimal('50000.00'),
            applies_globally=False,
            is_active=True
        )

        # Quotation before assignment
        quotation_before = ServiceSelector.get_variant_quotation(self.variant, duration=3.0)
        self.assertEqual(len(quotation_before['breakdown']['cost_rules']), 0)
        
        # Assign rule to variant
        ServiceCostRuleCommands.assign_to_variant(variant_rule, self.variant)
        
        # Quotation after assignment
        quotation_after = ServiceSelector.get_variant_quotation(self.variant, duration=3.0)
        self.assertEqual(len(quotation_after['breakdown']['cost_rules']), 1)
        self.assertEqual(quotation_after['breakdown']['cost_rules'][0]['name'], "Special Tech Support")
        self.assertEqual(quotation_after['breakdown']['cost_rules'][0]['amount'], 50000.00)

        # Deactivate rule
        ServiceCostRuleCommands.deactivate_rule(variant_rule)
        
        # Quotation after deactivation
        quotation_deactivated = ServiceSelector.get_variant_quotation(self.variant, duration=3.0)
        self.assertEqual(len(quotation_deactivated['breakdown']['cost_rules']), 0)


class DiscountPctLimitsTestCase(TransactionTestCase):
    """
    Test de regresion para R-01 (auditoria enterprise, 2026-07-24).

    discount_pct llegaba del cliente sin limites hasta Order.total_amount. Un
    valor > 100 producia un total negativo (el "descuento" superaba el
    subtotal). Doble capa de defensa:
      1. ServiceRequestInputSerializer (endpoint de creacion de orden): min/max_value.
      2. ServiceSelector.get_variant_quotation() y PackagePriceCalculator.calculate()
         (el segundo alimenta el endpoint publico AllowAny quote-package, que NO
         pasa por el serializer de arriba): clamp defensivo 0..100.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='discount_r01@example.com', password='testpassword')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='Test', last_name='User', user_type='VENDOR')

        self.category = ServiceCategory.objects.create(name='Cat R-01', slug='cat-r01')
        self.level = ServiceLevel.objects.create(name='Nivel R-01', slug='nivel-r01')
        self.service = TechnicalService.objects.create(
            vendor=self.user, category=self.category, level=self.level,
            name='Servicio R-01', slug='servicio-r01',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='SERV-R01-001', fixed_price=Decimal('100000.00'),
            pricing_strategy=ServiceVariant.FIXED,
        )

        from technical_services.models import ServicePackage
        self.package = ServicePackage.objects.create(
            service=self.service, name='Paquete R-01', slug='paquete-r01',
            base_price=Decimal('100000.00'),
        )

    def test_variant_quotation_clamps_discount_above_100(self):
        quotation = ServiceSelector.get_variant_quotation(self.variant, discount_pct=Decimal('200'))
        self.assertGreaterEqual(quotation['total_price'], 0)
        self.assertEqual(quotation['discount_pct'], Decimal('100.00'))

    def test_variant_quotation_clamps_discount_below_0(self):
        quotation = ServiceSelector.get_variant_quotation(self.variant, discount_pct=Decimal('-10'))
        self.assertEqual(quotation['discount_pct'], Decimal('0.00'))

    def test_package_calculator_clamps_discount_above_100(self):
        # Regresion real encontrada al escribir este test: el clamp existia en
        # get_variant_quotation() pero NO en PackagePriceCalculator.calculate(),
        # que es lo que consume el endpoint publico quote-package -- un
        # discount_pct=200 producia un total negativo. Corregido en el mismo
        # cambio que agrego este test.
        from technical_services.services.packages import PackagePriceCalculator
        breakdown = PackagePriceCalculator.calculate(self.package, discount_pct=Decimal('200'))
        self.assertGreaterEqual(breakdown['total'], Decimal('0.00'))
        self.assertEqual(breakdown['discount_pct'], Decimal('100'))

    def test_package_calculator_clamps_negative_discount(self):
        from technical_services.services.packages import PackagePriceCalculator
        breakdown = PackagePriceCalculator.calculate(self.package, discount_pct=Decimal('-25'))
        self.assertEqual(breakdown['discount_pct'], Decimal('0'))

    def test_service_request_serializer_rejects_discount_above_100(self):
        from technical_services.api.serializers import ServiceRequestInputSerializer
        serializer = ServiceRequestInputSerializer(data={
            'variant_uuid': str(self.variant.uuid),
            'discount_pct': '150',
            'description': 'Prueba R-01',
            'address': 'Calle 1 # 2-3',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('discount_pct', serializer.errors)

    def test_service_request_serializer_rejects_negative_discount(self):
        from technical_services.api.serializers import ServiceRequestInputSerializer
        serializer = ServiceRequestInputSerializer(data={
            'variant_uuid': str(self.variant.uuid),
            'discount_pct': '-5',
            'description': 'Prueba R-01',
            'address': 'Calle 1 # 2-3',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('discount_pct', serializer.errors)


class ServiceVariantPricingSourceTestCase(TransactionTestCase):
    """Plan 'Manual Pricing Engine' (2026-08-13) FASE 1 -- contrato formal de
    pricing_source en ServiceVariant.clean(). Solo valida el modelo -- el motor
    de calculo (ManualPricingCalculator/ServiceQuotationResolver) es FASE 3/4,
    todavia no existe."""

    def setUp(self):
        self.user = User.objects.create_user(email='pricing_source_ts@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='T', last_name='U', user_type='VENDOR')
        self.category = ServiceCategory.objects.create(name='Cat PS', slug='cat-ps')
        self.service = TechnicalService.objects.create(
            vendor=self.user, category=self.category, name='Servicio PS', slug='servicio-ps',
        )

    def _variant(self, **overrides):
        defaults = dict(service=self.service, sku=f'SKU-PS-{ServiceVariant.objects.count()}')
        defaults.update(overrides)
        return ServiceVariant(**defaults)

    def test_automatic_is_the_default_and_needs_no_manual_fields(self):
        variant = self._variant()
        variant.full_clean()
        self.assertEqual(variant.pricing_source, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertFalse(variant.is_manual_pricing)

    def test_automatic_rejects_manual_unit_price(self):
        variant = self._variant(manual_unit_price=Decimal('50000'))
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_project_requires_project_price(self):
        variant = self._variant(pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT)
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_project_rejects_zero_or_negative_price(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT, manual_project_price=Decimal('0'),
        )
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_project_rejects_unit_price_set(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1800000'), manual_unit_price=Decimal('1'),
        )
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_project_valid(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT, manual_project_price=Decimal('1800000'),
        )
        variant.full_clean()
        self.assertTrue(variant.is_manual_pricing)

    def test_manual_general_requires_unit_price(self):
        variant = self._variant(pricing_source=ServiceVariant.SOURCE_MANUAL_GENERAL)
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_general_rejects_project_price_set(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_GENERAL,
            manual_unit_price=Decimal('500000'), manual_project_price=Decimal('1'),
        )
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_general_valid(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_GENERAL, manual_unit_price=Decimal('500000'),
        )
        variant.full_clean()

    def test_manual_hourly_requires_unit_price(self):
        variant = self._variant(pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY)
        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_manual_hourly_valid(self):
        variant = self._variant(
            pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY, manual_unit_price=Decimal('85000'),
        )
        variant.full_clean()
        self.assertTrue(variant.is_manual_pricing)


class ManualPricingCalculatorTestCase(TransactionTestCase):
    """Plan 'Manual Pricing Engine' FASE 3. Casos exactos del propio plan (FASE
    25): tarifa 85.000/h x 6h = 510.000, IVA 19% = 96.900, total = 606.900."""

    def setUp(self):
        self.user = User.objects.create_user(email='manual_calc@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='M', last_name='C', user_type='VENDOR')
        self.category = ServiceCategory.objects.create(name='Cat MPC', slug='cat-mpc')
        self.service = TechnicalService.objects.create(
            vendor=self.user, category=self.category, name='Servicio MPC', slug='servicio-mpc',
        )
        ServiceConfiguration.objects.create(
            name='Config MPC', smlv=Decimal('1300000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'),
            iva_rate=Decimal('19.00'), is_active=True,
        )

    def test_manual_hourly_matches_plan_worked_example(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(
            service=self.service, sku='MPC-HOURLY', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
            manual_unit_price=Decimal('85000.00'),
        )
        result = ManualPricingCalculator.calculate_hourly_price(variant, duration=Decimal('6'))
        self.assertEqual(result['base_amount'], Decimal('510000.00'))
        self.assertEqual(result['iva_amount'], Decimal('96900.00'))
        self.assertEqual(result['total_price'], Decimal('606900.00'))
        self.assertEqual(result['material_cost'], Decimal('0.00'))
        self.assertEqual(result['breakdown']['cost_rules'], [])

    def test_manual_project_ignores_duration(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(
            service=self.service, sku='MPC-PROJECT', pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1000000.00'),
        )
        result_no_duration = ManualPricingCalculator.calculate_project_price(variant)
        result_with_duration = ManualPricingCalculator.calculate(variant, duration=Decimal('10'))
        self.assertEqual(result_no_duration['base_amount'], Decimal('1000000.00'))
        self.assertEqual(result_with_duration['base_amount'], Decimal('1000000.00'))

    def test_manual_general_ignores_duration(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(
            service=self.service, sku='MPC-GENERAL', pricing_source=ServiceVariant.SOURCE_MANUAL_GENERAL,
            manual_unit_price=Decimal('500000.00'),
        )
        result = ManualPricingCalculator.calculate(variant, duration=Decimal('10'))
        self.assertEqual(result['base_amount'], Decimal('500000.00'))

    def test_calculate_dispatches_by_pricing_source(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        project = ServiceVariant.objects.create(
            service=self.service, sku='MPC-DISPATCH-1', pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1800000.00'),
        )
        result = ManualPricingCalculator.calculate(project)
        self.assertEqual(result['pricing_source'], ServiceVariant.SOURCE_MANUAL_PROJECT)
        self.assertEqual(result['base_amount'], Decimal('1800000.00'))

    def test_calculate_rejects_automatic_variant(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(service=self.service, sku='MPC-AUTO')
        with self.assertRaises(ValueError):
            ManualPricingCalculator.calculate(variant)

    def test_hourly_raises_without_manual_unit_price(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant(
            service=self.service, sku='MPC-BAD', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
        )
        with self.assertRaises(ValueError):
            ManualPricingCalculator.calculate_hourly_price(variant, duration=Decimal('1'))

    def test_discount_applies_before_iva(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(
            service=self.service, sku='MPC-DISCOUNT', pricing_source=ServiceVariant.SOURCE_MANUAL_GENERAL,
            manual_unit_price=Decimal('1000000.00'),
        )
        result = ManualPricingCalculator.calculate_general_price(variant, discount_pct=Decimal('10'))
        self.assertEqual(result['discount_amount'], Decimal('100000.00'))
        taxable_base = Decimal('900000.00')
        self.assertEqual(result['iva_amount'], (taxable_base * Decimal('0.19')).quantize(Decimal('0.01')))

    def test_hourly_respects_min_duration_clamp(self):
        from technical_services.services.manual_pricing import ManualPricingCalculator
        variant = ServiceVariant.objects.create(
            service=self.service, sku='MPC-CLAMP', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
            manual_unit_price=Decimal('50000.00'), min_duration=Decimal('2.00'),
        )
        result = ManualPricingCalculator.calculate_hourly_price(variant, duration=Decimal('0.5'))
        self.assertEqual(result['base_amount'], Decimal('100000.00'))  # 50000 x 2 (clamped), no x 0.5


class ServiceQuotationResolverTestCase(APITestCase):
    """Plan 'Manual Pricing Engine' FASE 4 -- ServiceQuotationResolver es el
    unico punto de entrada real. Estos tests pegan directo al endpoint publico
    (GET .../quotation/) para probar la cadena completa serializer-free:
    ViewSet -> ServiceSelector.get_variant_quotation() -> Resolver -> motor
    correcto -- exactamente lo que FASE 12 del plan exige ('mismo contrato
    independientemente del modo')."""

    def setUp(self):
        self.user = User.objects.create_user(email='resolver@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='R', last_name='S', user_type='VENDOR')
        self.category = ServiceCategory.objects.create(name='Cat Resolver', slug='cat-resolver')
        self.service = TechnicalService.objects.create(
            vendor=self.user, category=self.category, name='Servicio Resolver', slug='servicio-resolver',
        )
        ServiceConfiguration.objects.create(
            name='Config Resolver', smlv=Decimal('1300000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'),
            iva_rate=Decimal('19.00'), is_active=True,
        )

    def test_resolver_routes_automatic_to_labor_cost_calculator(self):
        from technical_services.services.quotation_resolver import ServiceQuotationResolver
        variant = ServiceVariant.objects.create(
            service=self.service, sku='RES-AUTO', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('200000.00'),
        )
        result = ServiceQuotationResolver.resolve(variant)
        self.assertEqual(result['labor_cost'], Decimal('200000.00'))
        self.assertEqual(result['pricing_strategy'], ServiceVariant.FIXED)

    def test_resolver_routes_manual_hourly_to_manual_calculator(self):
        from technical_services.services.quotation_resolver import ServiceQuotationResolver
        variant = ServiceVariant.objects.create(
            service=self.service, sku='RES-MANUAL', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
            manual_unit_price=Decimal('85000.00'),
        )
        result = ServiceQuotationResolver.resolve(variant, duration=Decimal('6'))
        self.assertEqual(result['total_price'], Decimal('606900.00'))

    def test_public_quotation_endpoint_serves_manual_project(self):
        variant = ServiceVariant.objects.create(
            service=self.service, sku='API-PROJECT', pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1800000.00'),
        )
        resp = self.client.get(f'/api/v1/services/services/quotation/?variant_uuid={variant.uuid}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(str(resp.data['base_amount'])), Decimal('1800000.00'))
        self.assertEqual(Decimal(str(resp.data['iva_amount'])), Decimal('342000.00'))
        self.assertEqual(Decimal(str(resp.data['total_price'])), Decimal('2142000.00'))

    def test_public_quotation_endpoint_serves_manual_hourly(self):
        variant = ServiceVariant.objects.create(
            service=self.service, sku='API-HOURLY', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
            manual_unit_price=Decimal('85000.00'),
        )
        resp = self.client.get(f'/api/v1/services/services/quotation/?variant_uuid={variant.uuid}&duration=6')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(str(resp.data['total_price'])), Decimal('606900.00'))

    def test_public_quotation_endpoint_still_serves_automatic(self):
        """Regresion explicita: variantes AUTOMATIC (la inmensa mayoria del
        catalogo hoy) deben seguir cotizando exactamente igual que antes de
        FASE 4."""
        variant = ServiceVariant.objects.create(
            service=self.service, sku='API-AUTO', pricing_strategy=ServiceVariant.FIXED,
            fixed_price=Decimal('300000.00'),
        )
        resp = self.client.get(f'/api/v1/services/services/quotation/?variant_uuid={variant.uuid}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(str(resp.data['labor_cost'])), Decimal('300000.00'))

    def test_misconfigured_manual_variant_returns_400_not_500(self):
        """MANUAL_HOURLY sin manual_unit_price valido -- solo posible si se
        crea via ORM directo (el modelo lo rechaza en clean()/full_clean(), pero
        el endpoint no debe explotar con un 500 si de todos modos ocurre)."""
        variant = ServiceVariant.objects.create(service=self.service, sku='API-BAD')
        ServiceVariant.objects.filter(pk=variant.pk).update(pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY)
        variant.refresh_from_db()
        resp = self.client.get(f'/api/v1/services/services/quotation/?variant_uuid={variant.uuid}')
        self.assertEqual(resp.status_code, 400)


class OrderServiceDetailManualSnapshotTestCase(APITestCase):
    """Plan 'Manual Pricing Engine' FASE 2+4 integradas -- ahora que
    ServiceQuotationResolver esta cableado, request_service() debe snapshotear
    correctamente ordenes de variantes MANUAL_*, no solo AUTOMATIC."""

    def setUp(self):
        self.customer = User.objects.create_user(email='manual_snap_customer@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.category = ServiceCategory.objects.create(name='Cat Manual Snap', slug='cat-manual-snap')
        self.service = TechnicalService.objects.create(
            vendor=self.customer, category=self.category, name='Servicio Manual Snap', slug='servicio-manual-snap',
        )
        ServiceConfiguration.objects.create(
            name='Config Manual Snap', smlv=Decimal('1300000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'),
            iva_rate=Decimal('19.00'), is_active=True,
        )

    def test_manual_project_order_snapshots_project_price_not_unit_price(self):
        from technical_services.services.commands import ServiceCommands
        variant = ServiceVariant.objects.create(
            service=self.service, sku='SNAP-PROJECT', pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1800000.00'),
        )
        order = ServiceCommands.request_service(
            user=self.customer, variant=variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Proyecto manual', 'address': 'Calle 1'},
        )
        detail = order.service_detail
        self.assertEqual(detail.pricing_source_snapshot, ServiceVariant.SOURCE_MANUAL_PROJECT)
        self.assertIsNone(detail.unit_price_snapshot)
        self.assertEqual(detail.project_price_snapshot, Decimal('1800000.00'))
        self.assertEqual(detail.quotation_snapshot['total_price'], '2142000.00')

    def test_manual_hourly_order_snapshots_unit_price_and_duration(self):
        from technical_services.services.commands import ServiceCommands
        variant = ServiceVariant.objects.create(
            service=self.service, sku='SNAP-HOURLY', pricing_source=ServiceVariant.SOURCE_MANUAL_HOURLY,
            manual_unit_price=Decimal('85000.00'), estimated_hours=Decimal('6.00'),
        )
        order = ServiceCommands.request_service(
            user=self.customer, variant=variant, quantity=1,
            service_detail_data={'priority': 'medium', 'description': 'Por horas manual', 'address': 'Calle 2'},
        )
        detail = order.service_detail
        self.assertEqual(detail.pricing_source_snapshot, ServiceVariant.SOURCE_MANUAL_HOURLY)
        self.assertEqual(detail.unit_price_snapshot, Decimal('85000.00'))
        self.assertIsNone(detail.project_price_snapshot)
        self.assertEqual(detail.duration_snapshot, Decimal('6.00'))
        self.assertEqual(detail.pricing_mode_snapshot, None)  # solo AUTOMATIC lo llena


class ServicePricingCommandsTestCase(TransactionTestCase):
    """Plan 'Manual Pricing Engine' FASE 6/7 -- ServicePricingCommands.
    set_manual_pricing() como via preferida para cambiar pricing_source, con
    historial dedicado en ServicePriceHistory."""

    def setUp(self):
        self.admin = User.objects.create_user(email='pricing_cmd_admin@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.admin, first_name='A', last_name='D', user_type='ADMIN')
        self.category = ServiceCategory.objects.create(name='Cat Pricing Cmd', slug='cat-pricing-cmd')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Pricing Cmd', slug='servicio-pricing-cmd',
        )
        self.variant = ServiceVariant.objects.create(service=self.service, sku='PC-001')

    def test_set_manual_pricing_switches_automatic_to_hourly(self):
        from technical_services.services.commands import ServicePricingCommands
        from technical_services.models import ServicePriceHistory

        ServicePricingCommands.set_manual_pricing(
            self.variant, ServiceVariant.SOURCE_MANUAL_HOURLY, unit_price=Decimal('85000.00'),
            changed_by=self.admin, reason='Servicio con dificultad especial',
        )
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_MANUAL_HOURLY)
        self.assertEqual(self.variant.manual_unit_price, Decimal('85000.00'))
        self.assertTrue(self.variant.is_manual_pricing)

        entry = ServicePriceHistory.objects.filter(variant=self.variant).latest('created_at')
        self.assertEqual(entry.pricing_source_old, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertEqual(entry.pricing_source_new, ServiceVariant.SOURCE_MANUAL_HOURLY)
        self.assertIsNone(entry.unit_price_old)
        self.assertEqual(entry.unit_price_new, Decimal('85000.00'))
        self.assertEqual(entry.changed_by, self.admin)
        self.assertEqual(entry.reason, 'Servicio con dificultad especial')

    def test_set_manual_pricing_switches_back_to_automatic(self):
        from technical_services.services.commands import ServicePricingCommands
        ServicePricingCommands.set_manual_pricing(
            self.variant, ServiceVariant.SOURCE_MANUAL_GENERAL, unit_price=Decimal('500000.00'),
        )
        ServicePricingCommands.set_manual_pricing(self.variant, ServiceVariant.SOURCE_AUTOMATIC)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertIsNone(self.variant.manual_unit_price)
        self.assertFalse(self.variant.is_manual_pricing)

    def test_set_manual_pricing_rejects_invalid_combination(self):
        """MANUAL_PROJECT sin project_price -- la variante NUNCA debe quedar
        guardada con datos invalidos, ni generarse historial."""
        from technical_services.services.commands import ServicePricingCommands
        from technical_services.models import ServicePriceHistory

        with self.assertRaises(ValidationError):
            ServicePricingCommands.set_manual_pricing(self.variant, ServiceVariant.SOURCE_MANUAL_PROJECT)

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertEqual(ServicePriceHistory.objects.filter(variant=self.variant).count(), 0)

    def test_no_history_entry_when_nothing_actually_changes(self):
        from technical_services.services.commands import ServicePricingCommands
        from technical_services.models import ServicePriceHistory

        ServicePricingCommands.set_manual_pricing(self.variant, ServiceVariant.SOURCE_AUTOMATIC)
        self.assertEqual(ServicePriceHistory.objects.filter(variant=self.variant).count(), 0)

    def test_update_variant_validates_pricing_fields_when_touched(self):
        from technical_services.services.commands import ServiceVariantCommands
        with self.assertRaises(ValidationError):
            ServiceVariantCommands.update_variant(
                self.variant, {'pricing_source': ServiceVariant.SOURCE_MANUAL_GENERAL},
            )

    def test_update_variant_ignores_pricing_validation_when_untouched(self):
        """Regresion: update_variant() para campos NO relacionados con pricing
        (ej. complexity_factor) no debe empezar a exigir validacion de pricing_
        source -- el variant ya es AUTOMATIC valido de por si, pero clean() solo
        se llama si el caller realmente toco alguno de los 3 campos."""
        from technical_services.services.commands import ServiceVariantCommands
        updated = ServiceVariantCommands.update_variant(self.variant, {'complexity_factor': Decimal('2.00')})
        self.assertEqual(updated.complexity_factor, Decimal('2.00'))


class DashboardSetVariantPricingAPITestCase(APITestCase):
    """Plan 'Manual Pricing Engine' FASE 8 -- POST /api/v1/dashboard/
    service-variants/{uuid}/set-pricing/, la unica via HTTP real que existe
    hoy para que un admin cambie pricing_source de una variante."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='set_pricing_admin@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.admin, first_name='A', last_name='D', user_type='ADMIN')
        self.customer = User.objects.create_user(email='set_pricing_customer@example.com', password='x')
        UserProfile.objects.create(user=self.customer, first_name='C', last_name='U', user_type='CLIENT')
        self.category = ServiceCategory.objects.create(name='Cat Set Pricing', slug='cat-set-pricing')
        self.service = TechnicalService.objects.create(
            vendor=self.admin, category=self.category, name='Servicio Set Pricing', slug='servicio-set-pricing',
        )
        self.variant = ServiceVariant.objects.create(service=self.service, sku='DASH-SP-001')

    def _url(self, variant=None):
        return f'/api/v1/dashboard/service-variants/{(variant or self.variant).uuid}/set-pricing/'

    def test_requires_admin(self):
        resp = self.client.post(self._url(), {'pricing_source': ServiceVariant.SOURCE_MANUAL_HOURLY, 'unit_price': '85000'})
        self.assertEqual(resp.status_code, 401)

        self.client.force_authenticate(user=self.customer)
        resp = self.client.post(self._url(), {'pricing_source': ServiceVariant.SOURCE_MANUAL_HOURLY, 'unit_price': '85000'})
        self.assertEqual(resp.status_code, 403)

    def test_admin_switches_variant_to_manual_hourly(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url(), {
            'pricing_source': ServiceVariant.SOURCE_MANUAL_HOURLY, 'unit_price': '85000.00',
            'reason': 'Trabajo en altura + dificultad especial',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['pricing_source'], ServiceVariant.SOURCE_MANUAL_HOURLY)
        self.assertEqual(resp.data['manual_unit_price'], '85000.00')
        self.assertTrue(resp.data['is_manual_pricing'])

        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_MANUAL_HOURLY)

        from technical_services.models import ServicePriceHistory
        entry = ServicePriceHistory.objects.filter(variant=self.variant).latest('created_at')
        self.assertEqual(entry.reason, 'Trabajo en altura + dificultad especial')
        self.assertEqual(entry.changed_by, self.admin)

    def test_invalid_combination_returns_400_via_http(self):
        """MANUAL_PROJECT sin project_price -- ValidationError del modelo debe
        llegar al cliente como 400, no como 500 sin manejar."""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.post(self._url(), {'pricing_source': ServiceVariant.SOURCE_MANUAL_PROJECT})
        self.assertEqual(resp.status_code, 400)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_AUTOMATIC)

    def test_variant_detail_and_list_expose_pricing_fields_read_only(self):
        """Confirma FASE 8: el panel puede LEER pricing_source/manual_*_price
        del listado/detalle normal de variantes (GET), pero esos campos no son
        escribibles via el PATCH generico."""
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(f'/api/v1/dashboard/service-variants/{self.variant.uuid}/')
        self.assertEqual(resp.data['pricing_source'], ServiceVariant.SOURCE_AUTOMATIC)
        self.assertIn('manual_unit_price', resp.data)
        self.assertIn('is_manual_pricing', resp.data)

        # Intento de cambiar pricing_source via el PATCH generico -- se ignora
        # silenciosamente (read_only_fields), la variante sigue AUTOMATIC.
        resp = self.client.patch(
            f'/api/v1/dashboard/service-variants/{self.variant.uuid}/',
            {'pricing_source': ServiceVariant.SOURCE_MANUAL_GENERAL}, format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.pricing_source, ServiceVariant.SOURCE_AUTOMATIC)


class ManualPricingPackageIntegrationTestCase(APITestCase):
    """Plan 'Manual Pricing Engine' FASE 21 -- interaccion con ServicePackage.
    PackagePriceCalculator.calculate() recibe `extra_base=quotation['base_amount']`
    (services/commands.py::request_service) -- como get_variant_quotation() ya
    delega en ServiceQuotationResolver (FASE 4), un variant MANUAL_* alimenta el
    precio de paquete correctamente SIN ningun cambio en packages.py. Este test
    prueba esa integracion real, no solo el calculador en aislamiento."""

    def setUp(self):
        self.user = User.objects.create_user(email='pkg_manual@example.com', password='x')
        from accounts.models import UserProfile
        UserProfile.objects.create(user=self.user, first_name='P', last_name='M', user_type='CLIENT')
        self.category = ServiceCategory.objects.create(name='Cat Pkg Manual', slug='cat-pkg-manual')
        self.service = TechnicalService.objects.create(
            vendor=self.user, category=self.category, name='Servicio Pkg Manual', slug='servicio-pkg-manual',
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service, sku='PKG-MANUAL-001', pricing_source=ServiceVariant.SOURCE_MANUAL_PROJECT,
            manual_project_price=Decimal('1000000.00'),
        )
        from technical_services.models import ServicePackage
        self.package = ServicePackage.objects.create(
            service=self.service, name='Paquete Manual', slug='paquete-manual',
            base_price=Decimal('200000.00'),
        )
        ServiceConfiguration.objects.create(
            name='Config Pkg Manual', smlv=Decimal('1300000.00'), transport_subsidy=Decimal('162000.00'),
            benefit_rate=Decimal('53.10'), indirect_costs_rate=Decimal('15.00'),
            iva_rate=Decimal('19.00'), is_active=True,
        )

    def test_package_price_includes_manual_variant_base_not_automatic_calc(self):
        from technical_services.services.packages import PackagePriceCalculator
        quotation = ServiceSelector.get_variant_quotation(self.variant)
        self.assertEqual(quotation['base_amount'], Decimal('1000000.00'))

        breakdown = PackagePriceCalculator.calculate(self.package, extra_base=quotation['base_amount'])
        # 200.000 (paquete) + 1.000.000 (variant manual) = 1.200.000 subtotal
        self.assertEqual(breakdown['subtotal'], Decimal('1200000.00'))
        self.assertEqual(breakdown['iva_amount'], Decimal('228000.00'))
        self.assertEqual(breakdown['total'], Decimal('1428000.00'))

    def test_request_service_with_package_uses_manual_variant_price(self):
        from technical_services.services.commands import ServiceCommands
        order = ServiceCommands.request_service(
            user=self.user, variant=self.variant, quantity=1, package=self.package,
            service_detail_data={'priority': 'medium', 'description': 'Con paquete manual', 'address': 'Calle 1'},
        )
        # order_total = package_price_breakdown['total'] (services/commands.py) --
        # confirma que el camino real end-to-end (no solo el calculador aislado)
        # usa el precio manual del variant, no un calculo AUTOMATIC.
        self.assertEqual(order.total_amount, Decimal('1428000.00'))
        self.assertEqual(order.service_detail.pricing_source_snapshot, ServiceVariant.SOURCE_MANUAL_PROJECT)
        self.assertEqual(order.service_detail.project_price_snapshot, Decimal('1000000.00'))

