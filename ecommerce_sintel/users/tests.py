from django.contrib.auth.models import Group
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User, UserAuditLog, EmailVerificationCode
from users.services.selectors import UserSelector
from accounts.models import UserProfile
from accounts.services.commands import AccountCommands


class UserSelectorTestCase(TestCase):
    """
    Regresion: UserSelector.list_all() usa select_related('profile', 'vendor_profile',
    'technician_profile') -- vendor_profile dejo de existir cuando se elimino VendorProfile
    (2026-07-05) y quedo sin actualizar, causando un FieldError (500) real en
    GET /api/v1/users/ (UserList.vue en el panel admin).
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email='selector_test@example.com', password='Pass@1234!', is_active=True,
        )
        UserProfile.objects.create(user=self.user, first_name='Test', last_name='User')

    def test_list_all_does_not_raise(self):
        users = list(UserSelector.list_all())
        self.assertIn(self.user, users)

    def test_get_by_email_and_by_id(self):
        self.assertEqual(UserSelector.get_by_email('selector_test@example.com'), self.user)
        self.assertEqual(UserSelector.get_by_id(self.user.id), self.user)


class UserViewSetAPITestCase(TestCase):
    """Regresion end-to-end del mismo bug via el endpoint real que usa el panel admin."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin_users_api@example.com', password='Pass@1234!',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_list_users_endpoint_returns_200(self):
        response = self.client.get('/api/v1/users/')
        self.assertEqual(response.status_code, 200)


class UserSelectorFiltersTestCase(TestCase):
    """Filtros/busqueda/ordering nuevos de UserSelector.list_all() (panel /panel/usuarios)."""

    def setUp(self):
        self.tech = User.objects.create_user(email='filters_tech@example.com', password='x', is_active=True, is_verified=True)
        UserProfile.objects.create(user=self.tech, first_name='Ana', last_name='Gomez', user_type=UserProfile.TECHNICIAN, company='Acme')
        self.customer = User.objects.create_user(email='filters_customer@example.com', password='x', is_active=False, is_verified=False)
        UserProfile.objects.create(user=self.customer, first_name='Beto', last_name='Diaz', user_type=UserProfile.CUSTOMER, company='OtherCo')

    def test_search_matches_profile_fields(self):
        results = list(UserSelector.list_all(search='Gomez'))
        self.assertEqual(results, [self.tech])

    def test_filter_by_user_type(self):
        results = list(UserSelector.list_all(user_type=UserProfile.CUSTOMER))
        self.assertEqual(results, [self.customer])

    def test_filter_by_is_active_and_is_verified(self):
        self.assertEqual(list(UserSelector.list_all(is_active='true')), [self.tech])
        self.assertEqual(list(UserSelector.list_all(is_verified='false')), [self.customer])

    def test_filter_by_company(self):
        self.assertEqual(list(UserSelector.list_all(company='Acme')), [self.tech])

    def test_invalid_ordering_falls_back_to_default(self):
        # ordering no soportado -> no rompe, y cae al default (-date_joined: mas nuevo primero)
        results = list(UserSelector.list_all(ordering='"; DROP TABLE users_user; --'))
        self.assertEqual(results[0], self.customer)
        self.assertEqual(results[1], self.tech)


class UserViewSetAuditLogTestCase(TestCase):
    """UserViewSet debe registrar UserAuditLog en cada accion administrativa."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='audit_admin@example.com', password='Pass@1234!')
        self.target = User.objects.create_user(email='audit_target@example.com', password='Pass@1234!', is_active=True)
        UserProfile.objects.create(user=self.target, first_name='Target', last_name='User', user_type=UserProfile.CUSTOMER)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _actions_logged(self):
        return list(UserAuditLog.objects.filter(target_user=self.target).values_list('action', flat=True))

    def test_deactivate_and_reactivate_logs_actions(self):
        r = self.client.patch(f'/api/v1/users/{self.target.uuid}/', {'is_active': False}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertIn(UserAuditLog.ACTION_DEACTIVATED, self._actions_logged())

        r2 = self.client.patch(f'/api/v1/users/{self.target.uuid}/', {'is_active': True}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.assertIn(UserAuditLog.ACTION_ACTIVATED, self._actions_logged())

    def test_erase_logs_action_and_soft_deletes_without_removing_the_row(self):
        # erase() ya no hace DELETE fisico (ver UserCommands.erase_user) --
        # la fila sigue existiendo, solo is_deleted=True, para no chocar con
        # on_delete=PROTECT en modelos relacionados (bug real corregido).
        self.target.is_active = False
        self.target.save(update_fields=['is_active'])
        target_uuid, target_email = self.target.uuid, self.target.email

        r = self.client.delete(f'/api/v1/users/{target_uuid}/erase/')
        self.assertEqual(r.status_code, 204)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_deleted)
        self.assertTrue(User.objects.filter(uuid=target_uuid).exists())

        entry = UserAuditLog.objects.get(action=UserAuditLog.ACTION_ERASED, target_user_email=target_email)
        self.assertEqual(entry.target_user_id, self.target.id)  # fila sigue existiendo, FK intacto

    def test_reset_password_changes_hash_and_logs(self):
        old_hash = self.target.password
        r = self.client.post(f'/api/v1/users/{self.target.uuid}/reset-password/')
        self.assertEqual(r.status_code, 200)
        self.target.refresh_from_db()
        self.assertNotEqual(self.target.password, old_hash)
        self.assertIn(UserAuditLog.ACTION_PASSWORD_RESET, self._actions_logged())

    def test_resend_verification_rejected_when_already_verified(self):
        self.target.is_verified = True
        self.target.save(update_fields=['is_verified'])
        r = self.client.post(f'/api/v1/users/{self.target.uuid}/resend-verification/')
        self.assertEqual(r.status_code, 400)

    def test_resend_verification_and_confirm_link_marks_verified(self):
        r = self.client.post(f'/api/v1/users/{self.target.uuid}/resend-verification/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(UserAuditLog.ACTION_VERIFICATION_RESENT, self._actions_logged())

        token = AccountCommands.resend_verification_email(self.target)
        r2 = self.client.post('/api/v1/auth/verify-email-confirm/', {'token': token}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_verified)

    def test_groups_catalog_and_update(self):
        group = Group.objects.create(name='Soporte')
        r = self.client.get('/api/v1/users/groups-catalog/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(group.id, [g['id'] for g in r.data])

        r2 = self.client.put(f'/api/v1/users/{self.target.uuid}/groups/', {'group_ids': [group.id]}, format='json')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual([g['name'] for g in r2.data['groups']], ['Soporte'])
        self.assertIn(UserAuditLog.ACTION_GROUPS_CHANGED, self._actions_logged())

    def test_audit_log_endpoint_scoped_to_target_user(self):
        self.client.post(f'/api/v1/users/{self.target.uuid}/reset-password/')
        r = self.client.get(f'/api/v1/users/{self.target.uuid}/audit-log/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['action'], UserAuditLog.ACTION_PASSWORD_RESET)


class AdminForgotPasswordTestCase(TestCase):
    """Flujo self-service de recuperacion de contrasena EXCLUSIVO para admins."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email='admin_forgot_password@example.com', password='OldPass123!',
        )
        self.customer = User.objects.create_user(
            email='non_admin_forgot_password@example.com', password='OldPass123!',
        )

    def _latest_code(self, email):
        return (
            EmailVerificationCode.objects
            .filter(email=email, purpose=EmailVerificationCode.PURPOSE_PASSWORD_RESET_ADMIN)
            .order_by('-created_at')
            .first()
        )

    def test_full_reset_flow_and_auto_login(self):
        r1 = self.client.post(
            '/api/v1/admin-auth/forgot-password-request/', {'email': self.admin.email}, format='json',
        )
        self.assertEqual(r1.status_code, 200)

        code_obj = self._latest_code(self.admin.email)
        self.assertIsNotNone(code_obj)

        r2 = self.client.post(
            '/api/v1/admin-auth/forgot-password-verify/',
            {'email': self.admin.email, 'code': code_obj.code},
            format='json',
        )
        self.assertEqual(r2.status_code, 200)

        r3 = self.client.post(
            '/api/v1/admin-auth/reset-password/',
            {
                'email': self.admin.email,
                'code': code_obj.code,
                'new_password': 'BrandNewPass456!',
                'new_password_confirm': 'BrandNewPass456!',
            },
            format='json',
        )
        self.assertEqual(r3.status_code, 200)
        self.assertIn('tokens', r3.data)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('BrandNewPass456!'))

    def test_non_admin_email_cannot_be_reset_via_admin_endpoint(self):
        r1 = self.client.post(
            '/api/v1/admin-auth/forgot-password-request/', {'email': self.customer.email}, format='json',
        )
        self.assertEqual(r1.status_code, 200)
        self.assertIsNone(self._latest_code(self.customer.email))

        response = self.client.post(
            '/api/v1/admin-auth/reset-password/',
            {
                'email': self.customer.email,
                'code': '123456',
                'new_password': 'ShouldNotWork456!',
                'new_password_confirm': 'ShouldNotWork456!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('OldPass123!'))

    def test_reset_rejects_password_that_fails_policy(self):
        self.client.post(
            '/api/v1/admin-auth/forgot-password-request/', {'email': self.admin.email}, format='json',
        )
        code_obj = self._latest_code(self.admin.email)

        response = self.client.post(
            '/api/v1/admin-auth/reset-password/',
            {
                'email': self.admin.email,
                'code': code_obj.code,
                'new_password': 'short',
                'new_password_confirm': 'short',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('new_password', response.data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('OldPass123!'))


class UserEraseTestCase(TestCase):
    """
    DELETE /api/v1/users/{uuid}/erase/ -- antes hacia hard-delete y podia lanzar
    django.db.models.deletion.ProtectedError sin capturar (500) cuando el usuario
    tenia una RentalOperation asociada (RentalOperation.rental_request es PROTECT,
    RentalRequest.user es CASCADE). Ahora es soft-delete (is_deleted=True) -- el
    caso con RentalOperation real es la prueba de regresion central de este fix.
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='erase_admin@example.com', password='AdminE2E123!',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _inactive_user(self, email):
        u = User.objects.create_user(email=email, password='Pass123!')
        u.is_active = False
        u.save(update_fields=['is_active'])
        return u

    def test_erase_user_without_dependencies(self):
        target = self._inactive_user('erase_no_deps@example.com')
        response = self.client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(response.status_code, 204)
        target.refresh_from_db()
        self.assertTrue(target.is_deleted)
        self.assertNotIn(target, UserSelector.list_all())

    def test_erase_user_with_protected_rental_operation_no_longer_500s(self):
        from decimal import Decimal
        from datetime import date, timedelta
        from renting.models import RentingCategory, Equipment, EquipmentVariant, RentalRequest, RentalPeriod
        from renting.services.operations import RentalOperationCommands

        target = self._inactive_user('erase_with_rental@example.com')
        category = RentingCategory.objects.create(name='Erase Test Category', slug='erase-test-category')
        equipment = Equipment.objects.create(
            vendor=self.admin, category=category, name='Erase Test Equipment', slug='erase-test-equipment',
        )
        variant = EquipmentVariant.objects.create(
            equipment=equipment, sku='ERASE-001', rental_price_per_day=Decimal('100000'), stock=1,
        )
        rental_request = RentalRequest.objects.create(
            user=target, equipment_variant=variant,
            status=RentalRequest.STATUS_PAID, priority=RentalRequest.PRIORITY_HIGH,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=6),
            quantity=1, grand_total=Decimal('300000'), location_address='Calle 1',
        )
        RentalPeriod.objects.create(
            rental_request=rental_request, equipment_variant=variant,
            start_date=rental_request.start_date, end_date=rental_request.end_date,
            status=RentalPeriod.STATUS_SCHEDULED,
        )
        operation = RentalOperationCommands.ensure_for_request(rental_request, self.admin)

        response = self.client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(response.status_code, 204)
        target.refresh_from_db()
        self.assertTrue(target.is_deleted)
        # La RentalRequest/RentalOperation deben seguir intactas -- ninguna fila
        # relacionada se toca en un soft-delete.
        self.assertTrue(RentalRequest.objects.filter(pk=rental_request.pk).exists())
        self.assertTrue(operation.__class__.objects.filter(pk=operation.pk).exists())

    def test_erase_already_erased_user_returns_404(self):
        target = self._inactive_user('erase_twice@example.com')
        first = self.client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(first.status_code, 204)
        second = self.client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(second.status_code, 404)

    def test_erase_active_user_returns_400(self):
        target = User.objects.create_user(email='erase_active@example.com', password='Pass123!')
        response = self.client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(response.status_code, 400)

    def test_erase_self_returns_400(self):
        response = self.client.delete(f'/api/v1/users/{self.admin.uuid}/erase/')
        self.assertEqual(response.status_code, 400)

    def test_erase_requires_admin_permission(self):
        non_admin = User.objects.create_user(email='erase_non_admin@example.com', password='Pass123!')
        target = self._inactive_user('erase_forbidden@example.com')
        client = APIClient()
        client.force_authenticate(non_admin)
        response = client.delete(f'/api/v1/users/{target.uuid}/erase/')
        self.assertEqual(response.status_code, 403)

    def test_erase_nonexistent_user_returns_404(self):
        response = self.client.delete('/api/v1/users/00000000-0000-0000-0000-000000000000/erase/')
        self.assertEqual(response.status_code, 404)


class OtpNotLoggedTestCase(TestCase):
    """
    Test de regresion para A-01 (auditoria enterprise, 2026-07-24).

    Los logs de "OTP generado"/"Nuevo OTP" incluian el codigo en texto plano
    (f"...{code}"). Cualquiera con acceso de lectura a los logs (agregador
    centralizado, error tracker, etc.) podia leer el OTP de cualquier usuario
    sin necesidad de acceder al correo. La correccion quito el codigo del
    mensaje de log -- el codigo real sigue viajando (hasheado o no) solo por
    el canal legitimo: el correo enviado al usuario.
    """

    def test_request_verification_never_logs_the_otp_code(self):
        from users.services.commands import VerificationCommands
        from users.models import EmailVerificationCode

        with self.assertLogs('users.services.commands', level='INFO') as captured:
            verification = VerificationCommands.request_email_verification(
                email='otp_log_test@example.com',
                payload={'password': 'Sintel2026!Test', 'password_confirm': 'Sintel2026!Test'},
            )

        real_code = verification.code
        self.assertEqual(len(real_code), 6)
        log_text = '\n'.join(captured.output)
        self.assertNotIn(real_code, log_text)
        # La ausencia del codigo no debe ser porque el log dejo de escribirse:
        # confirmar que SI se registro el evento (sin el codigo adentro).
        self.assertIn('OTP generado', log_text)

    def test_resend_verification_never_logs_the_otp_code(self):
        from django.utils import timezone
        from datetime import timedelta
        from users.services.commands import VerificationCommands
        from users.models import EmailVerificationCode

        VerificationCommands.request_email_verification(
            email='otp_resend_log_test@example.com',
            payload={'password': 'Sintel2026!Test', 'password_confirm': 'Sintel2026!Test'},
        )
        # Sortear el cooldown de 60s de resend_email_verification (no es lo que
        # este test cubre) retrocediendo el created_at del codigo existente.
        EmailVerificationCode.objects.filter(email='otp_resend_log_test@example.com').update(
            created_at=timezone.now() - timedelta(seconds=120)
        )

        with self.assertLogs('users.services.commands', level='INFO') as captured:
            verification = VerificationCommands.resend_email_verification(
                email='otp_resend_log_test@example.com',
            )

        real_code = verification.code
        log_text = '\n'.join(captured.output)
        self.assertNotIn(real_code, log_text)
        self.assertIn('Nuevo OTP', log_text)


class UserAuditLogRequestMetadataTestCase(TestCase):
    """
    Lote 1 Identity Management (bajo riesgo): UserAuditCommands.log() ahora acepta
    `request` y captura ip_address/user_agent en metadata -- mismo patron ya usado
    por security.SecurityCommands.log_event(). Sin request, se comporta igual que
    antes (metadata sin esos 2 campos).
    """

    def setUp(self):
        self.admin = User.objects.create_superuser(email='audit_meta_admin@example.com', password='Pass@1234!')
        self.target = User.objects.create_user(email='audit_meta_target@example.com', password='Pass@1234!', is_active=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_reset_password_via_api_captures_ip_and_user_agent(self):
        response = self.client.post(
            f'/api/v1/users/{self.target.uuid}/reset-password/',
            HTTP_USER_AGENT='pytest-agent/1.0',
        )
        self.assertEqual(response.status_code, 200)
        entry = UserAuditLog.objects.get(target_user=self.target, action=UserAuditLog.ACTION_PASSWORD_RESET)
        self.assertIn('ip_address', entry.metadata)
        self.assertEqual(entry.metadata['user_agent'], 'pytest-agent/1.0')

    def test_log_without_request_has_no_ip_fields(self):
        from users.services.commands import UserAuditCommands
        entry = UserAuditCommands.log(self.admin, self.target, UserAuditLog.ACTION_UPDATED)
        self.assertNotIn('ip_address', entry.metadata)
        self.assertNotIn('user_agent', entry.metadata)


class UserBulkActionTestCase(TestCase):
    """POST /api/v1/users/bulk-action/ -- Lote 1 Identity Management."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='bulk_admin@example.com', password='Pass@1234!')
        self.u1 = User.objects.create_user(email='bulk_u1@example.com', password='Pass@1234!', is_active=True)
        self.u2 = User.objects.create_user(email='bulk_u2@example.com', password='Pass@1234!', is_active=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_bulk_deactivate_updates_all_and_logs_each(self):
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.u1.uuid), str(self.u2.uuid)],
            'action': 'deactivate',
            'reason': 'prueba masiva',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['updated']), 2)
        self.assertEqual(response.data['failed'], [])
        self.u1.refresh_from_db()
        self.u2.refresh_from_db()
        self.assertFalse(self.u1.is_active)
        self.assertFalse(self.u2.is_active)
        for u in (self.u1, self.u2):
            entry = UserAuditLog.objects.get(target_user=u, action=UserAuditLog.ACTION_DEACTIVATED)
            self.assertTrue(entry.metadata['bulk'])
            self.assertEqual(entry.metadata['reason'], 'prueba masiva')

    def test_bulk_activate_from_inactive(self):
        User.objects.filter(uuid__in=[self.u1.uuid, self.u2.uuid]).update(is_active=False)
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.u1.uuid), str(self.u2.uuid)], 'action': 'activate',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['updated']), 2)
        self.u1.refresh_from_db()
        self.assertTrue(self.u1.is_active)

    def test_bulk_deactivate_skips_self_but_processes_others(self):
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.admin.uuid), str(self.u1.uuid)], 'action': 'deactivate',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated'], [str(self.u1.uuid)])
        self.assertEqual(len(response.data['failed']), 1)
        self.assertEqual(response.data['failed'][0]['uuid'], str(self.admin.uuid))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_bulk_unknown_uuid_reported_as_failed(self):
        missing = '00000000-0000-0000-0000-000000000000'
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.u1.uuid), missing], 'action': 'activate',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated'], [str(self.u1.uuid)])
        self.assertEqual(response.data['failed'], [{'uuid': missing, 'email': '', 'detail': 'Usuario no encontrado.'}])

    def test_bulk_invalid_action_returns_400(self):
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.u1.uuid)], 'action': 'delete_forever',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_bulk_empty_uuids_returns_400(self):
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [], 'action': 'activate',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_bulk_resend_verification_skips_already_verified(self):
        self.u1.is_verified = True
        self.u1.save(update_fields=['is_verified'])
        response = self.client.post('/api/v1/users/bulk-action/', {
            'uuids': [str(self.u1.uuid), str(self.u2.uuid)], 'action': 'resend_verification',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['updated'], [str(self.u2.uuid)])
        self.assertEqual(len(response.data['failed']), 1)
        self.assertEqual(response.data['failed'][0]['uuid'], str(self.u1.uuid))


class UserTimelineTestCase(TestCase):
    """GET /api/v1/users/{uuid}/timeline/ -- fusiona UserAuditLog + KYC + SecurityEvent."""

    def setUp(self):
        self.admin = User.objects.create_superuser(email='timeline_admin@example.com', password='Pass@1234!')
        self.target = User.objects.create_user(email='timeline_target@example.com', password='Pass@1234!', is_active=True)
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_timeline_merges_and_sorts_three_sources(self):
        from users.services.commands import UserAuditCommands
        from kyc.models import UserVerification, VerificationEvent
        from security.services.commands import SecurityCommands
        from security.models import SecurityEvent

        UserAuditCommands.log(self.admin, self.target, UserAuditLog.ACTION_UPDATED)

        verification = UserVerification.objects.create(user=self.target, status=UserVerification.STATUS_APPROVED)
        VerificationEvent.objects.create(
            verification=verification, event_type=VerificationEvent.APPROVED, description='Aprobado en prueba',
        )

        SecurityCommands.log_event(SecurityEvent.LOGIN_SUCCESS, user=self.target)

        response = self.client.get(f'/api/v1/users/{self.target.uuid}/timeline/')
        self.assertEqual(response.status_code, 200)
        results = response.data['results']
        sources = {e['source'] for e in results}
        self.assertEqual(sources, {'audit', 'kyc', 'security'})

        timestamps = [e['timestamp'] for e in results]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_timeline_scoped_to_target_user_only(self):
        from users.services.commands import UserAuditCommands
        other = User.objects.create_user(email='timeline_other@example.com', password='Pass@1234!')
        UserAuditCommands.log(self.admin, other, UserAuditLog.ACTION_UPDATED)
        UserAuditCommands.log(self.admin, self.target, UserAuditLog.ACTION_UPDATED)

        response = self.client.get(f'/api/v1/users/{self.target.uuid}/timeline/')
        emails_involved = [e.get('actor_email') for e in response.data['results']]
        self.assertEqual(len(response.data['results']), 1)
        self.assertNotIn(other.email, [e for e in emails_involved if e])
