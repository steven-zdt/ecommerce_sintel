from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from ecommerce.base_models import SintelBaseModel


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Usuarios deben proporcionar un correo electronico')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, SintelBaseModel):
    email = models.EmailField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    @property
    def username(self):
        return self.email

    def get_full_name(self):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(self)
        if profile:
            return profile.get_full_name()
        return self.email

    def get_short_name(self):
        from accounts.services.profile_resolver import ProfileResolver
        profile = ProfileResolver.get_profile(self)
        if profile and profile.first_name:
            return profile.first_name
        return self.email.split('@')[0]

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'
        ordering = ['-created_at']


class PhoneOtp(SintelBaseModel):
    phone_number = models.CharField(max_length=20, unique=True)
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)

    def is_expired(self):
        return self.created_at + timedelta(minutes=5) < timezone.now()

    def __str__(self):
        return f"{self.phone_number} - {self.otp}"


class EmailVerificationCode(SintelBaseModel):
    """OTP de 6 digitos enviado por correo para verificar el email antes de crear el usuario,
    o para autorizar un restablecimiento de contrasena (self-service)."""

    PURPOSE_REGISTRATION = 'registration'
    PURPOSE_PASSWORD_RESET_CUSTOMER = 'password_reset_customer'
    PURPOSE_PASSWORD_RESET_ADMIN = 'password_reset_admin'
    PURPOSE_CHOICES = [
        (PURPOSE_REGISTRATION, 'Registro'),
        (PURPOSE_PASSWORD_RESET_CUSTOMER, 'Restablecimiento de contrasena (cliente)'),
        (PURPOSE_PASSWORD_RESET_ADMIN, 'Restablecimiento de contrasena (admin)'),
    ]

    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_REGISTRATION, db_index=True)
    registration_payload = models.JSONField()
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    failed_attempts = models.IntegerField(default=0)

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_blocked(self):
        return self.failed_attempts >= 5

    def __str__(self):
        return f"{self.email} [{self.code}] {'usada' if self.is_used else 'activa'}"

    class Meta:
        verbose_name = 'codigo de verificacion de email'
        verbose_name_plural = 'codigos de verificacion de email'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'purpose', 'is_used'], name='email_verif_purpose_used_idx'),
        ]


class UserAuditLog(SintelBaseModel):
    """
    Registro append-only de acciones administrativas sobre un usuario (panel /panel/usuarios).
    Poblado con llamadas explicitas desde UserViewSet (no via signals), siguiendo el patron de
    Service Layer del proyecto.
    """
    ACTION_CREATED             = 'created'
    ACTION_ACTIVATED          = 'activated'
    ACTION_DEACTIVATED        = 'deactivated'
    ACTION_UPDATED            = 'updated'
    ACTION_PASSWORD_RESET     = 'password_reset'
    ACTION_VERIFICATION_RESENT = 'verification_resent'
    ACTION_GROUPS_CHANGED     = 'groups_changed'
    ACTION_ERASED             = 'erased'
    ACTION_KYC_SUBMITTED      = 'kyc_submitted'
    ACTION_KYC_APPROVED       = 'kyc_approved'
    ACTION_KYC_REJECTED       = 'kyc_rejected'
    ACTION_KYC_INFO_REQUESTED = 'kyc_info_requested'
    ACTION_KYC_BLOCKED        = 'kyc_blocked'
    ACTION_KYC_UPGRADE_REQUESTED = 'kyc_upgrade_requested'

    ACTION_CHOICES = [
        (ACTION_CREATED,             'Usuario creado'),
        (ACTION_ACTIVATED,           'Usuario activado'),
        (ACTION_DEACTIVATED,         'Usuario desactivado'),
        (ACTION_UPDATED,             'Usuario actualizado'),
        (ACTION_PASSWORD_RESET,      'Contrasena restablecida'),
        (ACTION_VERIFICATION_RESENT, 'Verificacion reenviada'),
        (ACTION_GROUPS_CHANGED,      'Grupos modificados'),
        (ACTION_ERASED,              'Usuario eliminado permanentemente'),
        (ACTION_KYC_SUBMITTED,       'KYC enviado a revision'),
        (ACTION_KYC_APPROVED,        'KYC aprobado'),
        (ACTION_KYC_REJECTED,        'KYC rechazado'),
        (ACTION_KYC_INFO_REQUESTED,  'KYC informacion solicitada'),
        (ACTION_KYC_BLOCKED,         'KYC bloqueado'),
        (ACTION_KYC_UPGRADE_REQUESTED, 'Solicito upgrade a perfil profesional'),
    ]

    # SET_NULL (no CASCADE): un 'erase' no debe borrar/huerfanar su propia entrada de auditoria.
    # Los *_email denormalizados mantienen el log legible aun despues de que la fila objetivo (o
    # la cuenta del propio admin) ya no exista.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_actions_performed',
    )
    actor_email = models.EmailField(blank=True, default='')
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='audit_log_entries',
    )
    target_user_email = models.EmailField(blank=True, default='')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'registro de auditoria de usuario'
        verbose_name_plural = 'registros de auditoria de usuarios'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['target_user', 'created_at'])]

    def __str__(self):
        return f"{self.action} | {self.target_user_email} | {self.created_at}"

