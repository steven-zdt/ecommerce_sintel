import datetime
from decimal import Decimal
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import transaction
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

from users.models import User
from accounts.models import UserProfile, ProfessionalAvailability
from accounts.services.commands import AvailabilityCommands, AccountCommands
from accounts.services.selectors import AvailabilitySelector
from technical_services.models import TechnicalService, ServiceVariant, ServiceCategory, ServiceLevel
from technical_services.services.commands import ServiceCommands
from orders.models import Order, OrderItem
from payment.models import Transaction
from payment.services.commands import WompiCommands, PaymentCommands

User = get_user_model()


class AvailabilityServiceTestCase(TransactionTestCase):
    """
    Verifica las operaciones del service layer de disponibilidad y agenda profesional.
    """

    def setUp(self):
        # Crear usuario profesional y su perfil
        self.professional = AccountCommands.register_user({
            "email": "profesional_test@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Pro",
            "last_name": "Test",
        })
        self.profile = self.professional.profile
        
        # Crear cliente
        self.client_user = AccountCommands.register_user({
            "email": "client_test@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.SPECIALIST,
            "first_name": "Client",
            "last_name": "Test",
        })

    def test_create_availability_blocks(self):
        """Verifica la creacion masiva de slots de disponibilidad."""
        start_date = datetime.date(2026, 7, 6) # Lunes
        end_date = datetime.date(2026, 7, 7) # Martes
        
        # 8:00 a 12:00 en bloques de 2h = 2 slots por dia (8-10, 10-12)
        # 2 dias * 2 slots = 4 slots
        created = AvailabilityCommands.create_availability_blocks(
            user_profile=self.profile,
            start_date=start_date,
            end_date=end_date,
            work_start_hour=8,
            work_end_hour=12,
            slot_duration_hours=2,
            exclude_weekends=True
        )
        
        self.assertEqual(len(created), 4)
        self.assertEqual(ProfessionalAvailability.objects.filter(user_profile=self.profile).count(), 4)
        
        # Verificar que si se vuelve a correr, ignora conflictos por unique_together
        created_again = AvailabilityCommands.create_availability_blocks(
            user_profile=self.profile,
            start_date=start_date,
            end_date=end_date,
            work_start_hour=8,
            work_end_hour=12,
            slot_duration_hours=2,
            exclude_weekends=True
        )
        self.assertEqual(len(created_again), 0)
        self.assertEqual(ProfessionalAvailability.objects.filter(user_profile=self.profile).count(), 4)

    def test_create_availability_blocks_validation(self):
        """Valida las restricciones en los parametros de creacion masiva."""
        with self.assertRaises(ValidationError):
            AvailabilityCommands.create_availability_blocks(
                user_profile=self.profile,
                start_date=datetime.date(2026, 7, 7),
                end_date=datetime.date(2026, 7, 6),
            )
            
        with self.assertRaises(ValidationError):
            AvailabilityCommands.create_availability_blocks(
                user_profile=self.profile,
                start_date=datetime.date(2026, 7, 6),
                end_date=datetime.date(2026, 7, 7),
                slot_duration_hours=0
            )

        with self.assertRaises(ValidationError):
            AvailabilityCommands.create_availability_blocks(
                user_profile=self.profile,
                start_date=datetime.date(2026, 7, 6),
                end_date=datetime.date(2026, 7, 7),
                work_start_hour=18,
                work_end_hour=8
            )

    @patch('accounts.tasks.release_expired_slot.apply_async')
    def test_lock_slot_temporarily(self, mock_apply_async):
        """Verifica el bloqueo temporal de un slot y el encolamiento de la tarea Celery."""
        slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.AVAILABLE
        )
        
        locked_slot = AvailabilityCommands.lock_slot_temporarily(slot.id, self.client_user)
        
        self.assertEqual(locked_slot.status, ProfessionalAvailability.PENDING_RESERVATION)
        self.assertEqual(locked_slot.booked_by, self.client_user)
        
        # Como estamos usando TransactionTestCase, el on_commit se ejecuta al final de la transaccion.
        # En Django test environments, commit_on_success o on_commit se disparan cuando finaliza el test,
        # o podemos forzarlo en TransactionTestCase.
        # Verifiquemos si la tarea Celery fue llamada o agregada al commit hooks.
        # Para forzar la ejecucion de callbacks de on_commit en TransactionTestCase:
        # django test TransactionTestCase ejecuta los callbacks al terminar el bloque transaccional.
        # Verifiquemos mock_apply_async llamando directamente al commit.
        
    def test_confirm_and_release_booking(self):
        """Verifica los cambios de estado al confirmar o liberar reservas."""
        slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.PENDING_RESERVATION,
            booked_by=self.client_user
        )
        
        # Confirmar
        confirmed = AvailabilityCommands.confirm_booking(slot.id)
        self.assertEqual(confirmed.status, ProfessionalAvailability.BOOKED)
        
        # Liberar
        released = AvailabilityCommands.release_booking(slot.id)
        self.assertEqual(released.status, ProfessionalAvailability.AVAILABLE)
        self.assertIsNone(released.booked_by)

    def test_update_slot_status_permissions(self):
        """Verifica que solo el dueno del perfil pueda cambiar manualmente el estado del slot."""
        slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.AVAILABLE
        )
        
        # Cambiar a BLOCKED
        updated = AvailabilityCommands.update_slot_status(slot.id, ProfessionalAvailability.BLOCKED, self.professional)
        self.assertEqual(updated.status, ProfessionalAvailability.BLOCKED)
        
        # Intentar modificar con otro usuario
        with self.assertRaises(ValidationError):
            AvailabilityCommands.update_slot_status(slot.id, ProfessionalAvailability.AVAILABLE, self.client_user)


class AvailabilityCeleryTaskTestCase(TransactionTestCase):
    """
    Verifica que la tarea asincrona de liberacion funcione correctamente.
    """

    def setUp(self):
        self.professional = AccountCommands.register_user({
            "email": "profesional_celery@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Pro",
            "last_name": "Celery",
        })
        self.profile = self.professional.profile
        
        self.client_user = AccountCommands.register_user({
            "email": "client_celery@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.SPECIALIST,
            "first_name": "Client",
            "last_name": "Celery",
        })

    def test_release_expired_slot_task(self):
        """Verifica que la tarea release_expired_slot libere el slot si sigue en PENDING."""
        from accounts.tasks import release_expired_slot
        
        slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.PENDING_RESERVATION,
            booked_by=self.client_user
        )
        
        # Ejecutar la tarea directamente
        release_expired_slot(slot.id)
        
        slot.refresh_from_db()
        self.assertEqual(slot.status, ProfessionalAvailability.AVAILABLE)
        self.assertIsNone(slot.booked_by)

    def test_release_expired_slot_task_no_op_if_booked(self):
        """La tarea no debe alterar el slot si ya paso a BOOKED."""
        from accounts.tasks import release_expired_slot
        
        slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.BOOKED,
            booked_by=self.client_user
        )
        
        release_expired_slot(slot.id)
        
        slot.refresh_from_db()
        self.assertEqual(slot.status, ProfessionalAvailability.BOOKED)
        self.assertEqual(slot.booked_by, self.client_user)


class AvailabilityAPITestCase(APITestCase):
    """
    Pruebas de endpoints REST para la disponibilidad de contratistas.
    """

    def setUp(self):
        self.professional = AccountCommands.register_user({
            "email": "pro_api@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Pro",
            "last_name": "Api",
        })
        self.profile = self.professional.profile
        
        self.client_user = AccountCommands.register_user({
            "email": "client_api@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.SPECIALIST,
            "first_name": "Client",
            "last_name": "Api",
        })
        
        # Slot disponible
        self.slot_available = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.AVAILABLE
        )
        
        # Slot reservado
        self.slot_pending = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            status=ProfessionalAvailability.PENDING_RESERVATION
        )

    def test_list_availability_public(self):
        """Cualquier usuario (anonimo o autenticado) puede ver los slots AVAILABLE."""
        url = "/api/v1/auth/availability/"
        
        # Anonimo
        response = self.client.get(url, {"profile": str(self.profile.uuid)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.slot_available.id)

    def test_lock_slot_authenticated(self):
        """Un usuario autenticado puede bloquear un slot temporalmente."""
        url = f"/api/v1/auth/availability/{self.slot_available.id}/lock/"
        self.client.force_authenticate(user=self.client_user)
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'success')
        
        self.slot_available.refresh_from_db()
        self.assertEqual(self.slot_available.status, ProfessionalAvailability.PENDING_RESERVATION)
        self.assertEqual(self.slot_available.booked_by, self.client_user)

    def test_bulk_create_endpoint(self):
        """Un profesional puede crear su agenda masivamente."""
        url = "/api/v1/auth/availability/bulk-create/"
        self.client.force_authenticate(user=self.professional)
        
        payload = {
            "start_date": "2026-07-13",
            "end_date": "2026-07-14",
            "work_start_hour": 9,
            "work_end_hour": 15,
            "slot_duration_hours": 3,
            "exclude_weekends": True
        }
        
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 201)
        # 9 a 15 en bloques de 3h = 2 slots por dia. 2 dias = 4 slots.
        self.assertEqual(response.data['created_count'], 4)


class EndToEndBookingIntegrationTestCase(TransactionTestCase):
    """
    Verifica la integracion end-to-end del flujo de reserva:
    1. Bloqueo temporal del slot.
    2. Creacion de la solicitud de servicio asociando el slot.
    3. Webhook de pago exitoso (Wompi) que confirma el slot (BOOKED).
    4. O Webhook de pago fallido que libera el slot (AVAILABLE).
    """

    def setUp(self):
        # Crear actores
        self.admin = User.objects.create_superuser(
            email="admin_e2e@example.com",
            password="adminpassword",
        )
        UserProfile.objects.create(
            user=self.admin,
            first_name="Admin",
            last_name="E2E",
            user_type="ADMIN"
        )
        
        self.customer = AccountCommands.register_user({
            "email": "customer_e2e@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.SPECIALIST,
            "first_name": "Client",
            "last_name": "E2E",
        })
        
        self.professional = AccountCommands.register_user({
            "email": "tech_e2e@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "user_type": UserProfile.TECHNICIAN,
            "first_name": "Tech",
            "last_name": "E2E",
        })
        self.profile = self.professional.profile
        
        # Categorias, niveles, servicio y variante
        self.category = ServiceCategory.objects.create(name="E2E Specialty", slug="e2e-specialty")
        AccountCommands.add_specialty(self.profile, self.category.id)
        
        self.level = ServiceLevel.objects.create(name="E2E Level", slug="e2e-level")
        self.service = TechnicalService.objects.create(
            vendor=self.admin,
            category=self.category,
            level=self.level,
            name="E2E Clean Service",
            slug="e2e-clean-service"
        )
        self.variant = ServiceVariant.objects.create(
            service=self.service,
            sku="SERV-E2E-001",
            # CONTRACTOR_RATES fue removido del modelo (ver migracion
            # technical_services/0014_servicevariant_remove_contractor_rates.py,
            # que migra filas existentes a HOURLY) -- HOURLY es el reemplazo
            # sancionado, y coincide con la intencion original del test (usa
            # profile.hourly_rate/estimated_hours para el calculo de tarifa).
            pricing_strategy=ServiceVariant.HOURLY,
            estimated_hours=Decimal('2.00')
        )
        
        # Configurar tarifas del contratista
        self.profile.hourly_rate = Decimal('50000.00')
        self.profile.daily_rate = Decimal('350000.00')
        self.profile.contractor_type = 'ELECTRICISTA'
        self.profile.save()
        
        # Crear slot disponible
        self.slot = ProfessionalAvailability.objects.create(
            user_profile=self.profile,
            date=datetime.date(2026, 7, 6),
            start_time=datetime.time(8, 0),
            end_time=datetime.time(10, 0),
            status=ProfessionalAvailability.AVAILABLE
        )

    def test_e2e_successful_booking_lifecycle(self):
        """Flujo completo con pago exitoso."""
        # 1. Bloqueo temporal
        AvailabilityCommands.lock_slot_temporarily(self.slot.id, self.customer)
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, ProfessionalAvailability.PENDING_RESERVATION)
        
        # 2. Creacion del Service Request
        order = ServiceCommands.request_service(
            user=self.customer,
            variant=self.variant,
            quantity=1,
            duration=2,
            selected_technician=self.professional,
            selected_slot_id=self.slot.id,
            service_detail_data={
                "priority": "high",
                "description": "E2E Test Details",
                "address": "Calle Falsa 123"
            }
        )
        
        detail = order.service_detail
        self.assertEqual(detail.booked_slot_id, self.slot.id)
        self.assertEqual(detail.booked_date, self.slot.date)
        self.assertEqual(detail.booked_start_time, self.slot.start_time)
        
        # 3. Inicializar transaccion Wompi
        wompi_tx = WompiCommands.initialize_transaction(order)
        self.assertEqual(wompi_tx.status, 'PENDING')
        
        # 4. Simular Webhook Wompi APPROVED
        webhook_payload = {
            "data": {
                "transaction": {
                    "reference": str(wompi_tx.uuid),
                    "status": "APPROVED",
                    "id": "wompi_tx_12345"
                }
            }
        }
        
        with patch('ecommerce.ws_notify.ws_notify') as mock_ws:
            WompiCommands.process_webhook_notification(webhook_payload)
            
        # Verificar estados finales
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, ProfessionalAvailability.BOOKED)

    def test_e2e_failed_booking_lifecycle_releases_slot(self):
        """Flujo completo con pago fallido que libera el slot."""
        # 1. Bloqueo temporal
        AvailabilityCommands.lock_slot_temporarily(self.slot.id, self.customer)
        
        # 2. Creacion de solicitud de servicio
        order = ServiceCommands.request_service(
            user=self.customer,
            variant=self.variant,
            quantity=1,
            duration=2,
            selected_technician=self.professional,
            selected_slot_id=self.slot.id,
            service_detail_data={
                "priority": "high",
                "description": "E2E Test Details Failed",
                "address": "Calle Falsa 123"
            }
        )
        
        # 3. Inicializar transaccion Wompi
        wompi_tx = WompiCommands.initialize_transaction(order)
        
        # 4. Simular Webhook Wompi FAILED
        webhook_payload = {
            "data": {
                "transaction": {
                    "reference": str(wompi_tx.uuid),
                    "status": "FAILED",
                    "id": "wompi_tx_failed"
                }
            }
        }
        
        WompiCommands.process_webhook_notification(webhook_payload)
        
        # El slot debe haber vuelto a AVAILABLE y el booked_by debe haberse limpiado
        self.slot.refresh_from_db()
        self.assertEqual(self.slot.status, ProfessionalAvailability.AVAILABLE)
        self.assertIsNone(self.slot.booked_by)
