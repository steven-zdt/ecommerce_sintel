from django.conf import settings
from django.db import models
from accounts.models import UserProfile
from ecommerce.base_models import SintelBaseModel
from kyc.services.storage import kyc_private_storage, kyc_upload_path


class UserVerification(SintelBaseModel):
    """
    Verificacion de identidad (KYC) de un usuario. Una sola vez por usuario,
    reutilizada por todos los user_type (CLIENTE/PROVEEDOR/CONTRATISTA/TECNICO).
    No confundir con users.EmailVerificationCode (esa solo prueba propiedad
    del correo antes de crear la cuenta).
    """
    STATUS_PENDING      = 'PENDING'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_APPROVED     = 'APPROVED'
    STATUS_REJECTED     = 'REJECTED'
    STATUS_BLOCKED      = 'BLOCKED'
    STATUS_EXPIRED      = 'EXPIRED'
    STATUS_CHOICES = [
        (STATUS_PENDING,      'Pendiente de verificacion'),
        (STATUS_UNDER_REVIEW, 'En revision'),
        (STATUS_APPROVED,     'Aprobado'),
        (STATUS_REJECTED,     'Rechazado'),
        (STATUS_BLOCKED,      'Bloqueado'),
        (STATUS_EXPIRED,      'Expirado'),
    ]

    SEXO_MASCULINO = 'M'
    SEXO_FEMENINO = 'F'
    SEXO_OTRO = 'OTRO'
    SEXO_PREFIERO_NO_DECIR = 'PREFIERO_NO_DECIR'
    SEXO_CHOICES = [
        (SEXO_MASCULINO, 'Masculino'),
        (SEXO_FEMENINO, 'Femenino'),
        (SEXO_OTRO, 'Otro'),
        (SEXO_PREFIERO_NO_DECIR, 'Prefiero no decir'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='kyc_verification',
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)

    # Campos de identidad legal capturados en el registro (snapshot KYC).
    # first_name/last_name/document/document_type/birth_date/address/city/
    # country/phone_number viven en accounts.UserProfile y se reutilizan tal
    # cual -- no se duplican aqui. blank=True/default='' a nivel de modelo
    # porque la migracion de usuarios existentes (grandfathering) no puede
    # reconstruir estos datos; el serializer de registro exige required=True.
    primer_nombre    = models.CharField(max_length=50, blank=True, default='')
    segundo_nombre   = models.CharField(max_length=50, blank=True, default='')
    primer_apellido  = models.CharField(max_length=50, blank=True, default='')
    segundo_apellido = models.CharField(max_length=50, blank=True, default='')
    sexo             = models.CharField(max_length=20, choices=SEXO_CHOICES, blank=True, default='')
    nacionalidad     = models.CharField(max_length=80, blank=True, default='')
    fecha_expedicion_documento = models.DateField(null=True, blank=True)
    lugar_expedicion_documento = models.CharField(max_length=100, blank=True, default='')

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='kyc_reviews_done',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # Ultimo mensaje del admin (razon de rechazo, solicitud de info, o motivo
    # de bloqueo). El historial completo vive en VerificationEvent -- este
    # campo es solo un acceso rapido para listados.
    admin_message = models.CharField(max_length=500, blank=True, default='')

    # Se setea UNA sola vez, la primera vez que status pasa a APPROVED
    # (bootstrap_approved/approve/force_approve) -- y NUNCA se borra despues,
    # ni siquiera si luego pide un upgrade (vuelve a PENDING) o es rechazado.
    # Es la senal que usa AccountCommands._assert_kyc_approved para permitir
    # que un CUSTOMER conserve su acceso de comprador mientras se revisa un
    # upgrade a profesional. reviewed_at NO sirve para esto -- tambien lo
    # setean reject()/approve(), no distingue "aprobado alguna vez".
    first_approved_at = models.DateTimeField(null=True, blank=True)

    # Seteado por KycCommands.request_upgrade() cuando un CUSTOMER ya
    # aprobado pide convertirse en profesional. Nunca se sobreescribe ni se
    # borra -- queda como registro historico de en que se convirtio, incluso
    # despues de aplicado. Solo approve()/force_approve() lo consumen para
    # actualizar UserProfile.user_type en el momento de la aprobacion.
    requested_user_type = models.CharField(
        max_length=20, choices=UserProfile.USER_TYPE_CHOICES, null=True, blank=True, default=None,
    )

    class Meta:
        verbose_name = 'verificacion de identidad (KYC)'
        verbose_name_plural = 'verificaciones de identidad (KYC)'

    def __str__(self):
        return f"KYC {self.user.email} [{self.status}]"


class VerificationDocument(SintelBaseModel):
    CEDULA_FRONTAL = 'CEDULA_FRONTAL'
    CEDULA_REVERSO = 'CEDULA_REVERSO'
    RUT            = 'RUT'
    HOJA_VIDA      = 'HOJA_VIDA'
    DIPLOMA        = 'DIPLOMA'
    CERTIFICACION  = 'CERTIFICACION'
    ANTECEDENTES_POLICIA      = 'ANTECEDENTES_POLICIA'
    ANTECEDENTES_CONTRALORIA  = 'ANTECEDENTES_CONTRALORIA'
    ANTECEDENTES_PROCURADURIA = 'ANTECEDENTES_PROCURADURIA'
    OTRO = 'OTRO'
    DOC_TYPE_CHOICES = [
        (CEDULA_FRONTAL, 'Cedula (frontal)'),
        (CEDULA_REVERSO, 'Cedula (reverso)'),
        (RUT, 'RUT'),
        (HOJA_VIDA, 'Hoja de vida / CV'),
        (DIPLOMA, 'Diploma'),
        (CERTIFICACION, 'Certificacion'),
        (ANTECEDENTES_POLICIA, 'Antecedentes de Policia'),
        (ANTECEDENTES_CONTRALORIA, 'Antecedentes de Contraloria'),
        (ANTECEDENTES_PROCURADURIA, 'Antecedentes de Procuraduria'),
        (OTRO, 'Otro'),
    ]

    STATUS_PENDING  = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pendiente'),
        (STATUS_APPROVED, 'Aprobado'),
        (STATUS_REJECTED, 'Rechazado'),
    ]

    SCAN_SKIPPED  = 'SKIPPED'
    SCAN_CLEAN    = 'CLEAN'
    SCAN_INFECTED = 'INFECTED'
    SCAN_ERROR    = 'ERROR'
    SCAN_STATUS_CHOICES = [
        (SCAN_SKIPPED, 'Sin escanear (antivirus no configurado)'),
        (SCAN_CLEAN, 'Limpio'),
        (SCAN_INFECTED, 'Infectado'),
        (SCAN_ERROR, 'Error al escanear'),
    ]

    verification = models.ForeignKey(UserVerification, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES, db_index=True)
    file = models.FileField(storage=kyc_private_storage, upload_to=kyc_upload_path, blank=True, null=True)
    original_filename = models.CharField(max_length=255, blank=True, default='')
    content_type      = models.CharField(max_length=100, blank=True, default='')
    # SHA256 del contenido real del archivo -- nunca confiar solo en el
    # nombre/extension declarados por el cliente.
    file_hash_sha256  = models.CharField(max_length=64, blank=True, default='', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    scan_status = models.CharField(max_length=10, choices=SCAN_STATUS_CHOICES, default=SCAN_SKIPPED)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='uploaded_kyc_docs',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_kyc_docs',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        verbose_name = 'documento KYC'
        verbose_name_plural = 'documentos KYC'
        indexes = [models.Index(fields=['verification', 'doc_type'])]

    def __str__(self):
        return f"{self.verification.user.email} | {self.doc_type} [{self.status}]"


class VerificationEvent(SintelBaseModel):
    """Timeline append-only del proceso KYC. Nunca actualizar ni borrar filas -- solo INSERT."""
    CREATED               = 'CREATED'
    SUBMITTED_FOR_REVIEW   = 'SUBMITTED_FOR_REVIEW'
    APPROVED               = 'APPROVED'
    REJECTED               = 'REJECTED'
    INFO_REQUESTED         = 'INFO_REQUESTED'
    BLOCKED                = 'BLOCKED'
    DOC_UPLOADED           = 'DOC_UPLOADED'
    DOC_DELETED            = 'DOC_DELETED'
    DOC_OPENED             = 'DOC_OPENED'
    DOC_APPROVED           = 'DOC_APPROVED'
    DOC_REJECTED           = 'DOC_REJECTED'
    NOTE                   = 'NOTE'
    EVENT_TYPE_CHOICES = [
        (CREATED, 'Verificacion creada'),
        (SUBMITTED_FOR_REVIEW, 'Enviado a revision'),
        (APPROVED, 'Aprobado'),
        (REJECTED, 'Rechazado'),
        (INFO_REQUESTED, 'Informacion solicitada'),
        (BLOCKED, 'Bloqueado'),
        (DOC_UPLOADED, 'Documento subido'),
        (DOC_DELETED, 'Documento eliminado'),
        (DOC_OPENED, 'Documento abierto por admin'),
        (DOC_APPROVED, 'Documento aprobado'),
        (DOC_REJECTED, 'Documento rechazado'),
        (NOTE, 'Nota'),
    ]

    verification = models.ForeignKey(UserVerification, on_delete=models.CASCADE, related_name='timeline_events')
    event_type = models.CharField(max_length=25, choices=EVENT_TYPE_CHOICES, db_index=True)
    document = models.ForeignKey(
        VerificationDocument, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='events',
    )
    description = models.TextField(blank=True, default='')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='kyc_events_performed',
    )
    actor_email = models.EmailField(blank=True, default='')  # denormalizado, sobrevive a SET_NULL
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'evento de verificacion KYC'
        verbose_name_plural = 'eventos de verificacion KYC'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.verification.user.email} | {self.event_type}"


class ConsentRecord(SintelBaseModel):
    """
    Consentimiento Habeas Data (Ley 1581/2012 Colombia). Append-only -- jamas
    se actualiza ni se borra una fila existente. Un nuevo consentimiento (ej.
    nueva version del documento legal) siempre es un INSERT nuevo, nunca un
    UPDATE.
    """
    POLITICA_TRATAMIENTO = 'POLITICA_TRATAMIENTO_DATOS'
    AUTORIZACION_TRATAMIENTO = 'AUTORIZACION_TRATAMIENTO_DATOS'
    TERMINOS_CONDICIONES = 'TERMINOS_CONDICIONES'
    CONSENT_TYPE_CHOICES = [
        (POLITICA_TRATAMIENTO, 'Politica de Tratamiento de Datos Personales'),
        (AUTORIZACION_TRATAMIENTO, 'Autorizacion de Tratamiento de Datos'),
        (TERMINOS_CONDICIONES, 'Terminos y Condiciones'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consent_records')
    consent_type = models.CharField(max_length=40, choices=CONSENT_TYPE_CHOICES, db_index=True)
    document_version = models.CharField(max_length=20)
    accepted = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'registro de consentimiento (Habeas Data)'
        verbose_name_plural = 'registros de consentimiento (Habeas Data)'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'consent_type', 'created_at'])]

    def __str__(self):
        return f"{self.user.email} | {self.consent_type} | v{self.document_version}"
