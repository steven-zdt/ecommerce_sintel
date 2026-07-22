from datetime import date
from rest_framework import serializers
from accounts.models import UserProfile
from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
from kyc.models import UserVerification, VerificationDocument, VerificationEvent

MIN_AGE_YEARS = 18


class KycRegistrationFieldsMixin(serializers.Serializer):
    """
    Mixin de campos KYC obligatorios en el registro. Se mezcla en
    accounts.api.serializers.RegisterRequestSerializer y UserRegisterSerializer
    -- ambos flujos de registro deben capturar los mismos datos de identidad
    y consentimiento, para que ninguno quede como bypass silencioso del KYC.
    """
    primer_nombre    = serializers.CharField(max_length=50)
    segundo_nombre   = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    primer_apellido  = serializers.CharField(max_length=50)
    segundo_apellido = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    fecha_nacimiento = serializers.DateField()
    sexo = serializers.ChoiceField(choices=UserVerification.SEXO_CHOICES, required=False, allow_blank=True, default='')
    nacionalidad = serializers.CharField(max_length=80)
    pais = serializers.CharField(max_length=50)
    ciudad = serializers.CharField(max_length=50)
    direccion = serializers.CharField(max_length=250)
    tipo_documento = serializers.ChoiceField(choices=UserProfile.DOCUMENT_TYPE_CHOICES)
    numero_documento = serializers.CharField(max_length=30)
    fecha_expedicion_documento = serializers.DateField(required=False, allow_null=True, default=None)
    lugar_expedicion_documento = serializers.CharField(max_length=100)

    acepta_politica_tratamiento_datos = serializers.BooleanField()
    acepta_autorizacion_tratamiento_datos = serializers.BooleanField()
    acepta_terminos_condiciones = serializers.BooleanField()

    def validate_fecha_nacimiento(self, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < MIN_AGE_YEARS:
            raise serializers.ValidationError("Debes ser mayor de edad (18 anos o mas) para registrarte.")
        return value

    def validate_numero_documento(self, value):
        if not value.isdigit() or not (5 <= len(value) <= 20):
            raise serializers.ValidationError("El numero de documento debe contener solo digitos (5 a 20 caracteres).")
        return value

    def validate(self, data):
        data = super().validate(data)
        required_consents = (
            'acepta_politica_tratamiento_datos',
            'acepta_autorizacion_tratamiento_datos',
            'acepta_terminos_condiciones',
        )
        for field in required_consents:
            if not data.get(field):
                raise serializers.ValidationError({field: 'Debes aceptar este documento obligatorio para continuar.'})
        return data


class VerificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationEvent
        fields = ['uuid', 'event_type', 'description', 'actor_email', 'created_at']


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = [
            'uuid', 'doc_type', 'status', 'scan_status',
            'rejection_reason', 'original_filename', 'created_at',
        ]


class UserVerificationSerializer(serializers.ModelSerializer):
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserVerification
        fields = [
            'uuid', 'email', 'status', 'primer_nombre', 'segundo_nombre',
            'primer_apellido', 'segundo_apellido', 'sexo', 'nacionalidad',
            'fecha_expedicion_documento', 'lugar_expedicion_documento',
            'submitted_at', 'reviewed_at', 'admin_message', 'documents', 'created_at',
            'requested_user_type',
        ]
        read_only_fields = ['requested_user_type']


class AdminVerificationListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    document = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()

    class Meta:
        model = UserVerification
        fields = [
            'uuid', 'email', 'primer_nombre', 'primer_apellido',
            'document', 'document_type', 'status', 'requested_user_type',
            'submitted_at', 'created_at',
        ]

    def get_document(self, obj):
        from accounts.services import ProfileResolver
        profile = ProfileResolver.get_profile(obj.user)
        return profile.document if profile else ''

    def get_document_type(self, obj):
        from accounts.services import ProfileResolver
        profile = ProfileResolver.get_profile(obj.user)
        return profile.document_type if profile else ''


class AdminVerificationDetailSerializer(UserVerificationSerializer):
    """
    Detalle completo para el panel admin. Ademas de los campos KYC-only de
    UserVerification, expone los campos de identidad que viven en
    accounts.UserProfile (document/document_type/phone_number/etc) -- sin
    esto el admin revisando un caso no ve el numero de documento, telefono
    ni direccion del solicitante junto a sus documentos.
    """
    timeline_events = VerificationEventSerializer(many=True, read_only=True)
    document = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    fecha_nacimiento = serializers.SerializerMethodField()
    pais = serializers.SerializerMethodField()
    ciudad = serializers.SerializerMethodField()
    direccion = serializers.SerializerMethodField()

    class Meta(UserVerificationSerializer.Meta):
        fields = UserVerificationSerializer.Meta.fields + [
            'timeline_events', 'document', 'document_type', 'phone_number',
            'fecha_nacimiento', 'pais', 'ciudad', 'direccion',
        ]

    def _profile(self, obj):
        from accounts.services import ProfileResolver
        return ProfileResolver.get_profile(obj.user)

    def get_document(self, obj):
        profile = self._profile(obj)
        return profile.document if profile else ''

    def get_document_type(self, obj):
        profile = self._profile(obj)
        return profile.document_type if profile else ''

    def get_phone_number(self, obj):
        profile = self._profile(obj)
        return profile.phone_number if profile else ''

    def get_fecha_nacimiento(self, obj):
        profile = self._profile(obj)
        return profile.birth_date if profile else None

    def get_pais(self, obj):
        profile = self._profile(obj)
        return profile.country if profile else ''

    def get_ciudad(self, obj):
        profile = self._profile(obj)
        return profile.city if profile else ''

    def get_direccion(self, obj):
        profile = self._profile(obj)
        return profile.address if profile else ''


class DocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=VerificationDocument.DOC_TYPE_CHOICES)
    file = serializers.FileField()


class RequestUpgradeSerializer(serializers.Serializer):
    """
    CUSTOMER ya APPROVED pidiendo convertirse en profesional. Las choices se
    restringen a SERVICE_PROVIDER_TYPES (no todo USER_TYPE_CHOICES -- no
    tendria sentido "pedir" CUSTOMER o TRANSPORTER/ACCOUNTANT via este flujo).
    """
    requested_user_type = serializers.ChoiceField(choices=sorted(SERVICE_PROVIDER_TYPES))


class AdminForceApproveSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default='')


class AdminRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class AdminRequestInfoSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=500)


class AdminBlockSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class AdminDocReviewSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    reason = serializers.CharField(required=False, allow_blank=True, default='')
