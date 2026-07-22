import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from users.models import User
from accounts.models import (
    UserProfile, TechnicianProfile,
    ContractorSpecialty, ContractorSkill, AcademicTraining,
    ProfessionalCourse, ProfessionalCertification, ProfessionalExperience,
    SuccessCase, SuccessCaseImage, ContractorReview,
    ProfessionalAvailability,
)
from technical_services.models import ServiceCategory
from kyc.api.serializers import KycRegistrationFieldsMixin

_PHONE_MOBILE_RE = re.compile(r'^3\d{9}$')       # celular: 10 digitos, empieza en 3
_PHONE_LANDLINE_NEW_RE = re.compile(r'^6\d{9}$')  # fijo con indicativo nuevo: 10 digitos, empieza en 6
_PHONE_LANDLINE_OLD_RE = re.compile(r'^\d{7}$')   # fijo local antiguo: 7 digitos


def validate_colombian_phone_number(value: str) -> str:
    """
    Acepta celular (10 digitos, ej. 3001234567) o fijo (7 digitos locales, o
    10 digitos con indicativo, ej. 6011234567) en el mismo campo. Tolera
    espacios/guiones y un prefijo de pais +57/57 opcional.
    """
    digits = re.sub(r'\D', '', value or '')
    if digits.startswith('57') and len(digits) > 10:
        digits = digits[2:]
    if _PHONE_MOBILE_RE.match(digits) or _PHONE_LANDLINE_NEW_RE.match(digits) or _PHONE_LANDLINE_OLD_RE.match(digits):
        return value
    raise serializers.ValidationError(
        "Ingresa un numero de telefono valido: celular (10 digitos, ej. 3001234567) "
        "o fijo (7 digitos locales, o 10 digitos con indicativo, ej. 6011234567)."
    )


def validate_phone_number_available(value: str) -> str:
    """
    Formato + unicidad (UserProfile.phone_number es unique=True). Antes esta
    colision solo se descubria en register-verify (creacion de cuenta), obligando
    a gastar un OTP -- correo enviado, codigo generado -- para un dato que ya se
    sabia invalido desde el paso 1. Validar unicidad aqui, en register-request/
    register (antes de emitir el OTP), evita ese desperdicio y le muestra el
    error al usuario de inmediato, sin pasar por la pantalla de verificacion.
    """
    validate_colombian_phone_number(value)
    if UserProfile.objects.filter(phone_number=value).exists():
        raise serializers.ValidationError("Este numero de telefono ya esta registrado con otra cuenta.")
    return value


class UserRegisterSerializer(KycRegistrationFieldsMixin, serializers.Serializer):
    """
    Registro publico de nuevos usuarios. Campos de identidad/consentimiento
    KYC via KycRegistrationFieldsMixin -- ver kyc/api/serializers.py.
    `user_type` NO es client-suppliable aqui a proposito -- todo registro
    publico crea siempre un CUSTOMER (ver AccountCommands.register_user).
    Convertirse en profesional es un upgrade posterior via
    KycCommands.request_upgrade(), no una eleccion en el registro.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=20)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo ya esta registrado.")
        return value

    def validate_phone_number(self, value):
        return validate_phone_number_available(value)

    def validate(self, data):
        data = super().validate(data)
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Las contrasenas no coinciden."})
        return data


class RegisterRequestSerializer(KycRegistrationFieldsMixin, serializers.Serializer):
    """
    Paso 1 del registro OTP: recoge datos completos y dispara el envio del
    codigo. Campos de identidad/consentimiento KYC via KycRegistrationFieldsMixin
    -- ver kyc/api/serializers.py.
    `user_type` NO es client-suppliable aqui a proposito -- todo registro
    publico crea siempre un CUSTOMER (ver AccountCommands.create_from_verified_payload).
    Convertirse en profesional es un upgrade posterior via
    KycCommands.request_upgrade(), no una eleccion en el registro.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=20)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este correo ya esta registrado.")
        return value

    def validate_phone_number(self, value):
        return validate_phone_number_available(value)

    def validate(self, data):
        data = super().validate(data)
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Las contrasenas no coinciden."})
        return data


class VerifyCodeSerializer(serializers.Serializer):
    """Paso 2 del registro OTP: verifica el codigo recibido por correo."""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El codigo debe contener solo digitos.")
        return value


class ResendCodeSerializer(serializers.Serializer):
    """Solicitud de reenvio del codigo OTP."""
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class ForgotPasswordRequestSerializer(serializers.Serializer):
    """Paso 1 de recuperacion de contrasena: solicita el envio del codigo OTP."""
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class ResetPasswordSerializer(serializers.Serializer):
    """Paso 3 de recuperacion de contrasena: codigo OTP + nueva contrasena."""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()

    def validate_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("El codigo debe contener solo digitos.")
        return value

    def validate(self, data):
        data = super().validate(data)
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "Las contrasenas no coinciden."})
        return data


class VerifyEmailLinkSerializer(serializers.Serializer):
    """Token firmado del enlace de verificacion de correo (usuario ya existente)."""
    token = serializers.CharField()


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        return value.lower().strip()


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ('id', 'name', 'slug')


class ContractorSpecialtySerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ContractorSpecialty
        fields = ('id', 'category', 'category_id')


class ContractorSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractorSkill
        fields = ('id', 'name', 'level')


class AcademicTrainingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTraining
        fields = ('id', 'institution', 'degree', 'field_of_study', 'start_date', 'end_date', 'is_current')


class ProfessionalCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalCourse
        fields = ('id', 'title', 'institution', 'completion_date', 'hours')


class ProfessionalCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalCertification
        fields = ('id', 'name', 'issuing_organization', 'issue_date', 'expiration_date', 'credential_id', 'credential_url', 'document')


class ProfessionalExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalExperience
        fields = ('id', 'company', 'position', 'description', 'start_date', 'end_date', 'is_current')


class SuccessCaseImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessCaseImage
        fields = ('id', 'image', 'is_before', 'is_after')


class SuccessCaseSerializer(serializers.ModelSerializer):
    images = SuccessCaseImageSerializer(many=True, read_only=True)

    class Meta:
        model = SuccessCase
        fields = ('id', 'title', 'description', 'completion_date', 'images')


class ContractorReviewSerializer(serializers.ModelSerializer):
    reviewer_email = serializers.EmailField(source='reviewer.email', read_only=True)
    reviewer_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ContractorReview
        fields = (
            'id', 'reviewer_email', 'reviewer_name', 'comment',
            'quality_rating', 'punctuality_rating', 'professionalism_rating',
            'communication_rating', 'compliance_rating', 'created_at'
        )

    def get_reviewer_name(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(obj.reviewer)
        if profile:
            return profile.get_full_name()
        return obj.reviewer.email


class PublicContractorProfileSerializer(serializers.ModelSerializer):
    specialties = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    academic_trainings = serializers.SerializerMethodField()
    professional_courses = serializers.SerializerMethodField()
    professional_certifications = serializers.SerializerMethodField()
    professional_experiences = serializers.SerializerMethodField()
    success_cases = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            'uuid', 'user_uuid', 'first_name', 'last_name', 'email', 'profile_picture',
            'user_type', 'contractor_type', 'bio',
            'hourly_rate', 'daily_rate', 'project_rate', 'currency',
            'average_rating', 'total_reviews', 'total_services_completed',
            'specialties', 'skills', 'academic_trainings', 'professional_courses',
            'professional_certifications', 'professional_experiences',
            'success_cases', 'reviews'
        )
        # Este serializer solo se usa hoy en acciones de lectura (ReadOnlyModelViewSet),
        # pero user_type se marca read_only explicitamente como defensa en profundidad --
        # el unico camino autorizado para cambiarlo es KycCommands._apply_requested_user_type().
        read_only_fields = ('user_type',)

    # Todos filtran en Python sobre .all() para reusar el cache de prefetch_related que
    # arman ContractorSearchSelector/ContractorRecommendationSelector -- un .filter()
    # explicito aqui dispara una consulta nueva por cada perfil listado (N+1).

    def get_specialties(self, obj):
        specs = [s for s in obj.contractor_specialties.all() if not s.is_deleted]
        return ContractorSpecialtySerializer(specs, many=True).data

    def get_skills(self, obj):
        skills = [s for s in obj.contractor_skills.all() if not s.is_deleted]
        return ContractorSkillSerializer(skills, many=True).data

    def get_academic_trainings(self, obj):
        trainings = [t for t in obj.academic_trainings.all() if not t.is_deleted]
        return AcademicTrainingSerializer(trainings, many=True).data

    def get_professional_courses(self, obj):
        courses = [c for c in obj.professional_courses.all() if not c.is_deleted]
        return ProfessionalCourseSerializer(courses, many=True).data

    def get_professional_certifications(self, obj):
        certs = [c for c in obj.professional_certifications.all() if not c.is_deleted]
        return ProfessionalCertificationSerializer(certs, many=True).data

    def get_professional_experiences(self, obj):
        exps = [e for e in obj.professional_experiences.all() if not e.is_deleted]
        return ProfessionalExperienceSerializer(exps, many=True).data

    def get_success_cases(self, obj):
        cases = [c for c in obj.success_cases.all() if not c.is_deleted]
        return SuccessCaseSerializer(cases, many=True).data

    def get_reviews(self, obj):
        reviews = [r for r in obj.contractor_reviews.all() if not r.is_deleted]
        return ContractorReviewSerializer(reviews, many=True).data


class AdminContractorSerializer(serializers.ModelSerializer):
    """Listado liviano para el panel administrativo de profesionales (/panel/profesionales)."""
    user_uuid = serializers.UUIDField(source='user.uuid', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    is_available = serializers.SerializerMethodField()
    specialties_count = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            'uuid', 'user_uuid', 'full_name', 'email', 'user_type', 'city',
            'is_active', 'is_available', 'hourly_rate', 'currency',
            'average_rating', 'total_reviews', 'total_services_completed',
            'specialties_count', 'created_at',
        )
        # Defensa en profundidad: hoy este serializer solo alimenta acciones
        # de lectura de AdminContractorViewSet, pero user_type se marca
        # read_only explicitamente -- unico camino autorizado para cambiarlo:
        # KycCommands._apply_requested_user_type().
        read_only_fields = ('user_type',)

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_is_available(self, obj):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_technician_profile(obj.user)
        return bool(profile and profile.is_available)

    def get_specialties_count(self, obj):
        return len([s for s in obj.contractor_specialties.all() if not s.is_deleted])


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    `user_type` NO es editable aqui a proposito -- el unico camino valido
    para cambiarlo es KycCommands.request_upgrade() + aprobacion admin (ver
    kyc/CLAUDE.md, "SSoT de identidad"). Antes de este cambio, cualquier
    CUSTOMER autenticado podia auto-ascenderse a PROFESSIONAL con un PATCH
    directo, sin KYC ni aprobacion -- hueco de seguridad cerrado aqui.
    """
    class Meta:
        model = UserProfile
        fields = (
            'first_name', 'last_name', 'phone_number', 'document_type', 'document',
            'profile_picture', 'company', 'position',
            'address', 'city', 'state', 'country', 'postal_code',
            'birth_date', 'contractor_type', 'bio',
            'hourly_rate', 'daily_rate', 'project_rate', 'currency',
        )

    def validate_phone_number(self, value):
        """
        Normaliza '' -> None: phone_number es unique=True a nivel de BD, y una
        cadena vacia (a diferencia de NULL) SI colisiona con otra cadena vacia
        bajo esa constraint -- causaba IntegrityError 500 en cualquier segundo
        usuario que guardara el perfil con telefono en blanco (auditoria QA
        2026-07-19). Si viene un valor, se valida formato + unicidad excluyendo
        el propio perfil (edicion de un numero ya guardado no debe auto-chocar).
        """
        value = (value or '').strip()
        if not value:
            return None
        validate_colombian_phone_number(value)
        qs = UserProfile.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este numero de telefono ya esta registrado con otra cuenta.')
        return value


# ─── Availability Serializers ────────────────────────────────────────────────

class AvailabilityOutputSerializer(serializers.ModelSerializer):
    """Representacion publica de un slot de disponibilidad."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model  = ProfessionalAvailability
        fields = (
            'id', 'date', 'start_time', 'end_time',
            'status', 'status_display', 'notes',
        )
        read_only_fields = fields


class AvailabilityBulkCreateSerializer(serializers.Serializer):
    """Input para generacion masiva de slots."""
    start_date          = serializers.DateField()
    end_date            = serializers.DateField()
    work_start_hour     = serializers.IntegerField(default=8, min_value=0, max_value=23)
    work_end_hour       = serializers.IntegerField(default=18, min_value=1, max_value=24)
    slot_duration_hours = serializers.IntegerField(default=2, min_value=1, max_value=12)
    exclude_weekends    = serializers.BooleanField(default=True)
    notes               = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError(
                "start_date debe ser anterior o igual a end_date."
            )
        if attrs['work_start_hour'] >= attrs['work_end_hour']:
            raise serializers.ValidationError(
                "work_start_hour debe ser anterior a work_end_hour."
            )
        return attrs


class AvailabilityStatusUpdateSerializer(serializers.Serializer):
    """Input para que el profesional cambie el estado de un slot manualmente."""
    ALLOWED_STATUSES = [
        ProfessionalAvailability.AVAILABLE,
        ProfessionalAvailability.BLOCKED,
        ProfessionalAvailability.VACATION,
        ProfessionalAvailability.SICK_LEAVE,
    ]
    status = serializers.ChoiceField(choices=[(s, s) for s in ALLOWED_STATUSES]
    )
