from rest_framework import serializers
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from users.models import User, UserAuditLog
from accounts.models import UserProfile, TechnicianProfile
from accounts.services.profile_resolver import ProfileResolver


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class UserAuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = UserAuditLog
        fields = ('uuid', 'action', 'action_display', 'actor_email', 'metadata', 'created_at')
        read_only_fields = fields


class UserGroupsUpdateSerializer(serializers.Serializer):
    group_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            'first_name', 'last_name', 'phone_number', 'document_type', 'document',
            'profile_picture', 'company', 'position', 'user_type',
            'address', 'city', 'state', 'country', 'postal_code',
            'birth_date', 'contractor_type', 'bio',
            'hourly_rate', 'daily_rate', 'project_rate', 'currency',
        )


class TechnicianProfileSerializer(serializers.ModelSerializer):
    specialties = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='slug',
    )

    class Meta:
        model = TechnicianProfile
        fields = ('is_available', 'specialties')


class UserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    technician_profile = TechnicianProfileSerializer(read_only=True)
    dispatcher_profile = serializers.SerializerMethodField()
    groups = GroupSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    kyc_status = serializers.SerializerMethodField()
    kyc_verification = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'uuid', 'email', 'full_name', 'first_name', 'last_name',
            'is_verified', 'is_active', 'is_staff',
            'date_joined', 'last_login',
            'profile', 'technician_profile', 'dispatcher_profile', 'groups',
            'kyc_status', 'kyc_verification',
        )

    def get_full_name(self, obj) -> str:
        profile = ProfileResolver.get_profile(obj)
        if profile:
            return f"{profile.first_name} {profile.last_name}".strip()
        return obj.email

    def get_first_name(self, obj) -> str:
        profile = ProfileResolver.get_profile(obj)
        return profile.first_name if profile else ''

    def get_last_name(self, obj) -> str:
        profile = ProfileResolver.get_profile(obj)
        return profile.last_name if profile else ''

    def get_dispatcher_profile(self, obj) -> dict | None:
        dispatcher = ProfileResolver.get_dispatcher_profile(obj)
        if dispatcher is None:
            return None
        from operations.api.serializers import DispatcherProfileSerializer  # import diferido: evita ciclo
        return DispatcherProfileSerializer(dispatcher).data

    def get_kyc_status(self, obj) -> str | None:
        verification = getattr(obj, 'kyc_verification', None)
        return verification.status if verification else None

    def get_kyc_verification(self, obj) -> dict | None:
        verification = getattr(obj, 'kyc_verification', None)
        if verification is None:
            return None
        from kyc.api.serializers import AdminVerificationDetailSerializer  # import diferido: evita ciclo
        return AdminVerificationDetailSerializer(verification).data


class UserAdminCreateSerializer(serializers.Serializer):
    """
    Crea un usuario desde el panel de administracion.

    SSoT de identidad (2026-07-09): no expone `user_type` -- un admin solo puede crear
    CUSTOMER desde aqui (AccountCommands.register_user() ahora tambien defaultea a CUSTOMER
    cuando el caller no lo pasa explicito). Convertirse en TECHNICIAN/PROFESSIONAL/
    SPECIALIST/CONTRACTOR sigue siendo exclusivamente un upgrade vía KYC ya aprobado.
    """
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=50, default='')
    last_name = serializers.CharField(max_length=50, default='')
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Las contrasenas no coinciden."})
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Este correo ya esta registrado."})
        return data


class UserAdminUpdateSerializer(serializers.Serializer):
    """
    Actualiza campos de un usuario desde el panel de administracion.

    SSoT de identidad (2026-07-09): no expone `user_type` -- ya era ignorado en silencio por
    AccountCommands.update_profile() (no esta en su allow-list de profile_fields); se retira
    del serializer para que el contrato de la API sea honesto. El unico camino valido para
    cambiar el tipo de un usuario existente es KycCommands._apply_requested_user_type()
    (upgrade aprobado), nunca este endpoint.
    """
    first_name = serializers.CharField(max_length=50, required=False)
    last_name = serializers.CharField(max_length=50, required=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)
