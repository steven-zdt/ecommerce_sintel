import logging
import os
import secrets
import string
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import User, EmailVerificationCode, UserAuditLog
from users.services.commands import VerificationCommands, UserAuditCommands
from accounts.models import (
    UserProfile, TechnicianProfile,
    ContractorSpecialty, ContractorSkill, AcademicTraining,
    ProfessionalCourse, ProfessionalCertification, ProfessionalExperience,
    SuccessCase, SuccessCaseImage, ContractorReview,
    ProfessionalAvailability,
)
from technical_services.models import ServiceCategory

logger = logging.getLogger(__name__)

_TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits + '!@#$%'
_EMAIL_VERIFICATION_SALT = 'email-verification'
_EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24  # 24 horas


_MAGIC_BYTES = {
    '.pdf': b'%PDF',
    '.jpg': b'\xff\xd8\xff',
    '.jpeg': b'\xff\xd8\xff',
    '.png': b'\x89PNG',
}


def _log_file_rejected(file, reason: str) -> None:
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(
        SecurityEvent.FILE_REJECTED, severity=SecurityEvent.SEVERITY_WARNING,
        metadata={'filename': getattr(file, 'name', ''), 'reason': reason},
    )


def validate_file(file, max_size_mb=5, allowed_extensions=None, magic_bytes_check=False):
    if not file:
        return
    if allowed_extensions is None:
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']

    # Check size
    if file.size > max_size_mb * 1024 * 1024:
        reason = f"El archivo supera el limite permitido de {max_size_mb}MB."
        _log_file_rejected(file, reason)
        raise ValidationError(reason)

    # Check extension
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        reason = f"El formato del archivo {ext} no esta permitido. Permitidos: {', '.join(allowed_extensions)}"
        _log_file_rejected(file, reason)
        raise ValidationError(reason)

    # Nunca confiar solo en el nombre/extension declarados por el cliente --
    # verificar los primeros bytes reales del archivo (magic bytes).
    if magic_bytes_check:
        expected = _MAGIC_BYTES.get(ext)
        if expected:
            header = file.read(len(expected))
            file.seek(0)
            if header != expected:
                reason = f"El contenido del archivo no coincide con la extension {ext} declarada."
                _log_file_rejected(file, reason)
                raise ValidationError(reason)


def _pop_kyc_registration_data(data: dict) -> dict:
    """
    Extrae del payload de registro (dict mutable) los campos KYC-only, los
    campos que van a UserProfile pero que register_user/create_from_verified_payload
    no manejaban antes, y los 3 eventos de consentimiento Habeas Data. Usado
    por register_user() y create_from_verified_payload().

    has_kyc_data indica si el caller realmente vino del flujo publico de
    autoregistro (via KycRegistrationFieldsMixin -- trae 'primer_nombre').
    Si es False (creacion admin via UserAdminCreateSerializer, o codigo/tests
    internos que llaman a register_user con el dict plano de siempre:
    first_name/last_name), el caller debe tratar la cuenta como ya confiable
    (bootstrap_approved) en vez de exigirle el flujo KYC completo -- de lo
    contrario un admin no podria crear cuentas operativas de inmediato desde
    /panel/usuarios.

    Retorna dict con: first_name, last_name (derivados o heredados),
    profile_extra (dict), kyc_fields (dict para UserVerification),
    consent_events (list), has_kyc_data (bool).
    """
    from kyc.services.config import CURRENT_CONSENT_DOCUMENT_VERSION

    has_kyc_data = 'primer_nombre' in data

    # Compatibilidad con callers que aun crean cuentas con el shape plano
    # first_name/last_name (UserAdminCreateSerializer, fixtures de tests).
    legacy_first_name = data.pop('first_name', '')
    legacy_last_name = data.pop('last_name', '')

    primer_nombre = data.pop('primer_nombre', '')
    segundo_nombre = data.pop('segundo_nombre', '')
    primer_apellido = data.pop('primer_apellido', '')
    segundo_apellido = data.pop('segundo_apellido', '')

    profile_extra = {
        'country': data.pop('pais', ''),
        'city': data.pop('ciudad', ''),
        'address': data.pop('direccion', ''),
        'birth_date': data.pop('fecha_nacimiento', None),
        'document_type': data.pop('tipo_documento', ''),
        'document': data.pop('numero_documento', ''),
    }
    kyc_fields = {
        'primer_nombre': primer_nombre,
        'segundo_nombre': segundo_nombre,
        'primer_apellido': primer_apellido,
        'segundo_apellido': segundo_apellido,
        'sexo': data.pop('sexo', ''),
        'nacionalidad': data.pop('nacionalidad', ''),
        'fecha_expedicion_documento': data.pop('fecha_expedicion_documento', None),
        'lugar_expedicion_documento': data.pop('lugar_expedicion_documento', ''),
    }

    ip_address = data.pop('ip_address', None) or '0.0.0.0'
    user_agent = data.pop('user_agent', '')
    consent_events = []
    consent_map = {
        'acepta_politica_tratamiento_datos': 'POLITICA_TRATAMIENTO_DATOS',
        'acepta_autorizacion_tratamiento_datos': 'AUTORIZACION_TRATAMIENTO_DATOS',
        'acepta_terminos_condiciones': 'TERMINOS_CONDICIONES',
    }
    for field, consent_type in consent_map.items():
        if data.pop(field, False):
            consent_events.append({
                'consent_type': consent_type,
                'document_version': CURRENT_CONSENT_DOCUMENT_VERSION,
                'ip_address': ip_address,
                'user_agent': user_agent,
            })

    resolved_first_name = f'{primer_nombre} {segundo_nombre}'.strip() or legacy_first_name
    resolved_last_name = f'{primer_apellido} {segundo_apellido}'.strip() or legacy_last_name

    return {
        'first_name': resolved_first_name,
        'last_name': resolved_last_name,
        'profile_extra': profile_extra,
        'kyc_fields': kyc_fields,
        'consent_events': consent_events,
        'has_kyc_data': has_kyc_data,
    }


def _create_default_shipping_address_from_registration(user, kyc_data: dict, phone_number: str | None) -> None:
    """
    SSoT de direccion (2026-07-17): la direccion estructurada que el usuario ya
    diligencio en /register (kyc_data['profile_extra']['address'], armada por el
    constructor colombiano de PersonalInfoFields.vue) se convierte automaticamente
    en la primera orders.ShippingAddress del usuario (is_default=True) -- nunca se
    le vuelve a pedir en "Mis Direcciones". Import diferido (evita import
    circular accounts<->orders, mismo patron que PricingEngineSelector). Si el
    registro no trajo direccion (ej. creacion admin sin KycRegistrationFieldsMixin),
    no se crea nada -- el usuario vera el estado vacio de "Mis Direcciones".
    """
    address_line_1 = (kyc_data.get('profile_extra') or {}).get('address') or ''
    if not address_line_1:
        return

    from orders.services.commands import ShippingAddressCommands

    full_name = f"{kyc_data['first_name']} {kyc_data['last_name']}".strip() or user.email
    digits = ''.join(ch for ch in str(phone_number or '') if ch.isdigit())[-10:]

    ShippingAddressCommands.create(
        user,
        label='Principal',
        full_name=full_name,
        address_line_1=address_line_1,
        city=kyc_data['profile_extra'].get('city') or '',
        country=kyc_data['profile_extra'].get('country') or 'Colombia',
        phone_number=digits,
    )


class AccountCommands:

    @staticmethod
    @transaction.atomic
    def register_user(validated_data: dict) -> User:
        """
        Crea un User (solo auth) y su UserProfile. La API nunca asigna
        is_staff ni is_superuser.

        SSoT de identidad (2026-07-09, endurecido): todo registro publico
        (validated_data trae los campos de KycRegistrationFieldsMixin, via
        UserRegisterSerializer) crea SIEMPRE un CUSTOMER con acceso
        instantaneo -- KYC ya no bloquea el login de un comprador.
        Convertirse en profesional es un upgrade posterior desde el
        dashboard (ver kyc.services.commands.KycCommands.request_upgrade).
        Si el caller NO pasa `user_type` explicito (creacion admin via
        UserAdminCreateSerializer -- ya no expone ese campo -- o
        codigo/tests internos con el dict plano first_name/last_name de
        siempre), el default es CUSTOMER: un admin ya NO puede crear
        cuentas de tipo especializado directamente, ni siquiera omitiendo
        el chequeo de KYC -- todo perfil especializado nace de un upgrade
        aprobado. Codigo interno (fixtures de tests, seeds) que necesite un
        usuario ya tipado debe seguir pasando `user_type` explicito en el
        dict -- ese camino no cambia. En ambos casos la cuenta queda
        APPROVED de inmediato (ver KycCommands.bootstrap_approved).
        """
        from kyc.services.commands import KycCommands

        password = validated_data.pop('password')
        validated_data.pop('password_confirm', None)
        phone_number = validated_data.pop('phone_number', None)
        user_type = validated_data.pop('user_type', UserProfile.CUSTOMER)

        # Garantia: la API nunca eleva privilegios de admin
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)

        kyc_data = _pop_kyc_registration_data(validated_data)
        if kyc_data['has_kyc_data']:
            user_type = UserProfile.CUSTOMER

        user = User.objects.create_user(password=password, **validated_data)

        UserProfile.objects.create(
            user=user,
            first_name=kyc_data['first_name'],
            last_name=kyc_data['last_name'],
            phone_number=phone_number or None,
            user_type=user_type,
            **kyc_data['profile_extra'],
        )
        KycCommands.bootstrap_approved(user, kyc_data['kyc_fields'], kyc_data['consent_events'])
        _create_default_shipping_address_from_registration(user, kyc_data, phone_number)

        from notifications.services.commands import NotificationCommands
        _user = user
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='user_registered',
                context={'user_email': _user.email, 'user_id': _user.pk},
                ws_group='admin_notifications',
            )
        )

        logger.info(f"[accounts:register_user] Nuevo usuario: {user.email}")
        return user

    @staticmethod
    @transaction.atomic
    def create_from_verified_payload(payload: dict) -> User:
        """
        Crea User + UserProfile + UserVerification a partir del payload
        verificado por OTP. La contrasena ya viene hasheada en
        'password_hash'; no se vuelve a hashear.

        SSoT de identidad: este es el flujo de registro publico real (unico
        activo desde el frontend) -- SIEMPRE crea un CUSTOMER con acceso
        instantaneo (KycCommands.bootstrap_approved), sin importar que la
        UI antigua pudiera enviar 'user_type' (el campo ya no existe en
        RegisterRequestSerializer, pero se ignora defensivamente si llegara).
        Convertirse en profesional es un upgrade posterior desde el
        dashboard (KycCommands.request_upgrade), no una eleccion aqui.
        """
        from kyc.services.commands import KycCommands

        payload = dict(payload)  # no mutar el dict original (viene de un JSONField)
        email = payload.pop('email')
        hashed_password = payload.pop('password_hash', '')
        phone_number = payload.pop('phone_number', None) or None
        payload.pop('user_type', None)  # ignorado a proposito -- ver docstring

        kyc_data = _pop_kyc_registration_data(payload)

        user = User(email=email, is_verified=True)
        user.password = hashed_password
        user.save()

        UserProfile.objects.create(
            user=user,
            first_name=kyc_data['first_name'],
            last_name=kyc_data['last_name'],
            phone_number=phone_number,
            user_type=UserProfile.CUSTOMER,
            **kyc_data['profile_extra'],
        )
        KycCommands.bootstrap_approved(user, kyc_data['kyc_fields'], kyc_data['consent_events'])
        _create_default_shipping_address_from_registration(user, kyc_data, phone_number)

        from notifications.services.commands import NotificationCommands
        _user = user
        transaction.on_commit(
            lambda: NotificationCommands.dispatch_notification(
                user=_user,
                template_slug='user_registered',
                context={'user_email': _user.email, 'user_id': _user.pk},
                ws_group='admin_notifications',
            )
        )

        logger.info(f"[accounts:create_from_verified_payload] Usuario verificado creado: {email}")
        return user

    @staticmethod
    def authenticate_user(email: str, password: str) -> User:
        """
        Login publico de cliente (auth/login/). Bloquea explicitamente
        is_staff/is_superuser -- las cuentas de administrador SOLO pueden
        autenticarse via admin-auth/login/ (panel.sintel.net.co), nunca desde
        el formulario publico. Sin este chequeo, una cuenta staff que
        tambien tuviera un UserVerification aprobado pasaba el gate de KYC
        de abajo y quedaba con sesion valida en el dominio publico (bug
        real, sesion de admin reflejada en sintel.net.co).
        """
        email = email.lower().strip()
        user = authenticate(email=email, password=password)
        if not user:
            raise AuthenticationFailed("Credenciales invalidas.")
        if not user.is_active:
            raise AuthenticationFailed("Cuenta desactivada.")
        if user.is_staff or user.is_superuser:
            raise AuthenticationFailed(
                "Esta cuenta debe iniciar sesion desde el panel de administracion."
            )
        AccountCommands._assert_kyc_approved(user)
        return user

    @staticmethod
    def _assert_kyc_approved(user: User) -> None:
        """
        Bloquea el login si el usuario nunca tuvo una aprobacion KYC, o si su
        verificacion esta BLOCKED (esto ultimo SIEMPRE bloquea, sin
        excepcion). Usado por authenticate_user (login/) y por
        GatedTokenObtainPairSerializer (token/) -- las dos rutas que emiten
        tokens a partir de credenciales ya existentes. register_verify NO
        pasa por aqui a proposito: el usuario recien creado debe poder
        autenticarse lo suficiente para completar la carga de documentos KYC
        si aplica.

        SSoT de identidad: `first_approved_at` (seteado UNA vez, nunca se
        borra -- ver KycCommands.bootstrap_approved/approve/force_approve)
        es la senal de "ya tuvo acceso alguna vez". Un CUSTOMER siempre lo
        tiene desde el registro (bootstrap_approved). Cuando pide un upgrade
        a profesional (KycCommands.request_upgrade), status vuelve a PENDING
        pero first_approved_at NO se toca -- por eso sigue pudiendo
        loguearse y comprar mientras se revisa su ascenso, sin perder
        acceso. NO se puede usar `reviewed_at` para esto: reject()/approve()
        tambien lo setean, no distingue "aprobado alguna vez" de "revisado y
        rechazado". Solo un usuario que JAMAS fue aprobado (caso ya
        retirado: registro directo como profesional) queda bloqueado -- y
        cualquier usuario BLOCKED, sin importar su historial.
        """
        from accounts.services.profile_resolver import ProfileResolver
        from kyc.models import UserVerification
        verification = ProfileResolver.get_verification(user)
        if verification is None:
            raise AuthenticationFailed(
                "Tu cuenta aun esta en proceso de validacion por el equipo de Sintel. "
                "Recibiras un correo cuando finalice la revision."
            )
        if verification.status == UserVerification.STATUS_BLOCKED:
            raise AuthenticationFailed(
                "Tu cuenta ha sido bloqueada. Contacta al equipo de soporte de Sintel."
            )
        if verification.status == UserVerification.STATUS_APPROVED or verification.first_approved_at is not None:
            return
        raise AuthenticationFailed(
            "Tu cuenta aun esta en proceso de validacion por el equipo de Sintel. "
            "Recibiras un correo cuando finalice la revision."
        )

    @staticmethod
    def logout(refresh_token: str) -> None:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info("[accounts:logout] Token invalidado.")
        except Exception as exc:
            logger.error(f"[accounts:logout] {exc}")
            raise ValidationError({"refresh": "Token invalido o expirado."})

    @staticmethod
    @transaction.atomic
    def change_password(user: User, old_password: str, new_password: str) -> User:
        if not user.check_password(old_password):
            raise ValidationError({"old_password": "La contrasena actual es incorrecta."})
        user.set_password(new_password)
        user.save()
        logger.info(f"[accounts:change_password] Contrasena cambiada: {user.email}")
        return user

    @staticmethod
    @transaction.atomic
    def update_profile(user: User, validated_data: dict) -> User:
        """
        Actualiza campos del UserProfile del usuario.
        Los campos de autenticacion (email, password) NO se tocan aqui.
        `user_type` esta deliberadamente excluido de profile_fields -- unico
        camino valido para cambiarlo: KycCommands.request_upgrade() +
        aprobacion admin (ver kyc/services/commands.py::_apply_requested_user_type).
        Defensa en profundidad ademas de que UserProfileUpdateSerializer ya
        no lo expone como campo editable.
        """
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(user)
        if profile is None:
            profile = UserProfile.objects.create(user=user)

        profile_fields = {
            'first_name', 'last_name', 'phone_number', 'document_type', 'document',
            'profile_picture', 'company', 'position',
            'address', 'city', 'state', 'country', 'postal_code',
            'birth_date', 'contractor_type', 'bio',
            'hourly_rate', 'daily_rate', 'project_rate', 'currency',
        }
        for attr, value in validated_data.items():
            if attr in profile_fields:
                setattr(profile, attr, value)
        profile.save()

        logger.info(f"[accounts:update_profile] Perfil actualizado: {user.email}")
        return user

    @staticmethod
    @transaction.atomic
    def admin_update_user(user: User, validated_data: dict) -> User:
        """
        Actualiza campos del User (is_active, is_verified) y del perfil
        desde el panel de administracion. NUNCA otorga is_staff/is_superuser via API.
        """
        user_fields = {'is_active', 'is_verified'}
        for attr in user_fields:
            if attr in validated_data:
                setattr(user, attr, validated_data[attr])
        user.save()

        # Delegar campos de perfil a update_profile
        profile_data = {k: v for k, v in validated_data.items() if k not in user_fields}
        if profile_data:
            AccountCommands.update_profile(user, profile_data)

        return user

    @staticmethod
    @transaction.atomic
    def admin_reset_password(user: User) -> str:
        """
        Genera una contrasena temporal, la aplica y la envia por correo al usuario.
        Retorna la contrasena en claro solo para el envio -- nunca se persiste como tal.
        """
        temp_password = ''.join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(12))
        user.set_password(temp_password)
        user.save(update_fields=['password'])

        from notifications.services.commands import NotificationCommands
        _user = user
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=_user,
            template_slug='admin_password_reset',
            context={'user_email': _user.email, 'temp_password': temp_password},
        ))
        logger.info(f"[accounts:admin_reset_password] Contrasena restablecida por admin para: {user.email}")
        return temp_password

    @staticmethod
    def resend_verification_email(user: User) -> str:
        """
        Genera un enlace de verificacion firmado (sin estado, sin modelo nuevo) para un usuario
        YA EXISTENTE -- distinto del flujo OTP de EmailVerificationCode, que es solo para
        pre-registro (antes de que exista el User). Expira en 24h; no es de un solo uso (la
        confirmacion es idempotente: solo marca is_verified=True).
        """
        token = signing.dumps({'user_id': user.pk}, salt=_EMAIL_VERIFICATION_SALT)
        # [2026-07-12] Antes tenia un fallback hardcodeado que duplicaba el default de
        # FRONTEND_BASE_URL en settings/base.py -- ahora lee de organization.EmailSettings
        # primero (SSoT), ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        email_settings = OrganizationSelector.get_email_settings()
        base_url = (email_settings.frontend_base_url if email_settings else '') or getattr(
            settings, 'FRONTEND_BASE_URL', 'http://localhost:5173'
        )
        link = f"{base_url}/verificar-cuenta?token={token}"

        from notifications.services.commands import NotificationCommands
        transaction.on_commit(lambda: NotificationCommands.dispatch_notification(
            user=user,
            template_slug='admin_email_verification',
            context={'user_email': user.email, 'verification_link': link},
        ))
        logger.info(f"[accounts:resend_verification_email] Enlace reenviado a: {user.email}")
        return token

    @staticmethod
    @transaction.atomic
    def confirm_email_verification_link(token: str) -> User:
        try:
            data = signing.loads(token, salt=_EMAIL_VERIFICATION_SALT, max_age=_EMAIL_VERIFICATION_MAX_AGE)
        except signing.SignatureExpired:
            raise ValidationError({'token': 'El enlace de verificación ha expirado. Solicita uno nuevo.'})
        except signing.BadSignature:
            raise ValidationError({'token': 'El enlace de verificación es inválido.'})

        try:
            user = User.objects.get(pk=data['user_id'])
        except User.DoesNotExist:
            raise ValidationError({'token': 'Usuario no encontrado.'})

        if not user.is_verified:
            user.is_verified = True
            user.save(update_fields=['is_verified'])
        return user

    @staticmethod
    @transaction.atomic
    def set_user_groups(user: User, group_ids: list) -> User:
        """
        Asigna al usuario a un conjunto de Django Groups existentes. Sin efecto en la
        autorizacion real del sistema hoy (ver users/api/views.py::UserViewSet.update_groups).
        """
        from django.contrib.auth.models import Group
        user.groups.set(Group.objects.filter(id__in=group_ids))
        return user

    # --- Specialty Commands ---
    @staticmethod
    @transaction.atomic
    def add_specialty(user_profile: UserProfile, category_id: int) -> ContractorSpecialty:
        try:
            category = ServiceCategory.objects.get(id=category_id, is_deleted=False)
        except ServiceCategory.DoesNotExist:
            raise ValidationError("La categoria de servicio no existe.")
        
        spec, created = ContractorSpecialty.objects.get_or_create(
            user_profile=user_profile,
            category=category,
            defaults={'is_deleted': False}
        )
        if not created and spec.is_deleted:
            spec.is_deleted = False
            spec.save()
        return spec

    @staticmethod
    @transaction.atomic
    def remove_specialty(user_profile: UserProfile, category_id: int) -> None:
        spec = ContractorSpecialty.objects.filter(
            user_profile=user_profile,
            category_id=category_id,
            is_deleted=False
        ).first()
        if spec:
            spec.is_deleted = True
            spec.save()

    # --- Skill Commands ---
    @staticmethod
    @transaction.atomic
    def add_skill(user_profile: UserProfile, name: str, level: str) -> ContractorSkill:
        skill, created = ContractorSkill.objects.get_or_create(
            user_profile=user_profile,
            name=name,
            defaults={'level': level, 'is_deleted': False}
        )
        if not created:
            skill.level = level
            skill.is_deleted = False
            skill.save()
        return skill

    @staticmethod
    @transaction.atomic
    def remove_skill(user_profile: UserProfile, skill_id: int) -> None:
        skill = ContractorSkill.objects.filter(
            id=skill_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if skill:
            skill.is_deleted = True
            skill.save()

    # --- Experience Commands ---
    @staticmethod
    @transaction.atomic
    def add_experience(
        user_profile: UserProfile,
        company: str,
        position: str,
        description: str,
        start_date,
        end_date,
        is_current: bool
    ) -> ProfessionalExperience:
        if not is_current and end_date and start_date and end_date < start_date:
            raise ValidationError("La fecha de finalizacion no puede ser anterior a la fecha de inicio.")
        
        exp = ProfessionalExperience.objects.create(
            user_profile=user_profile,
            company=company,
            position=position,
            description=description,
            start_date=start_date,
            end_date=None if is_current else end_date,
            is_current=is_current
        )
        return exp

    @staticmethod
    @transaction.atomic
    def remove_experience(user_profile: UserProfile, experience_id: int) -> None:
        exp = ProfessionalExperience.objects.filter(
            id=experience_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if exp:
            exp.is_deleted = True
            exp.save()

    # --- Academic Training Commands ---
    @staticmethod
    @transaction.atomic
    def add_academic_training(
        user_profile: UserProfile,
        institution: str,
        degree: str,
        field_of_study: str,
        start_date,
        end_date,
        is_current: bool
    ) -> AcademicTraining:
        if not is_current and end_date and start_date and end_date < start_date:
            raise ValidationError("La fecha de finalizacion no puede ser anterior a la fecha de inicio.")
        
        aca = AcademicTraining.objects.create(
            user_profile=user_profile,
            institution=institution,
            degree=degree,
            field_of_study=field_of_study,
            start_date=start_date,
            end_date=None if is_current else end_date,
            is_current=is_current
        )
        return aca

    @staticmethod
    @transaction.atomic
    def remove_academic_training(user_profile: UserProfile, academic_id: int) -> None:
        aca = AcademicTraining.objects.filter(
            id=academic_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if aca:
            aca.is_deleted = True
            aca.save()

    # --- Course Commands ---
    @staticmethod
    @transaction.atomic
    def add_course(
        user_profile: UserProfile,
        title: str,
        institution: str,
        completion_date,
        hours: int = None
    ) -> ProfessionalCourse:
        course = ProfessionalCourse.objects.create(
            user_profile=user_profile,
            title=title,
            institution=institution,
            completion_date=completion_date,
            hours=hours
        )
        return course

    @staticmethod
    @transaction.atomic
    def remove_course(user_profile: UserProfile, course_id: int) -> None:
        course = ProfessionalCourse.objects.filter(
            id=course_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if course:
            course.is_deleted = True
            course.save()

    # --- Certification Commands ---
    @staticmethod
    @transaction.atomic
    def add_certification(
        user_profile: UserProfile,
        name: str,
        issuing_organization: str,
        issue_date,
        expiration_date=None,
        credential_id: str = '',
        credential_url: str = '',
        document=None
    ) -> ProfessionalCertification:
        if document:
            validate_file(document, max_size_mb=5, allowed_extensions=['.pdf', '.jpg', '.jpeg', '.png'])
        
        cert = ProfessionalCertification.objects.create(
            user_profile=user_profile,
            name=name,
            issuing_organization=issuing_organization,
            issue_date=issue_date,
            expiration_date=expiration_date,
            credential_id=credential_id,
            credential_url=credential_url,
            document=document
        )
        return cert

    @staticmethod
    @transaction.atomic
    def remove_certification(user_profile: UserProfile, certification_id: int) -> None:
        cert = ProfessionalCertification.objects.filter(
            id=certification_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if cert:
            cert.is_deleted = True
            cert.save()

    # --- Success Case Commands ---
    @staticmethod
    @transaction.atomic
    def add_success_case(
        user_profile: UserProfile,
        title: str,
        description: str,
        completion_date=None,
        images: list = None
    ) -> SuccessCase:
        success_case = SuccessCase.objects.create(
            user_profile=user_profile,
            title=title,
            description=description,
            completion_date=completion_date
        )
        if images:
            for img_data in images:
                if isinstance(img_data, dict):
                    img_file = img_data.get('image')
                    is_before = img_data.get('is_before', False)
                    is_after = img_data.get('is_after', False)
                else:
                    img_file = img_data
                    is_before = False
                    is_after = False
                
                if img_file:
                    validate_file(img_file, max_size_mb=5, allowed_extensions=['.jpg', '.jpeg', '.png'], magic_bytes_check=True)
                    SuccessCaseImage.objects.create(
                        success_case=success_case,
                        image=img_file,
                        is_before=is_before,
                        is_after=is_after
                    )
        return success_case

    @staticmethod
    @transaction.atomic
    def remove_success_case(user_profile: UserProfile, case_id: int) -> None:
        case = SuccessCase.objects.filter(
            id=case_id,
            user_profile=user_profile,
            is_deleted=False
        ).first()
        if case:
            case.is_deleted = True
            case.save()

    # --- Review Commands ---
    @staticmethod
    @transaction.atomic
    def add_review(
        contractor: UserProfile,
        reviewer: User,
        comment: str,
        quality_rating: int,
        punctuality_rating: int,
        professionalism_rating: int,
        communication_rating: int,
        compliance_rating: int
    ) -> ContractorReview:
        if contractor.user == reviewer:
            raise ValidationError("No puedes dejarte una reseña a ti mismo.")
        
        ratings = [quality_rating, punctuality_rating, professionalism_rating, communication_rating, compliance_rating]
        for rating in ratings:
            if not (1 <= rating <= 5):
                raise ValidationError("Las calificaciones deben estar entre 1 y 5.")
        
        review, created = ContractorReview.objects.get_or_create(
            contractor=contractor,
            reviewer=reviewer,
            defaults={
                'comment': comment,
                'quality_rating': quality_rating,
                'punctuality_rating': punctuality_rating,
                'professionalism_rating': professionalism_rating,
                'communication_rating': communication_rating,
                'compliance_rating': compliance_rating,
                'is_deleted': False
            }
        )
        if not created:
            review.comment = comment
            review.quality_rating = quality_rating
            review.punctuality_rating = punctuality_rating
            review.professionalism_rating = professionalism_rating
            review.communication_rating = communication_rating
            review.compliance_rating = compliance_rating
            review.is_deleted = False
            review.save()
        return review

    @staticmethod
    @transaction.atomic
    def set_technician_availability(user, is_available: bool):
        """Activa/desactiva la disponibilidad de un profesional. Uso exclusivo de AdminContractorViewSet."""
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_technician_profile(user)
        if profile is None:
            raise ValidationError("Este usuario no tiene un perfil de tecnico configurado.")
        profile.is_available = is_available
        profile.save(update_fields=['is_available', 'updated_at'])
        return profile


class CustomerPasswordResetCommands:
    """
    Restablecimiento de contrasena self-service para clientes (is_staff=False).
    Reutiliza VerificationCommands/EmailVerificationCode -- no duplica el motor de OTP.
    Aislado de users.api.admin_auth / AdminPasswordResetCommands por diseno.
    """

    PURPOSE = EmailVerificationCode.PURPOSE_PASSWORD_RESET_CUSTOMER

    @staticmethod
    def request_reset(email: str) -> None:
        """Genera y envia el OTP solo si el correo pertenece a un cliente real.
        No revela si el correo existe: el caller (view) siempre responde 200 generico."""
        email = email.lower().strip()
        user = User.objects.filter(email=email, is_staff=False).first()
        if user is None:
            return
        VerificationCommands.request_email_verification(
            email, payload={}, purpose=CustomerPasswordResetCommands.PURPOSE
        )

    @staticmethod
    def verify_reset_code(email: str, code: str) -> None:
        """Solo lectura: valida el codigo sin consumirlo (feedback inmediato del paso 2)."""
        VerificationCommands.get_valid_verification(
            email.lower().strip(), code, purpose=CustomerPasswordResetCommands.PURPOSE
        )

    @staticmethod
    @transaction.atomic
    def confirm_reset(email: str, code: str, new_password: str) -> User:
        """Consume el codigo y establece la nueva contrasena, dentro de la misma
        transaccion (un fallo revierte tambien el consumo del OTP)."""
        email = email.lower().strip()
        verification = VerificationCommands.get_valid_verification(
            email, code, purpose=CustomerPasswordResetCommands.PURPOSE
        )
        verification.is_used = True
        verification.save(update_fields=['is_used'])

        user = User.objects.select_for_update().get(email=email, is_staff=False)
        user.set_password(new_password)
        user.save(update_fields=['password'])

        UserAuditCommands.log(
            None, user, UserAuditLog.ACTION_PASSWORD_RESET, metadata={'method': 'self_service_otp'},
        )
        logger.info(f"[customer_password_reset] Contrasena restablecida para: {email}")
        return user


class AvailabilityCommands:
    """
    Gestiona el ciclo de vida de los slots de disponibilidad profesional.
    """

    @staticmethod
    @transaction.atomic
    def create_availability_blocks(
        user_profile: UserProfile,
        start_date,
        end_date,
        work_start_hour: int = 8,
        work_end_hour: int = 18,
        slot_duration_hours: int = 2,
        exclude_weekends: bool = True,
        notes: str = "",
    ) -> list:
        """
        Genera bloques de disponibilidad para un rango de fechas.
        Retorna la lista de slots creados (ignora duplicados por unique_together).
        """
        import datetime
        from datetime import date as date_type, timedelta

        if isinstance(start_date, str):
            start_date = date_type.fromisoformat(start_date)
        if isinstance(end_date, str):
            end_date = date_type.fromisoformat(end_date)

        if start_date > end_date:
            raise ValidationError("La fecha de inicio debe ser anterior o igual a la fecha de fin.")
        if slot_duration_hours <= 0:
            raise ValidationError("La duracion del slot debe ser mayor a 0 horas.")
        if work_start_hour >= work_end_hour:
            raise ValidationError("La hora de inicio del turno debe ser anterior a la hora de fin.")

        # Obtener combinaciones existentes
        existing_slots = ProfessionalAvailability.objects.filter(
            user_profile=user_profile,
            date__range=(start_date, end_date),
            is_deleted=False
        ).values_list('date', 'start_time')
        existing_set = {(d, t) for d, t in existing_slots}

        slots_to_create = []
        current = start_date
        while current <= end_date:
            # 5=Sabado, 6=Domingo
            if exclude_weekends and current.weekday() >= 5:
                current += timedelta(days=1)
                continue

            slot_start = work_start_hour
            while slot_start + slot_duration_hours <= work_end_hour:
                t_start = datetime.time(slot_start, 0)
                t_end   = datetime.time(slot_start + slot_duration_hours, 0)
                if (current, t_start) not in existing_set:
                    slots_to_create.append(
                        ProfessionalAvailability(
                            user_profile=user_profile,
                            date=current,
                            start_time=t_start,
                            end_time=t_end,
                            status=ProfessionalAvailability.AVAILABLE,
                            notes=notes,
                        )
                    )
                slot_start += slot_duration_hours

            current += timedelta(days=1)

        # ignore_conflicts=True respeta el unique_together y omite duplicados
        created = ProfessionalAvailability.objects.bulk_create(
            slots_to_create, ignore_conflicts=True
        )
        logger.info(
            "[availability:bulk_create] %d slots generados para %s (%s a %s)",
            len(created), user_profile, start_date, end_date,
        )
        return created

    @staticmethod
    @transaction.atomic
    def lock_slot_temporarily(
        slot_id: int,
        requesting_user,
    ) -> ProfessionalAvailability:
        """
        Bloquea un slot de forma pesimista (select_for_update) y programa
        su liberacion automatica a los 15 minutos via Celery.
        Lanza ValidationError si el slot no esta disponible.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(
                    id=slot_id,
                    status=ProfessionalAvailability.AVAILABLE,
                    is_deleted=False,
                )
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError(
                "El slot seleccionado ya no esta disponible. Por favor elige otro horario."
            )

        slot.status    = ProfessionalAvailability.PENDING_RESERVATION
        slot.booked_by = requesting_user
        slot.save(update_fields=['status', 'booked_by', 'updated_at'])

        logger.info(
            "[availability:lock] Slot %d bloqueado temporalmente por %s",
            slot_id, requesting_user.email,
        )

        # Programar liberacion automatica: se ejecuta dentro del on_commit
        # para garantizar que el slot ya este en BD antes de que la tarea corra.
        from accounts.tasks import release_expired_slot
        transaction.on_commit(
            lambda: release_expired_slot.apply_async(
                args=[slot_id], countdown=900  # 15 minutos
            )
        )
        return slot

    @staticmethod
    @transaction.atomic
    def confirm_booking(slot_id: int) -> ProfessionalAvailability:
        """
        Confirma definitivamente la reserva de un slot.
        Llamado desde el callback de pago exitoso.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(id=slot_id, is_deleted=False)
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError("Slot no encontrado.")

        if slot.status not in (
            ProfessionalAvailability.PENDING_RESERVATION,
            ProfessionalAvailability.AVAILABLE,
        ):
            raise ValidationError(
                f"No se puede confirmar un slot con estado '{slot.get_status_display()}'."
            )

        slot.status = ProfessionalAvailability.BOOKED
        slot.save(update_fields=['status', 'updated_at'])
        logger.info("[availability:confirm] Slot %d -> BOOKED", slot_id)
        return slot

    @staticmethod
    @transaction.atomic
    def release_booking(slot_id: int) -> ProfessionalAvailability:
        """
        Libera un slot y lo deja disponible de nuevo.
        Llamado por la tarea Celery de expiracion o ante pago fallido.
        """
        slot_id = int(slot_id)
        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(id=slot_id, is_deleted=False)
            )
        except ProfessionalAvailability.DoesNotExist:
            return None  # Ya eliminado, sin accion necesaria

        # Solo liberar si estaba en un estado "reservable"
        if slot.status in (
            ProfessionalAvailability.PENDING_RESERVATION,
            ProfessionalAvailability.BOOKED,
        ):
            slot.status    = ProfessionalAvailability.AVAILABLE
            slot.booked_by = None
            slot.save(update_fields=['status', 'booked_by', 'updated_at'])
            logger.info("[availability:release] Slot %d -> AVAILABLE", slot_id)
        return slot

    @staticmethod
    @transaction.atomic
    def update_slot_status(
        slot_id: int,
        new_status: str,
        requesting_user,
    ) -> ProfessionalAvailability:
        """
        Permite al profesional cambiar manualmente el estado de un slot
        (BLOCKED, VACATION, SICK_LEAVE, AVAILABLE).
        """
        slot_id = int(slot_id)
        allowed = [
            ProfessionalAvailability.AVAILABLE,
            ProfessionalAvailability.BLOCKED,
            ProfessionalAvailability.VACATION,
            ProfessionalAvailability.SICK_LEAVE,
        ]
        if new_status not in allowed:
            raise ValidationError(
                f"Estado '{new_status}' no permitido. Opciones: {allowed}"
            )

        try:
            slot = (
                ProfessionalAvailability.objects
                .select_for_update()
                .get(
                    id=slot_id,
                    user_profile__user=requesting_user,
                    is_deleted=False,
                )
            )
        except ProfessionalAvailability.DoesNotExist:
            raise ValidationError("Slot no encontrado o no tienes permisos para modificarlo.")

        slot.status = new_status
        slot.save(update_fields=['status', 'updated_at'])
        logger.info(
            "[availability:update_status] Slot %d -> %s por %s",
            slot.id, new_status, requesting_user.email
        )
        return slot
