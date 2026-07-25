import random
import logging
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError, NotFound
from users.models import User, EmailVerificationCode, UserAuditLog

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
OTP_EXPIRY_MINUTES = 60
RESEND_COOLDOWN_SECONDS = 60

_OTP_EXPIRY_MINUTES_BY_PURPOSE = {
    EmailVerificationCode.PURPOSE_REGISTRATION: OTP_EXPIRY_MINUTES,
    EmailVerificationCode.PURPOSE_PASSWORD_RESET_CUSTOMER: 15,
    EmailVerificationCode.PURPOSE_PASSWORD_RESET_ADMIN: 15,
}


class UserCommands:
    @staticmethod
    @transaction.atomic
    def change_password(user: User, old_password: str, new_password: str):
        """Cambia la contrasena del usuario tras validar la anterior."""
        if not user.check_password(old_password):
            raise ValidationError({"old_password": "La contrasena actual es incorrecta."})
        user.set_password(new_password)
        user.save()
        logger.info(f"[users:change_password] Contrasena cambiada para: {user.email}")
        return user

    @staticmethod
    @transaction.atomic
    def erase_user(actor: User, user: User) -> User:
        """
        Soft-delete permanente (is_deleted=True): el usuario desaparece de todas
        las listas (UserSelector.list_all() ya filtra is_deleted=False) sin tocar
        ninguna fila relacionada -- historial de ordenes/pagos/rentas/etc. queda
        100% intacto. NUNCA hace DELETE fisico (.AGENT.md seccion 6.1): un hard
        delete aqui choca con on_delete=PROTECT dos saltos mas abajo en el grafo
        de borrado de Django (ej. RentalOperation protege RentalRequest, cuyo
        .user es CASCADE) y lanzaba ProtectedError sin capturar -- 500 real
        encontrado en produccion/dev con la cuenta ceo@sintel.net.co.
        """
        if user == actor:
            raise ValidationError({'detail': 'No puedes eliminarte a ti mismo.'})
        if user.is_active:
            raise ValidationError({'detail': 'Solo se pueden eliminar usuarios inactivos. Desactiva primero la cuenta.'})
        if user.is_deleted:
            raise NotFound('Este usuario ya fue eliminado.')

        email = user.email
        user.is_deleted = True
        user.save(update_fields=['is_deleted'])
        UserAuditCommands.log(actor, user, UserAuditLog.ACTION_ERASED, target_user_email=email)
        logger.info(f"[users:erase_user] Usuario eliminado (soft-delete) por {actor.email}: {email}")
        return user


class VerificationCommands:

    @staticmethod
    @transaction.atomic
    def request_email_verification(
        email: str, payload: dict, purpose: str = EmailVerificationCode.PURPOSE_REGISTRATION
    ) -> EmailVerificationCode:
        """
        Genera y envia un OTP de 6 digitos. `purpose` por defecto es el flujo de registro
        (retrocompatible con todos los callers existentes); tambien se usa para los flujos
        de restablecimiento de contrasena (cliente/admin), donde `payload` va vacio ({}).
        Hashea la contrasena del payload antes de persistirla (solo aplica a registro).
        """
        expiry_minutes = _OTP_EXPIRY_MINUTES_BY_PURPOSE[purpose]

        # Invalidar codigos anteriores no usados para este email, mismo purpose
        EmailVerificationCode.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)

        code = f"{random.randint(0, 999999):06d}"

        # Hashear la contrasena antes de guardar el payload (nunca plaintext en BD)
        safe_payload = dict(payload)
        raw_password = safe_payload.pop('password', None)
        safe_payload.pop('password_confirm', None)
        if raw_password:
            safe_payload['password_hash'] = make_password(raw_password)

        verification = EmailVerificationCode.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            registration_payload=safe_payload,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

        VerificationCommands._send_otp_email(email, code, purpose=purpose, expiry_minutes=expiry_minutes)
        logger.info(f"[verification:request] OTP generado para {email} (purpose={purpose})")
        return verification

    @staticmethod
    def get_valid_verification(
        email: str, code: str, purpose: str = EmailVerificationCode.PURPOSE_REGISTRATION
    ) -> EmailVerificationCode | None:
        """
        Localiza y valida el OTP para email+code+purpose SIN marcarlo como usado todavia
        (el caller debe marcarlo dentro de la misma transaccion atomica que hace la
        mutacion real -- ver AccountViewSet.register_verify -- para que un fallo alli
        revierta tambien el consumo del codigo y el usuario pueda reintentar con el
        mismo OTP).
        Lanza ValidationError en caso de codigo invalido, expirado o bloqueado.

        Para purpose=registration: si el codigo ya fue usado exitosamente para crear
        la cuenta (reintento duplicado del mismo request) retorna None en vez de
        fallar, tratando el caso como idempotente. Esta rama NO aplica a otros
        purposes (restablecimiento de contrasena): ahi un codigo usado/inexistente
        siempre debe fallar (fail-closed) -- "ya se hizo" no es un resultado seguro
        de reportar como exito silencioso para un cambio de contrasena.
        """
        try:
            verification = (
                EmailVerificationCode.objects
                .filter(email=email, purpose=purpose, is_used=False)
                .latest('created_at')
            )
        except EmailVerificationCode.DoesNotExist:
            if purpose == EmailVerificationCode.PURPOSE_REGISTRATION:
                already_verified = EmailVerificationCode.objects.filter(
                    email=email, purpose=purpose, is_used=True, code=code,
                ).exists()
                if already_verified and User.objects.filter(email=email).exists():
                    return None
            raise ValidationError({'code': 'No hay un codigo activo para este correo.'})

        if verification.is_expired():
            raise ValidationError({'code': 'El codigo ha caducado. Solicita uno nuevo.'})

        if verification.is_blocked():
            raise ValidationError({'code': 'Demasiados intentos fallidos. Solicita un nuevo codigo.'})

        if verification.code != code:
            verification.failed_attempts += 1
            verification.save(update_fields=['failed_attempts'])
            remaining = MAX_ATTEMPTS - verification.failed_attempts
            if remaining > 0:
                raise ValidationError({'code': f'Codigo incorrecto. Te quedan {remaining} intentos.'})
            raise ValidationError({'code': 'Demasiados intentos fallidos. Solicita un nuevo codigo.'})

        logger.info(f"[verification:verify] OTP verificado correctamente para {email} (purpose={purpose})")
        return verification

    @staticmethod
    @transaction.atomic
    def resend_email_verification(
        email: str, purpose: str = EmailVerificationCode.PURPOSE_REGISTRATION
    ) -> EmailVerificationCode:
        """Reenvio del OTP con cooldown de 60 segundos entre intentos."""
        expiry_minutes = _OTP_EXPIRY_MINUTES_BY_PURPOSE[purpose]
        cooldown_from = timezone.now() - timedelta(seconds=RESEND_COOLDOWN_SECONDS)
        if EmailVerificationCode.objects.filter(
            email=email, purpose=purpose, is_used=False, created_at__gte=cooldown_from
        ).exists():
            raise ValidationError(
                {'email': f'Debes esperar {RESEND_COOLDOWN_SECONDS} segundos antes de reenviar.'}
            )

        try:
            last = (
                EmailVerificationCode.objects
                .filter(email=email, purpose=purpose, is_used=False)
                .latest('created_at')
            )
            existing_payload = last.registration_payload
        except EmailVerificationCode.DoesNotExist:
            raise ValidationError(
                {'email': 'No hay un proceso activo. Comienza de nuevo.'}
            )

        # Invalidar codigo anterior y crear uno nuevo con el mismo payload (ya con hash)
        EmailVerificationCode.objects.filter(email=email, purpose=purpose, is_used=False).update(is_used=True)

        code = f"{random.randint(0, 999999):06d}"
        verification = EmailVerificationCode.objects.create(
            email=email,
            code=code,
            purpose=purpose,
            registration_payload=existing_payload,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

        VerificationCommands._send_otp_email(email, code, resend=True, purpose=purpose, expiry_minutes=expiry_minutes)
        logger.info(f"[verification:resend] Nuevo OTP para {email} (purpose={purpose})")
        return verification

    @staticmethod
    def _send_otp_email(
        email: str,
        code: str,
        resend: bool = False,
        purpose: str = EmailVerificationCode.PURPOSE_REGISTRATION,
        expiry_minutes: int = OTP_EXPIRY_MINUTES,
    ) -> None:
        is_reset = purpose != EmailVerificationCode.PURPOSE_REGISTRATION
        action_word = 'restablecer tu contrasena' if is_reset else 'verificar tu correo'
        base_subject = 'Restablece tu contrasena Sintel' if is_reset else 'Tu codigo de verificacion Sintel'
        subject = f"Tu nuevo codigo para {action_word}" if resend else base_subject
        message = (
            f"Hola,\n\n"
            f"Tu codigo para {action_word} es:\n\n"
            f"    {code}\n\n"
            f"Caduca en {expiry_minutes} minutos.\n"
            f"Si no solicitaste este codigo, ignora este mensaje.\n\n"
            f"Equipo Sintel"
        )
        try:
            # [2026-07-12] Antes tenia un fallback hardcodeado que duplicaba el default de
            # DEFAULT_FROM_EMAIL en settings/base.py -- ahora lee de organization.EmailSettings
            # primero (SSoT), ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
            from organization.services.selectors import OrganizationSelector
            email_settings = OrganizationSelector.get_email_settings()
            from_email = (email_settings.default_from_email if email_settings else '') or getattr(
                settings, 'DEFAULT_FROM_EMAIL', 'noreply@sintel.co'
            )
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as exc:
            logger.warning(f"[verification:send_mail] Fallo el envio a {email}: {exc}")


class UserAuditCommands:
    @staticmethod
    def log(actor, target_user, action: str, metadata: dict | None = None, target_user_email: str = '') -> UserAuditLog:
        return UserAuditLog.objects.create(
            actor=actor if getattr(actor, 'is_authenticated', False) else None,
            actor_email=getattr(actor, 'email', '') or '',
            target_user=target_user,
            target_user_email=target_user_email or getattr(target_user, 'email', '') or '',
            action=action,
            metadata=metadata or {},
        )


class AdminPasswordResetCommands:
    """
    Restablecimiento de contrasena self-service EXCLUSIVO para administradores
    (is_staff=True AND is_superuser=True). Aislado de accounts/AccountCommands por
    diseno, igual que users.api.admin_auth.AdminLoginView -- ver ese archivo para
    la regla de aislamiento completa. NUNCA importar desde accounts.
    """

    PURPOSE = EmailVerificationCode.PURPOSE_PASSWORD_RESET_ADMIN

    @staticmethod
    def request_reset(email: str) -> None:
        """Genera y envia el OTP solo si el correo pertenece a un admin real.
        No revela si el correo existe: el caller (view) siempre responde 200 generico."""
        email = email.lower().strip()
        user = User.objects.filter(email=email, is_staff=True, is_superuser=True).first()
        if user is None:
            return
        VerificationCommands.request_email_verification(
            email, payload={}, purpose=AdminPasswordResetCommands.PURPOSE
        )

    @staticmethod
    def verify_reset_code(email: str, code: str) -> None:
        """Solo lectura: valida el codigo sin consumirlo (feedback inmediato del paso 2)."""
        VerificationCommands.get_valid_verification(
            email.lower().strip(), code, purpose=AdminPasswordResetCommands.PURPOSE
        )

    @staticmethod
    @transaction.atomic
    def confirm_reset(email: str, code: str, new_password: str) -> User:
        """Consume el codigo y establece la nueva contrasena, dentro de la misma
        transaccion (un fallo revierte tambien el consumo del OTP)."""
        email = email.lower().strip()
        verification = VerificationCommands.get_valid_verification(
            email, code, purpose=AdminPasswordResetCommands.PURPOSE
        )
        verification.is_used = True
        verification.save(update_fields=['is_used'])

        user = User.objects.select_for_update().get(email=email, is_staff=True, is_superuser=True)
        user.set_password(new_password)
        user.save(update_fields=['password'])

        UserAuditCommands.log(
            None, user, UserAuditLog.ACTION_PASSWORD_RESET, metadata={'method': 'admin_self_service_otp'},
        )
        logger.info(f"[admin_password_reset] Contrasena restablecida para admin: {email}")
        return user
