"""
Suite de smoke tests para el rediseno SSoT de identidad (2026-07-06):
  - Registro publico crea siempre CUSTOMER, con acceso instantaneo.
  - Convertirse en profesional es un upgrade posterior via
    KycCommands.request_upgrade(), aprobado desde /panel/validaciones.
  - user_type NUNCA cambia fuera de KycCommands._apply_requested_user_type().

No duplica la suite completa de accounts/users -- solo los criterios de
aceptacion explicitos de la fase de consolidacion.
"""
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from users.models import User, EmailVerificationCode
from accounts.models import UserProfile, TechnicianProfile
from accounts.services.commands import AccountCommands
from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
from kyc.models import UserVerification, VerificationDocument
from kyc.services.commands import KycCommands


def _register_otp_payload(email, numero_documento="9000000001"):
    return {
        "email": email,
        "password": "Sintel#2026Segura!",
        "password_confirm": "Sintel#2026Segura!",
        "phone_number": "3" + numero_documento[-9:],
        "primer_nombre": "Ana",
        "primer_apellido": "Gomez",
        "fecha_nacimiento": "1995-06-15",
        "nacionalidad": "Colombiana",
        "pais": "Colombia",
        "ciudad": "Bogota",
        "direccion": "Calle 1 # 2-3",
        "tipo_documento": "CC",
        "numero_documento": numero_documento,
        "lugar_expedicion_documento": "Bogota",
        "acepta_politica_tratamiento_datos": True,
        "acepta_autorizacion_tratamiento_datos": True,
        "acepta_terminos_condiciones": True,
    }


def _fake_pdf(name="doc.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake content", content_type="application/pdf")


def _make_admin(email="kyc_admin_test@example.com"):
    return User.objects.create_superuser(email=email, password="Admin#2026Segura!")


def _register_via_otp(client, email, numero_documento="9000000001"):
    """Ejecuta el flujo OTP real (register-request + register-verify) y retorna el User creado."""
    payload = _register_otp_payload(email, numero_documento)
    r1 = client.post("/api/v1/auth/register-request/", payload, format="json")
    assert r1.status_code == 200, r1.data
    code_obj = EmailVerificationCode.objects.filter(email=email).order_by("-created_at").first()
    r2 = client.post(
        "/api/v1/auth/register-verify/", {"email": email, "code": code_obj.code}, format="json",
    )
    assert r2.status_code == 201, r2.data
    return User.objects.get(email=email), r2.data


class RegistrationAlwaysCustomerTestCase(APITestCase):
    """Registro: siempre CUSTOMER, login inmediato permitido, sin seleccion de tipo."""

    def setUp(self):
        # register-request usa ScopedRateThrottle (cache real, no se resetea
        # con el rollback de BD entre tests) -- limpiar para no chocar con
        # el limite de 5/hora entre los distintos tests de este archivo.
        cache.clear()

    def test_register_creates_customer_already_approved(self):
        user, data = _register_via_otp(self.client, "ssot_customer1@example.com", "9000000001")
        self.assertEqual(user.profile.user_type, UserProfile.CUSTOMER)
        self.assertEqual(user.kyc_verification.status, UserVerification.STATUS_APPROVED)
        self.assertIsNotNone(user.kyc_verification.first_approved_at)
        self.assertEqual(data["user"]["profile"]["user_type"], UserProfile.CUSTOMER)
        self.assertEqual(data["user"]["kyc_status"], UserVerification.STATUS_APPROVED)
        # Login inmediato: tokens ya vienen en la respuesta de register-verify.
        self.assertIn("access", data["tokens"])

    def test_register_payload_has_no_user_type_field(self):
        """user_type ya no es un campo del serializer -- si se envia, se ignora."""
        payload = _register_otp_payload("ssot_customer2@example.com", "9000000002")
        payload["user_type"] = UserProfile.PROFESSIONAL
        r1 = self.client.post("/api/v1/auth/register-request/", payload, format="json")
        self.assertEqual(r1.status_code, 200)
        code_obj = EmailVerificationCode.objects.filter(email=payload["email"]).order_by("-created_at").first()
        r2 = self.client.post(
            "/api/v1/auth/register-verify/",
            {"email": payload["email"], "code": code_obj.code}, format="json",
        )
        self.assertEqual(r2.status_code, 201)
        user = User.objects.get(email=payload["email"])
        self.assertEqual(user.profile.user_type, UserProfile.CUSTOMER)


class UpgradeWorkflowTestCase(APITestCase):
    """CUSTOMER -> solicita upgrade -> sube documentos -> sigue comprando mientras tanto."""

    def setUp(self):
        cache.clear()
        self.user, _ = _register_via_otp(self.client, "ssot_upgrade1@example.com", "9000000003")
        self.client.force_authenticate(user=self.user)

    def test_request_upgrade_rejects_non_service_provider_types(self):
        for bad_type in ("TRANSPORTER", "ACCOUNTANT", "CUSTOMER", "NOPE"):
            r = self.client.post(
                "/api/v1/auth/request-upgrade/", {"requested_user_type": bad_type}, format="json",
            )
            self.assertEqual(r.status_code, 400, f"{bad_type} deberia ser rechazado")

    def test_request_upgrade_accepts_service_provider_types(self):
        r = self.client.post(
            "/api/v1/auth/request-upgrade/", {"requested_user_type": "PROFESSIONAL"}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.user.kyc_verification.refresh_from_db()
        self.assertEqual(self.user.kyc_verification.status, UserVerification.STATUS_PENDING)
        self.assertEqual(self.user.kyc_verification.requested_user_type, "PROFESSIONAL")

    def test_customer_keeps_buyer_access_during_upgrade(self):
        self.client.post("/api/v1/auth/request-upgrade/", {"requested_user_type": "PROFESSIONAL"}, format="json")
        r = self.client.get("/api/v1/cart/")
        self.assertNotIn(r.status_code, (401, 403))

    def test_upload_documents_persist_across_requests(self):
        """Puede subir documentos, y si 'sale y vuelve' (nueva request), el progreso sigue ahi."""
        self.client.post("/api/v1/auth/request-upgrade/", {"requested_user_type": "TECHNICIAN"}, format="json")
        r = self.client.post(
            "/api/v1/auth/upload-document/",
            {"doc_type": "CEDULA_FRONTAL", "file": _fake_pdf()}, format="multipart",
        )
        self.assertEqual(r.status_code, 201, r.data)

        # Simula "volver despues": nueva consulta de estado, sin reenviar nada.
        r2 = self.client.get("/api/v1/auth/verification/")
        self.assertEqual(r2.status_code, 200)
        doc_types = [d["doc_type"] for d in r2.data["documents"]]
        self.assertIn("CEDULA_FRONTAL", doc_types)


class PanelValidacionesTestCase(APITestCase):
    """Aprobar/rechazar/solicitar-info desde /panel/validaciones."""

    def setUp(self):
        cache.clear()
        self.admin = _make_admin()
        self.user, _ = _register_via_otp(self.client, "ssot_panel1@example.com", "9000000004")
        KycCommands.request_upgrade(self.user.kyc_verification, "CONTRACTOR", by=self.user)
        self.verification = self.user.kyc_verification
        self.verification.refresh_from_db()
        for doc_type in ("CEDULA_FRONTAL", "CEDULA_REVERSO", "RUT", "HOJA_VIDA", "DIPLOMA"):
            VerificationDocument.objects.create(
                verification=self.verification, doc_type=doc_type, uploaded_by=self.user,
            )
        KycCommands.submit_for_review(self.verification, by=self.user)
        self.client.force_authenticate(user=self.admin)

    def test_reject_preserves_customer_type(self):
        r = self.client.post(
            f"/api/v1/auth/admin/verifications/{self.verification.uuid}/reject/",
            {"reason": "Documentos ilegibles"}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_type, UserProfile.CUSTOMER)

    def test_request_more_info_returns_to_pending(self):
        r = self.client.post(
            f"/api/v1/auth/admin/verifications/{self.verification.uuid}/request-info/",
            {"message": "Falta el RUT legible"}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.verification.refresh_from_db()
        self.assertEqual(self.verification.status, UserVerification.STATUS_PENDING)

    def test_approve_changes_user_type_creates_technician_profile_and_group(self):
        for doc in self.verification.documents.all():
            self.client.post(
                f"/api/v1/auth/admin/verifications/{self.verification.uuid}/documents/{doc.uuid}/review/",
                {"approved": True}, format="json",
            )
        r = self.client.post(
            f"/api/v1/auth/admin/verifications/{self.verification.uuid}/approve/", {}, format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_type, "CONTRACTOR")
        self.assertTrue(TechnicianProfile.objects.filter(user=self.user).exists())
        self.assertTrue(self.user.groups.filter(name="CONTRACTOR").exists())


class MarketplaceVisibilityTestCase(APITestCase):
    """CUSTOMER nunca aparece en el marketplace; solo profesionales aprobados."""

    def setUp(self):
        cache.clear()

    def test_customer_never_in_marketplace(self):
        user, _ = _register_via_otp(self.client, "ssot_market1@example.com", "9000000005")
        self.assertEqual(user.profile.user_type, UserProfile.CUSTOMER)
        r = self.client.get("/api/v1/auth/contractors/")
        emails = [c["email"] for c in r.data.get("results", r.data if isinstance(r.data, list) else [])]
        self.assertNotIn(user.email, emails)

    def test_approved_professional_appears_in_marketplace(self):
        admin = _make_admin("ssot_market_admin@example.com")
        user, _ = _register_via_otp(self.client, "ssot_market2@example.com", "9000000006")
        verification = user.kyc_verification
        KycCommands.request_upgrade(verification, "PROFESSIONAL", by=user)
        KycCommands.force_approve(verification, reviewed_by=admin, note="test")

        r = self.client.get("/api/v1/auth/contractors/")
        emails = [c["email"] for c in r.data.get("results", r.data if isinstance(r.data, list) else [])]
        self.assertIn(user.email, emails)


class SecurityRegressionTestCase(APITestCase):
    """Regresion del hueco de seguridad cerrado: PATCH profile no cambia user_type."""

    def setUp(self):
        cache.clear()
        self.user, _ = _register_via_otp(self.client, "ssot_security1@example.com", "9000000007")
        self.client.force_authenticate(user=self.user)

    def test_patch_profile_does_not_change_user_type(self):
        r = self.client.patch("/api/v1/auth/profile/", {"user_type": "PROFESSIONAL"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.user_type, UserProfile.CUSTOMER)

    def test_user_profile_update_serializer_has_no_user_type_field(self):
        from accounts.api.serializers import UserProfileUpdateSerializer
        self.assertNotIn("user_type", UserProfileUpdateSerializer().fields)


class BasicRegressionSmokeTestCase(APITestCase):
    """Confirma que login/OTP/cart siguen funcionando para un CUSTOMER recien registrado."""

    def setUp(self):
        cache.clear()

    def test_full_register_then_login_then_cart(self):
        email = "ssot_regression1@example.com"
        user, data = _register_via_otp(self.client, email, "9000000008")

        # Login independiente (no solo los tokens del register-verify)
        login_client_user = AccountCommands.authenticate_user(email=email, password="Sintel#2026Segura!")
        self.assertEqual(login_client_user.email, email)

        self.client.force_authenticate(user=user)
        r = self.client.get("/api/v1/cart/")
        self.assertNotIn(r.status_code, (401, 403))
