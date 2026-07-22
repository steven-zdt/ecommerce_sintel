"""
Test suite para el Contractor Marketplace — app accounts.
Cubre:
  - Registro simplificado (Paso 1)
  - Actualización de perfil por pasos (onboarding)
  - Cálculo de promedio de calificaciones (average_rating)
  - Validación de archivos (tamaño y extensión)
  - Permisos de los endpoints API
"""

import io
import datetime
from decimal import Decimal

from django.core.cache import cache
from django.test import TransactionTestCase
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from users.models import User, EmailVerificationCode
from accounts.models import (
    UserProfile,
    TechnicianProfile,
    ContractorSkill,
    AcademicTraining,
    ProfessionalCourse,
    ProfessionalCertification,
    ProfessionalExperience,
    SuccessCase,
    SuccessCaseImage,
    ContractorReview,
)
from accounts.services.commands import AccountCommands, validate_file
from accounts.services.profile_resolver import ProfileResolver
from accounts.exceptions import MissingRequiredProfile, ProfileMismatchError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email, password="Pass@1234!", user_type=UserProfile.TECHNICIAN):
    """Helper que crea un usuario + perfil vía el service layer."""
    return AccountCommands.register_user({
        "email": email,
        "password": password,
        "password_confirm": password,
        "user_type": user_type,
        "first_name": "Test",
        "last_name": "User",
    })


def _register_endpoint_payload(email, numero_documento="1000000001", password="Pass@1234!Segura"):
    """
    Payload completo para POST /api/v1/auth/register/ -- incluye los campos
    obligatorios de KycRegistrationFieldsMixin (identidad + consentimiento
    Habeas Data) y una contrasena que cumple la politica de 12+ caracteres
    con mayuscula/minuscula/numero/especial.
    """
    return {
        "email": email,
        "password": password,
        "password_confirm": password,
        "user_type": UserProfile.TECHNICIAN,
        "phone_number": "3" + numero_documento[-9:],
        "primer_nombre": "Test",
        "primer_apellido": "User",
        "fecha_nacimiento": "1995-06-15",
        "nacionalidad": "Colombiana",
        "pais": "Colombia",
        "ciudad": "Bogota",
        "direccion": "Calle 1 # 2-3",
        "tipo_documento": "CC",
        "numero_documento": numero_documento,
        "fecha_expedicion_documento": "2013-01-01",
        "lugar_expedicion_documento": "Bogota",
        "acepta_politica_tratamiento_datos": True,
        "acepta_autorizacion_tratamiento_datos": True,
        "acepta_terminos_condiciones": True,
    }


def _fake_file(name="archivo.pdf", size_bytes=1024 * 100, content=b"PDF-CONTENT"):
    """Crea un objeto file-like simulado para tests de validación."""
    f = io.BytesIO(content * (size_bytes // len(content) + 1))
    f.seek(0)
    f.name = name
    f.size = size_bytes
    return f


# ===========================================================================
# FASE 1 – Registro simplificado
# ===========================================================================

class RegisterUserTestCase(TransactionTestCase):
    """Verifica el registro de 2 pasos: solo credenciales en el paso 1."""

    def test_register_creates_user_and_profile(self):
        """El registro crea User + UserProfile automáticamente."""
        user = _make_user("contratista01@example.com")

        self.assertIsNotNone(user.pk)
        self.assertTrue(User.objects.filter(email="contratista01@example.com").exists())

        profile = getattr(user, "profile", None)
        self.assertIsNotNone(profile, "UserProfile debe crearse automáticamente")
        self.assertEqual(profile.user_type, UserProfile.TECHNICIAN)

    def test_register_technician_creates_technician_profile(self):
        """Al registrar un TECHNICIAN, se auto-crea su TechnicianProfile."""
        user = _make_user("tecnico01@example.com", user_type=UserProfile.TECHNICIAN)
        self.assertIsNotNone(user.technician_profile)
        self.assertTrue(user.technician_profile.is_available)

    def test_register_professional_type(self):
        """Se puede registrar como PROFESSIONAL."""
        user = _make_user("profesional01@example.com", user_type=UserProfile.PROFESSIONAL)
        self.assertEqual(user.profile.user_type, UserProfile.PROFESSIONAL)

    def test_register_prevents_privilege_escalation(self):
        """El registro nunca otorga is_staff ni is_superuser."""
        data = {
            "email": "hacker@example.com",
            "password": "Pass@1234!",
            "password_confirm": "Pass@1234!",
            "is_staff": True,
            "is_superuser": True,
        }
        user = AccountCommands.register_user(data)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_register_duplicate_email_raises_error(self):
        """El registro con email duplicado falla con ValidationError en la API."""
        _make_user("duplicado@example.com")
        # El serializer valida duplicados; aquí comprobamos la capa DB
        with self.assertRaises(Exception):
            User.objects.create_user(email="duplicado@example.com", password="Pass@1234!")


# ===========================================================================
# FASE 2 – Actualización de perfil (onboarding por pasos)
# ===========================================================================

class OnboardingProfileUpdateTestCase(TransactionTestCase):
    """Simula el wizard de onboarding actualizando el perfil en pasos."""

    def setUp(self):
        self.user = _make_user("onboarding@example.com")
        self.profile = self.user.profile

    def test_step2_update_personal_info(self):
        """Paso 2: actualizar información personal y profesional."""
        data = {
            "first_name": "Carlos",
            "last_name": "Pérez",
            "phone_number": "+573001234567",
            "city": "Bogotá",
            "country": "Colombia",
            "document_type": "CC",
            "document": "12345678",
            "bio": "Técnico electricista con 10 años de experiencia.",
            "hourly_rate": Decimal("80000"),
            "currency": "COP",
        }
        AccountCommands.update_profile(self.user, data)
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.first_name, "Carlos")
        self.assertEqual(self.profile.last_name, "Pérez")
        self.assertEqual(self.profile.city, "Bogotá")
        self.assertEqual(self.profile.hourly_rate, Decimal("80000"))
        self.assertEqual(self.profile.currency, "COP")

    def test_step3_add_skill(self):
        """Paso 3: añadir habilidades."""
        skill = AccountCommands.add_skill(self.profile, name="Python", level="Experto")
        self.assertIsNotNone(skill.pk)
        self.assertEqual(self.profile.contractor_skills.filter(is_deleted=False).count(), 1)

    def test_step3_add_duplicate_skill_updates_level(self):
        """Añadir habilidad duplicada actualiza el nivel sin crear duplicado."""
        AccountCommands.add_skill(self.profile, name="Python", level="Básico")
        AccountCommands.add_skill(self.profile, name="Python", level="Experto")
        skills = self.profile.contractor_skills.filter(name="Python", is_deleted=False)
        self.assertEqual(skills.count(), 1)
        self.assertEqual(skills.first().level, "Experto")

    def test_step3_remove_skill(self):
        """Soft-delete de habilidad."""
        skill = AccountCommands.add_skill(self.profile, name="Django", level="Intermedio")
        AccountCommands.remove_skill(self.profile, skill.id)
        self.assertEqual(
            self.profile.contractor_skills.filter(name="Django", is_deleted=False).count(), 0
        )

    def test_step4_add_experience(self):
        """Paso 4: añadir experiencia laboral."""
        exp = AccountCommands.add_experience(
            user_profile=self.profile,
            company="Acme S.A.S.",
            position="Técnico Senior",
            description="Instalaciones eléctricas industriales.",
            start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2023, 6, 30),
            is_current=False,
        )
        self.assertIsNotNone(exp.pk)
        self.assertEqual(exp.company, "Acme S.A.S.")

    def test_step4_experience_date_validation(self):
        """La fecha de fin no puede ser anterior a la de inicio."""
        with self.assertRaises(ValidationError):
            AccountCommands.add_experience(
                user_profile=self.profile,
                company="Bad Dates Co.",
                position="Dev",
                description="",
                start_date=datetime.date(2023, 1, 1),
                end_date=datetime.date(2022, 1, 1),
                is_current=False,
            )

    def test_step4_add_academic_training(self):
        """Paso 4: añadir formación académica."""
        aca = AccountCommands.add_academic_training(
            user_profile=self.profile,
            institution="Universidad Nacional",
            degree="Ingeniería Eléctrica",
            field_of_study="Energía",
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2015, 12, 31),
            is_current=False,
        )
        self.assertEqual(aca.institution, "Universidad Nacional")

    def test_step4_add_course(self):
        """Paso 4: añadir curso profesional."""
        course = AccountCommands.add_course(
            user_profile=self.profile,
            title="Seguridad Industrial ICONTEC",
            institution="SENA",
            completion_date=datetime.date(2022, 3, 15),
            hours=40,
        )
        self.assertEqual(course.hours, 40)

    def test_step4_add_success_case(self):
        """Paso 4: añadir caso de éxito (portafolio)."""
        case = AccountCommands.add_success_case(
            user_profile=self.profile,
            title="Centro Comercial Éxito — Remodelación eléctrica",
            description="Actualización completa del tablero eléctrico.",
            completion_date=datetime.date(2023, 11, 30),
        )
        self.assertIsNotNone(case.pk)
        self.assertEqual(self.profile.success_cases.filter(is_deleted=False).count(), 1)


# ===========================================================================
# FASE 3 – Cálculo de calificaciones (average_rating)
# ===========================================================================

class RatingCalculationTestCase(TransactionTestCase):
    """Verifica el cálculo del promedio de las 5 dimensiones de calificación."""

    def setUp(self):
        self.contractor = _make_user("contratista_rated@example.com")
        self.profile = self.contractor.profile

        # Creamos 3 revisores diferentes
        self.reviewer1 = _make_user("reviewer1@example.com", user_type=UserProfile.PROFESSIONAL)
        self.reviewer2 = _make_user("reviewer2@example.com", user_type=UserProfile.PROFESSIONAL)
        self.reviewer3 = _make_user("reviewer3@example.com", user_type=UserProfile.PROFESSIONAL)

    def test_average_rating_no_reviews(self):
        """Sin reseñas, el promedio es 0.0."""
        self.assertEqual(self.profile.average_rating, 0.0)
        self.assertEqual(self.profile.total_reviews, 0)

    def test_average_rating_single_perfect_review(self):
        """Una reseña perfecta (5,5,5,5,5) → promedio = 5.0."""
        AccountCommands.add_review(
            contractor=self.profile,
            reviewer=self.reviewer1,
            comment="Excelente trabajo.",
            quality_rating=5,
            punctuality_rating=5,
            professionalism_rating=5,
            communication_rating=5,
            compliance_rating=5,
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.average_rating, 5.0)
        self.assertEqual(self.profile.total_reviews, 1)

    def test_average_rating_multiple_reviews(self):
        """
        Reviewer1: (4,5,4,5,4) → sum=22
        Reviewer2: (3,3,3,3,3) → sum=15
        Total sum = 37, reviews=2, factors=5
        Expected = round(37 / (2*5), 2) = round(3.7, 2) = 3.7
        """
        AccountCommands.add_review(
            contractor=self.profile,
            reviewer=self.reviewer1,
            comment="Muy bien.",
            quality_rating=4,
            punctuality_rating=5,
            professionalism_rating=4,
            communication_rating=5,
            compliance_rating=4,
        )
        AccountCommands.add_review(
            contractor=self.profile,
            reviewer=self.reviewer2,
            comment="Regular.",
            quality_rating=3,
            punctuality_rating=3,
            professionalism_rating=3,
            communication_rating=3,
            compliance_rating=3,
        )
        self.assertEqual(self.profile.total_reviews, 2)
        self.assertAlmostEqual(float(self.profile.average_rating), 3.7, places=2)

    def test_review_prevents_self_review(self):
        """Un contratista no puede reseñarse a sí mismo."""
        with self.assertRaises(ValidationError):
            AccountCommands.add_review(
                contractor=self.profile,
                reviewer=self.contractor,
                comment="Auto-review.",
                quality_rating=5,
                punctuality_rating=5,
                professionalism_rating=5,
                communication_rating=5,
                compliance_rating=5,
            )

    def test_review_rating_out_of_range(self):
        """Calificaciones fuera del rango 1-5 son rechazadas."""
        with self.assertRaises(ValidationError):
            AccountCommands.add_review(
                contractor=self.profile,
                reviewer=self.reviewer1,
                comment="Test.",
                quality_rating=6,   # inválido
                punctuality_rating=1,
                professionalism_rating=1,
                communication_rating=1,
                compliance_rating=1,
            )

    def test_review_update_on_duplicate(self):
        """Una segunda reseña del mismo usuario actualiza la existente (no duplica)."""
        AccountCommands.add_review(
            contractor=self.profile,
            reviewer=self.reviewer1,
            comment="Primera.",
            quality_rating=3,
            punctuality_rating=3,
            professionalism_rating=3,
            communication_rating=3,
            compliance_rating=3,
        )
        AccountCommands.add_review(
            contractor=self.profile,
            reviewer=self.reviewer1,
            comment="Actualizada.",
            quality_rating=5,
            punctuality_rating=5,
            professionalism_rating=5,
            communication_rating=5,
            compliance_rating=5,
        )
        self.assertEqual(self.profile.total_reviews, 1)
        self.assertEqual(self.profile.average_rating, 5.0)


# ===========================================================================
# FASE 4 – Validación de archivos
# ===========================================================================

class FileValidationTestCase(TransactionTestCase):
    """Verifica la función validate_file para certificaciones y portafolios."""

    def test_valid_pdf_file_passes(self):
        """Un PDF de 1MB es válido."""
        f = _fake_file(name="cert.pdf", size_bytes=1 * 1024 * 1024)
        try:
            validate_file(f, max_size_mb=5, allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'])
        except ValidationError:
            self.fail("validate_file levantó ValidationError para un PDF válido.")

    def test_valid_jpg_file_passes(self):
        """Un JPG de 2MB es válido."""
        f = _fake_file(name="foto.jpg", size_bytes=2 * 1024 * 1024)
        try:
            validate_file(f, max_size_mb=5)
        except ValidationError:
            self.fail("validate_file levantó ValidationError para un JPG válido.")

    def test_oversized_file_raises_error(self):
        """Un archivo de 6MB supera el límite de 5MB."""
        f = _fake_file(name="grande.pdf", size_bytes=6 * 1024 * 1024)
        with self.assertRaises(ValidationError) as ctx:
            validate_file(f, max_size_mb=5)
        self.assertIn("5MB", str(ctx.exception))

    def test_invalid_extension_raises_error(self):
        """Extensiones no permitidas (ej. .exe) son rechazadas."""
        f = _fake_file(name="malware.exe", size_bytes=100 * 1024)
        with self.assertRaises(ValidationError) as ctx:
            validate_file(f, allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'])
        self.assertIn(".exe", str(ctx.exception))

    def test_docx_blocked_by_default(self):
        """Por defecto .docx no está permitido."""
        f = _fake_file(name="documento.docx", size_bytes=500 * 1024)
        with self.assertRaises(ValidationError):
            validate_file(f)

    def test_none_file_passes_silently(self):
        """None es válido (campo opcional)."""
        try:
            validate_file(None)
        except ValidationError:
            self.fail("validate_file levantó error para un archivo None (campo opcional).")


# ===========================================================================
# FASE 5 – Permisos de la API REST
# ===========================================================================

class ContractorAPIPermissionsTestCase(APITestCase):
    """Verifica los permisos de los endpoints del marketplace de contratistas."""

    def setUp(self):
        # Los tests de /register/ estan sujetos a ScopedRateThrottle(scope='register');
        # limpiar el cache evita que el conteo se acumule entre tests o con
        # corridas anteriores en el mismo backend de cache.
        cache.clear()
        self.contractor_user = _make_user("api_contractor@example.com")
        self.contractor_profile = self.contractor_user.profile

        self.other_user = _make_user("api_other@example.com", user_type=UserProfile.PROFESSIONAL)

    # ── Listado público (GET /accounts/contractors/) ────────────────────────

    def test_list_contractors_anonymous_ok(self):
        """El listado de contratistas es público."""
        response = self.client.get("/api/v1/auth/contractors/")
        self.assertEqual(response.status_code, 200)

    def test_list_contractors_returns_marketplace_types(self):
        """Solo aparecen perfiles TECHNICIAN, PROFESSIONAL, SPECIALIST."""
        # Crear un admin user (no debe aparecer en el listado)
        admin = User.objects.create_superuser(
            email="admin_api_test@example.com",
            password="AdminPass@1234!"
        )
        UserProfile.objects.create(
            user=admin,
            first_name="Admin",
            last_name="Test",
            user_type="ADMIN"  # No es un tipo de marketplace
        )
        response = self.client.get("/api/v1/auth/contractors/")
        self.assertEqual(response.status_code, 200)
        # Los perfiles retornados NO deben incluir al admin
        uuids = [item.get("uuid") for item in response.data.get("results", response.data)]
        admin_profile = getattr(admin, "profile", None)
        if admin_profile:
            self.assertNotIn(str(admin_profile.uuid), uuids)

    # ── Detalle público (GET /accounts/contractors/{uuid}/) ─────────────────

    def test_get_contractor_detail_anonymous_ok(self):
        """El detalle de un contratista es público."""
        uuid = str(self.contractor_profile.uuid)
        response = self.client.get(f"/api/v1/auth/contractors/{uuid}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["uuid"], uuid)

    def test_get_contractor_detail_hides_document(self):
        """El perfil público NO expone el número de documento."""
        AccountCommands.update_profile(self.contractor_user, {
            "document": "98765432",
            "document_type": "CC"
        })
        uuid = str(self.contractor_profile.uuid)
        response = self.client.get(f"/api/v1/auth/contractors/{uuid}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("document", response.data)

    # ── Añadir reseña (POST /accounts/contractors/{uuid}/review/) ───────────

    def test_add_review_requires_auth(self):
        """Añadir reseña requiere estar autenticado."""
        uuid = str(self.contractor_profile.uuid)
        response = self.client.post(f"/api/v1/auth/contractors/{uuid}/review/", {
            "quality_rating": 5,
            "punctuality_rating": 5,
            "professionalism_rating": 5,
            "communication_rating": 5,
            "compliance_rating": 5,
            "comment": "Sin auth",
        })
        self.assertEqual(response.status_code, 401)

    def test_add_review_authenticated_ok(self):
        """Un usuario autenticado puede reseñar a un contratista."""
        self.client.force_authenticate(user=self.other_user)
        uuid = str(self.contractor_profile.uuid)
        response = self.client.post(f"/api/v1/auth/contractors/{uuid}/review/", {
            "quality_rating": 4,
            "punctuality_rating": 4,
            "professionalism_rating": 4,
            "communication_rating": 4,
            "compliance_rating": 4,
            "comment": "Buen trabajo.",
        })
        self.assertEqual(response.status_code, 201)
        self.contractor_profile.refresh_from_db()
        self.assertEqual(self.contractor_profile.total_reviews, 1)

    # ── Gestión de habilidades (POST /accounts/contractor-skills/) ──────────

    def test_add_skill_requires_auth(self):
        """Añadir habilidades requiere autenticación."""
        response = self.client.post("/api/v1/auth/skills/", {
            "name": "Electricidad",
            "level": "Experto"
        })
        self.assertIn(response.status_code, [401, 403])

    def test_add_skill_authenticated_ok(self):
        """Un contratista autenticado puede añadir habilidades."""
        self.client.force_authenticate(user=self.contractor_user)
        response = self.client.post("/api/v1/auth/skills/", {
            "name": "Fontanería",
            "level": "Intermedio"
        })
        self.assertEqual(response.status_code, 201)

    def test_skill_isolation_between_users(self):
        """Un usuario no puede ver ni borrar habilidades de otro usuario."""
        skill = AccountCommands.add_skill(self.contractor_profile, "Carpintería", "Básico")

        # other_user intenta borrar la habilidad del contractor
        self.client.force_authenticate(user=self.other_user)
        response = self.client.delete(f"/api/v1/auth/skills/{skill.id}/")
        self.assertEqual(response.status_code, 404)

    # ── Registro via API ─────────────────────────────────────────────────────

    def test_register_endpoint_creates_user(self):
        """El endpoint de registro crea un usuario y retorna 201."""
        response = self.client.post(
            "/api/v1/auth/register/",
            _register_endpoint_payload("nuevo_api@example.com", numero_documento="1000000010"),
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="nuevo_api@example.com").exists())

    def test_register_endpoint_duplicate_email_fails(self):
        """El registro con email duplicado retorna 400."""
        payload = _register_endpoint_payload("duplicado_api@example.com", numero_documento="1000000011")
        self.client.post("/api/v1/auth/register/", payload)
        response = self.client.post("/api/v1/auth/register/", payload)
        self.assertEqual(response.status_code, 400)

    def test_register_password_mismatch_fails(self):
        """Contraseñas que no coinciden retornan 400."""
        payload = _register_endpoint_payload("mismatch@example.com", numero_documento="1000000012")
        payload["password_confirm"] = "OtraClaveDiferente#9"
        response = self.client.post("/api/v1/auth/register/", payload)
        self.assertEqual(response.status_code, 400)


# ===========================================================================
# ProfileResolver — Fase fundacional de arquitectura de perfiles (2026-07-05)
# ===========================================================================

class ProfileResolverTestCase(TransactionTestCase):
    """
    Cubre accounts.services.profile_resolver.ProfileResolver: punto único de acceso a
    user.profile / user.technician_profile / user.dispatcher_profile.
    """

    def setUp(self):
        self.technician = _make_user("resolver_tech@example.com", user_type=UserProfile.TECHNICIAN)
        self.customer = _make_user("resolver_customer@example.com", user_type=UserProfile.CUSTOMER)

        self.bare_user = User.objects.create_user(
            email="resolver_bare@example.com", password="Pass@1234!", is_active=True,
        )

    def test_get_profile_returns_profile_when_exists(self):
        profile = ProfileResolver.get_profile(self.technician)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.user_type, UserProfile.TECHNICIAN)

    def test_get_profile_returns_none_without_crashing(self):
        self.assertIsNone(ProfileResolver.get_profile(self.bare_user))

    def test_resolve_raises_missing_profile(self):
        with self.assertRaises(MissingRequiredProfile):
            ProfileResolver.resolve(self.bare_user)

    def test_resolve_raises_mismatch_when_type_not_expected(self):
        with self.assertRaises(ProfileMismatchError):
            ProfileResolver.resolve(self.customer, expected_types={UserProfile.TECHNICIAN})

    def test_resolve_returns_profile_when_type_matches(self):
        profile = ProfileResolver.resolve(self.technician, expected_types={UserProfile.TECHNICIAN})
        self.assertEqual(profile.user, self.technician)

    def test_get_type_and_has_type(self):
        self.assertEqual(ProfileResolver.get_type(self.technician), UserProfile.TECHNICIAN)
        self.assertIsNone(ProfileResolver.get_type(self.bare_user))
        self.assertTrue(ProfileResolver.has_type(self.technician, {UserProfile.TECHNICIAN, UserProfile.PROFESSIONAL}))
        self.assertFalse(ProfileResolver.has_type(self.customer, {UserProfile.TECHNICIAN}))
        self.assertFalse(ProfileResolver.has_type(self.bare_user, {UserProfile.TECHNICIAN}))

    def test_technician_profile_resolution(self):
        # El signal post_save crea TechnicianProfile automaticamente para user_type=TECHNICIAN.
        tp = ProfileResolver.get_technician_profile(self.technician)
        self.assertIsNotNone(tp)
        self.assertEqual(ProfileResolver.resolve_technician(self.technician), tp)

        with self.assertRaises(MissingRequiredProfile):
            ProfileResolver.resolve_technician(self.customer)

    def test_dispatcher_profile_resolution(self):
        from operations.models import DispatcherProfile

        with self.assertRaises(MissingRequiredProfile):
            ProfileResolver.resolve_dispatcher(self.customer)

        dispatcher_user = User.objects.create_user(
            email="resolver_dispatcher@example.com", password="Pass@1234!", is_active=True,
        )
        dp = DispatcherProfile.objects.create(user=dispatcher_user, dispatcher_type=DispatcherProfile.DRIVER)
        self.assertEqual(ProfileResolver.resolve_dispatcher(dispatcher_user), dp)


# ===========================================================================
# Marketplace de Contratistas + Asignación de Técnicos (2026-07-05)
# ===========================================================================

class TechnicianProfileSignalGeneralizationTestCase(TransactionTestCase):
    """El signal post_save de UserProfile crea TechnicianProfile para los 4 tipos service-provider."""

    def test_technician_profile_created_for_all_service_provider_types(self):
        for user_type in (UserProfile.TECHNICIAN, UserProfile.PROFESSIONAL,
                           UserProfile.SPECIALIST, UserProfile.CONTRACTOR):
            user = _make_user(f"sp_{user_type.lower()}@example.com", user_type=user_type)
            self.assertTrue(
                TechnicianProfile.objects.filter(user=user).exists(),
                f"No se creó TechnicianProfile para user_type={user_type}",
            )

    def test_technician_profile_not_created_for_customer(self):
        user = _make_user("sp_customer@example.com", user_type=UserProfile.CUSTOMER)
        self.assertFalse(TechnicianProfile.objects.filter(user=user).exists())


class ContractorAdminSelectorTestCase(TransactionTestCase):
    """ContractorAdminSelector.list_all_for_admin/get_metrics — panel /panel/profesionales."""

    def setUp(self):
        from accounts.services.selectors import ContractorAdminSelector
        self.selector = ContractorAdminSelector

        self.contractor = _make_user("admin_sel_contractor@example.com", user_type=UserProfile.CONTRACTOR)
        self.technician = _make_user("admin_sel_tech@example.com", user_type=UserProfile.TECHNICIAN)
        self.customer = _make_user("admin_sel_customer@example.com", user_type=UserProfile.CUSTOMER)

        # Inactivo: no debe desaparecer del listado admin (a diferencia del marketplace público).
        self.technician.is_active = False
        self.technician.save(update_fields=['is_active'])

    def test_list_all_for_admin_excludes_non_service_provider_types(self):
        qs = self.selector.list_all_for_admin()
        users = [p.user for p in qs]
        self.assertIn(self.contractor, users)
        self.assertNotIn(self.customer, users)

    def test_list_all_for_admin_includes_inactive_users(self):
        """A diferencia del marketplace público, el admin ve perfiles inactivos."""
        qs = self.selector.list_all_for_admin()
        self.assertIn(self.technician, [p.user for p in qs])

    def test_list_all_for_admin_filters_by_is_active(self):
        qs = self.selector.list_all_for_admin(is_active='false')
        users = [p.user for p in qs]
        self.assertIn(self.technician, users)
        self.assertNotIn(self.contractor, users)

    def test_get_metrics_counts_by_type(self):
        metrics = self.selector.get_metrics()
        self.assertGreaterEqual(metrics['total'], 2)
        self.assertIn(UserProfile.CONTRACTOR, metrics['by_type'])
        self.assertIn(UserProfile.TECHNICIAN, metrics['by_type'])


class SetTechnicianAvailabilityCommandTestCase(TransactionTestCase):
    """AccountCommands.set_technician_availability — usado por AdminContractorViewSet.toggle_availability."""

    def setUp(self):
        self.contractor = _make_user("avail_contractor@example.com", user_type=UserProfile.CONTRACTOR)

    def test_set_technician_availability_updates_profile(self):
        profile = AccountCommands.set_technician_availability(self.contractor, False)
        self.assertFalse(profile.is_available)
        profile = AccountCommands.set_technician_availability(self.contractor, True)
        self.assertTrue(profile.is_available)

    def test_set_technician_availability_raises_without_profile(self):
        customer = _make_user("avail_customer@example.com", user_type=UserProfile.CUSTOMER)
        with self.assertRaises(ValidationError):
            AccountCommands.set_technician_availability(customer, True)


class AdminContractorViewSetTestCase(APITestCase):
    """Endpoints de /api/v1/auth/admin/professionals/ — solo accesibles por admin."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin_professionals@example.com", password="AdminPass@1234!",
        )
        self.contractor = _make_user("panel_contractor@example.com", user_type=UserProfile.CONTRACTOR)
        self.other_user = _make_user("panel_other@example.com", user_type=UserProfile.PROFESSIONAL)

    def test_list_requires_admin(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/v1/auth/admin/professionals/")
        self.assertEqual(response.status_code, 403)

    def test_list_ok_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/auth/admin/professionals/")
        self.assertEqual(response.status_code, 200)

    def test_metrics_ok_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/v1/auth/admin/professionals/metrics/")
        self.assertEqual(response.status_code, 200)
        self.assertIn('total', response.data)
        self.assertIn('by_type', response.data)

    def test_toggle_availability_ok_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        uuid = str(self.contractor.profile.uuid)
        response = self.client.patch(
            f"/api/v1/auth/admin/professionals/{uuid}/toggle-availability/",
            {"is_available": False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_available'])

    def test_toggle_availability_requires_boolean(self):
        self.client.force_authenticate(user=self.admin)
        uuid = str(self.contractor.profile.uuid)
        response = self.client.patch(
            f"/api/v1/auth/admin/professionals/{uuid}/toggle-availability/",
            {"is_available": "not-a-bool"},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_schedule_ok_for_admin(self):
        self.client.force_authenticate(user=self.admin)
        uuid = str(self.contractor.profile.uuid)
        response = self.client.get(f"/api/v1/auth/admin/professionals/{uuid}/schedule/")
        self.assertEqual(response.status_code, 200)


class CustomerForgotPasswordTestCase(APITestCase):
    """Flujo self-service de recuperacion de contrasena para clientes (is_staff=False)."""

    def setUp(self):
        cache.clear()
        self.customer = User.objects.create_user(
            email='forgot_password_customer@example.com', password='OldPass123!',
        )
        self.admin = User.objects.create_superuser(
            email='forgot_password_admin_email@example.com', password='OldPass123!',
        )

    def _latest_code(self, email, purpose=EmailVerificationCode.PURPOSE_PASSWORD_RESET_CUSTOMER):
        return (
            EmailVerificationCode.objects
            .filter(email=email, purpose=purpose)
            .order_by('-created_at')
            .first()
        )

    def test_full_reset_flow_and_auto_login(self):
        r1 = self.client.post(
            '/api/v1/auth/forgot-password-request/', {'email': self.customer.email}, format='json',
        )
        self.assertEqual(r1.status_code, 200)

        code_obj = self._latest_code(self.customer.email)
        self.assertIsNotNone(code_obj)

        r2 = self.client.post(
            '/api/v1/auth/forgot-password-verify/',
            {'email': self.customer.email, 'code': code_obj.code},
            format='json',
        )
        self.assertEqual(r2.status_code, 200)

        r3 = self.client.post(
            '/api/v1/auth/forgot-password-reset/',
            {
                'email': self.customer.email,
                'code': code_obj.code,
                'new_password': 'BrandNewPass456!',
                'new_password_confirm': 'BrandNewPass456!',
            },
            format='json',
        )
        self.assertEqual(r3.status_code, 200)
        self.assertIn('tokens', r3.data)

        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('BrandNewPass456!'))
        self.assertFalse(self.customer.check_password('OldPass123!'))

    def test_request_is_generic_for_unknown_email(self):
        response = self.client.post(
            '/api/v1/auth/forgot-password-request/',
            {'email': 'no_such_user@example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(EmailVerificationCode.objects.filter(email='no_such_user@example.com').first())

    def test_wrong_code_is_rejected(self):
        self.client.post(
            '/api/v1/auth/forgot-password-request/', {'email': self.customer.email}, format='json',
        )
        response = self.client.post(
            '/api/v1/auth/forgot-password-verify/',
            {'email': self.customer.email, 'code': '000000'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_staff_email_cannot_be_reset_via_customer_endpoint(self):
        r1 = self.client.post(
            '/api/v1/auth/forgot-password-request/', {'email': self.admin.email}, format='json',
        )
        # Respuesta generica identica (no revela que es una cuenta admin)...
        self.assertEqual(r1.status_code, 200)
        # ...pero no se genero ningun codigo real para esa cuenta.
        self.assertIsNone(self._latest_code(self.admin.email))

        response = self.client.post(
            '/api/v1/auth/forgot-password-reset/',
            {
                'email': self.admin.email,
                'code': '123456',
                'new_password': 'ShouldNotWork456!',
                'new_password_confirm': 'ShouldNotWork456!',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('OldPass123!'))
