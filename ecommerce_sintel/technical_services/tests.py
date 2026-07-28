from decimal import Decimal
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




