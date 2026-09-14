from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from users.models import User
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema
from accounts.models import UserProfile
from accounts.services import AccountSelector, AccountCommands
from accounts.services.selectors import (
    ContractorSearchSelector, ContractorRecommendationSelector, AvailabilitySelector,
    ContractorAdminSelector, ContractorCVSelector, ContractorProfileSelector,
)
from accounts.services.commands import AvailabilityCommands, CustomerPasswordResetCommands
from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
from accounts.services.profile_resolver import ProfileResolver
from accounts.exceptions import MissingRequiredProfile
from accounts.api.serializers import (
    UserRegisterSerializer,
    RegisterRequestSerializer,
    VerifyCodeSerializer,
    ResendCodeSerializer,
    UserLoginSerializer,
    LogoutSerializer,
    ChangePasswordSerializer,
    PublicContractorProfileSerializer,
    UserProfileUpdateSerializer,
    ContractorSpecialtySerializer,
    ContractorSkillSerializer,
    AcademicTrainingSerializer,
    ProfessionalCourseSerializer,
    ProfessionalCertificationSerializer,
    ProfessionalExperienceSerializer,
    SuccessCaseSerializer,
    ContractorReviewSerializer,
    AvailabilityOutputSerializer,
    AvailabilityBulkCreateSerializer,
    AvailabilityStatusUpdateSerializer,
    VerifyEmailLinkSerializer,
    AdminContractorSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordSerializer,
)
from users.api.serializers import UserDetailSerializer
from users.api.permissions import IsServiceProviderUser, IsServiceProviderOrUpgrading, IsAdminUser
from users.services import VerificationCommands
from users.services.commands import OTP_EXPIRY_MINUTES


class GatedTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Igual que el serializer estandar de SimpleJWT, pero aplicando el mismo
    chequeo de KYC que AccountCommands.authenticate_user -- /api/v1/auth/token/
    es una ruta paralela que de otro modo emitiria tokens sin pasar por
    AccountViewSet.login ni por el gate de verificacion.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        if self.user.is_staff or self.user.is_superuser:
            raise AuthenticationFailed(
                "Esta cuenta debe iniciar sesion desde el panel de administracion."
            )
        AccountCommands._assert_kyc_approved(self.user)
        return data


class GatedTokenObtainPairView(TokenObtainPairView):
    serializer_class = GatedTokenObtainPairSerializer


class AccountViewSet(viewsets.ViewSet):
    """
    ViewSet para centralizar la autenticacion: Registro, Login, Logout y Perfil.
    """
    # Rate limiting de registro/login (DRF ScopedRateThrottle, tasas en
    # REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']). register/register_request
    # comparten scope para que no se pueda duplicar la cuota alternando entre
    # los dos endpoints.
    ACTION_THROTTLE_SCOPES = {
        'register': 'register',
        'register_request': 'register',
        'login': 'login',
        'forgot_password_request': 'password_reset_request',
        'forgot_password_verify': 'password_reset_verify',
        'forgot_password_reset': 'password_reset_request',
        # A-03 (auditoria enterprise): la unica proteccion de fuerza bruta
        # de estos dos endpoints era el contador de 5 intentos fallidos por
        # codigo especifico (a nivel de modelo, EmailVerificationCode) y el
        # cooldown de 60s entre reenvios -- sin limite por IP contra intentos
        # distribuidos en varios emails/codigos distintos.
        'register_verify': 'register_verify',
        'register_resend': 'register_resend',
    }

    def get_throttles(self):
        scope = self.ACTION_THROTTLE_SCOPES.get(self.action)
        if not scope:
            return []
        self.throttle_scope = scope
        return [ScopedRateThrottle()]

    @extend_schema(request=UserRegisterSerializer, responses={201: UserDetailSerializer})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """Registro de nuevos usuarios."""
        serializer = UserRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = dict(serializer.validated_data)
        validated_data['ip_address'] = request.META.get('REMOTE_ADDR', '')
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        user = AccountCommands.register_user(validated_data)
        return Response(UserDetailSerializer(user, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=UserLoginSerializer, responses={200: UserDetailSerializer})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """Autenticacion y obtencion de tokens JWT."""
        from rest_framework.exceptions import AuthenticationFailed
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands

        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = AccountCommands.authenticate_user(**serializer.validated_data)
        except AuthenticationFailed:
            SecurityCommands.log_event(
                SecurityEvent.LOGIN_FAILED, request=request, severity=SecurityEvent.SEVERITY_WARNING,
                metadata={'email': serializer.validated_data.get('email', '')},
            )
            raise
        SecurityCommands.log_event(SecurityEvent.LOGIN_SUCCESS, request=request, user=user)
        tokens = AccountSelector.get_tokens_for_user(user)
        return Response({'user': UserDetailSerializer(user, context={'request': request}).data, 'tokens': tokens})

    @extend_schema(request=LogoutSerializer, responses={204: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        """Cierre de sesion e invalidacion de token."""
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountCommands.logout(serializer.validated_data['refresh'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(methods=['get'], responses={200: UserDetailSerializer})
    @extend_schema(methods=['patch'], request=UserProfileUpdateSerializer, responses={200: UserDetailSerializer})
    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def profile(self, request):
        """Obtener o actualizar el perfil del usuario autenticado. Soporta multipart/form-data para avatar."""
        if request.method == 'GET':
            return Response(UserDetailSerializer(request.user, context={'request': request}).data)

        data = {**request.data}
        if request.FILES:
            # request.FILES es un MultiValueDict (subclase de dict) -- data.update(request.FILES)
            # copia las listas internas tal cual ([archivo] en vez de archivo), porque dict.update()
            # usa un fast-path de copia directa entre subclases de dict que ignora el __getitem__
            # de valor unico que MultiValueDict sobreescribe. Iterar con [key] si evita el problema.
            data.update({key: request.FILES[key] for key in request.FILES})

        try:
            profile = ProfileResolver.resolve(request.user)
        except MissingRequiredProfile:
            return Response(
                {'detail': 'Tu cuenta no tiene un perfil configurado. Contacta a soporte.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserProfileUpdateSerializer(profile, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = AccountCommands.update_profile(request.user, serializer.validated_data)
        return Response(UserDetailSerializer(updated, context={'request': request}).data)

    @extend_schema(request=ChangePasswordSerializer, responses={200: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='change-password')
    def change_password(self, request):
        """Cambiar la contrasena del usuario autenticado."""
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        AccountCommands.change_password(
            user=request.user,
            old_password=serializer.validated_data['old_password'],
            new_password=serializer.validated_data['new_password']
        )
        return Response(status=status.HTTP_200_OK)

    @extend_schema(request=RegisterRequestSerializer, responses={200: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='register-request')
    def register_request(self, request):
        """
        Paso 1 del registro con verificacion de correo.
        Valida los datos completos y envia un OTP de 6 digitos al email indicado.
        No crea el usuario hasta que el OTP sea verificado.
        """
        serializer = RegisterRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        email = data['email']
        payload = {
            'email': email,
            'password': data['password'],
            'primer_nombre': data['primer_nombre'],
            'segundo_nombre': data.get('segundo_nombre', ''),
            'primer_apellido': data['primer_apellido'],
            'segundo_apellido': data.get('segundo_apellido', ''),
            'fecha_nacimiento': data['fecha_nacimiento'].isoformat(),
            'sexo': data.get('sexo', ''),
            'nacionalidad': data['nacionalidad'],
            'pais': data['pais'],
            'ciudad': data['ciudad'],
            'direccion': data['direccion'],
            'tipo_documento': data['tipo_documento'],
            'numero_documento': data['numero_documento'],
            # Opcional -- data['fecha_expedicion_documento'] puede ser None.
            'fecha_expedicion_documento': (
                data['fecha_expedicion_documento'].isoformat()
                if data.get('fecha_expedicion_documento') else None
            ),
            'lugar_expedicion_documento': data['lugar_expedicion_documento'],
            'acepta_politica_tratamiento_datos': data['acepta_politica_tratamiento_datos'],
            'acepta_autorizacion_tratamiento_datos': data['acepta_autorizacion_tratamiento_datos'],
            'acepta_terminos_condiciones': data['acepta_terminos_condiciones'],
            'phone_number': data.get('phone_number', '') or '',
            # Todo registro publico crea siempre un CUSTOMER (ver
            # AccountCommands.create_from_verified_payload) -- 'user_type'
            # ya no es client-suppliable aqui.
            # Capturados en el momento real en que el usuario marco los
            # checkboxes de Habeas Data (no en el momento posterior de
            # verificar el OTP).
            'ip_address': request.META.get('REMOTE_ADDR', ''),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }

        VerificationCommands.request_email_verification(email, payload)
        return Response(
            {'detail': f'Se ha enviado un codigo de verificacion a {email}. Caduca en {OTP_EXPIRY_MINUTES} minutos.'},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=VerifyCodeSerializer, responses={201: UserDetailSerializer})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='register-verify')
    def register_verify(self, request):
        """
        Paso 2 del registro: verifica el OTP y crea el usuario + perfil.
        Retorna 201 con el usuario y tokens JWT listos para usar.
        """
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        verification = VerificationCommands.get_valid_verification(email, code)

        if verification is None:
            # Reintento duplicado de un codigo que ya verifico y creo la cuenta
            # (p.ej. el backend se reinicio a mitad del flujo y el navegador
            # reenvio el request). La cuenta ya existe: solo se reemiten tokens.
            user = get_object_or_404(User, email=email)
            tokens = AccountSelector.get_tokens_for_user(user)
            return Response(
                {'user': UserDetailSerializer(user, context={'request': request}).data, 'tokens': tokens},
                status=status.HTTP_200_OK,
            )

        try:
            from rest_framework.exceptions import ValidationError as DRFValidationError
            with transaction.atomic():
                # is_used se marca en la misma transaccion que crea la cuenta:
                # si create_from_verified_payload falla (p.ej. telefono duplicado),
                # el rollback deja el codigo intacto y el usuario puede reintentar
                # sin perder el OTP. [CORREGIDO 2026-08-04, hallazgo M7 de
                # AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md]: delegado a
                # VerificationCommands.mark_as_used en vez de escribir el modelo
                # directo aqui -- sigue en la misma transaccion atomica.
                VerificationCommands.mark_as_used(verification)
                user = AccountCommands.create_from_verified_payload(verification.registration_payload)
        except IntegrityError as exc:
            if 'phone_number' in str(exc):
                raise DRFValidationError(
                    {'phone_number': 'Este numero de telefono ya esta registrado con otra cuenta.'}
                )
            raise DRFValidationError({'email': 'El correo ya esta registrado.'})

        tokens = AccountSelector.get_tokens_for_user(user)
        return Response(
            {'user': UserDetailSerializer(user, context={'request': request}).data, 'tokens': tokens},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ResendCodeSerializer, responses={200: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='register-resend')
    def register_resend(self, request):
        """Reenvio del OTP con cooldown de 60 segundos entre intentos."""
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        VerificationCommands.resend_email_verification(serializer.validated_data['email'])
        return Response(
            {'detail': 'Se ha reenviado el codigo de verificacion.'},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=VerifyEmailLinkSerializer, responses={200: dict})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='verify-email-confirm')
    def verify_email_confirm(self, request):
        """
        Confirma el enlace de verificacion enviado por un admin a un usuario YA EXISTENTE
        (distinto del OTP de registro). Ver AccountCommands.resend_verification_email/
        confirm_email_verification_link.
        """
        serializer = VerifyEmailLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = AccountCommands.confirm_email_verification_link(serializer.validated_data['token'])
        return Response({
            'detail': 'Correo verificado exitosamente.',
            'user': UserDetailSerializer(user, context={'request': request}).data,
        })

    @extend_schema(request=ForgotPasswordRequestSerializer, responses={200: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='forgot-password-request')
    def forgot_password_request(self, request):
        """
        Paso 1 de recuperacion de contrasena. Siempre responde el mismo 200
        generico exista o no el correo, para no revelar si una cuenta existe.
        """
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        CustomerPasswordResetCommands.request_reset(serializer.validated_data['email'])
        return Response(
            {'detail': 'Si el correo existe, se ha enviado un codigo de recuperacion.'},
            status=status.HTTP_200_OK,
        )

    @extend_schema(request=VerifyCodeSerializer, responses={200: None})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='forgot-password-verify')
    def forgot_password_verify(self, request):
        """Paso 2: valida el codigo sin consumirlo (feedback inmediato antes del paso 3)."""
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        CustomerPasswordResetCommands.verify_reset_code(
            serializer.validated_data['email'], serializer.validated_data['code']
        )
        return Response({'detail': 'Codigo valido.'}, status=status.HTTP_200_OK)

    @extend_schema(request=ResetPasswordSerializer, responses={200: UserDetailSerializer})
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny], url_path='forgot-password-reset')
    def forgot_password_reset(self, request):
        """Paso 3: consume el codigo, establece la nueva contrasena e inicia sesion automaticamente."""
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = CustomerPasswordResetCommands.confirm_reset(
            serializer.validated_data['email'],
            serializer.validated_data['code'],
            serializer.validated_data['new_password'],
        )
        tokens = AccountSelector.get_tokens_for_user(user)
        return Response(
            {'user': UserDetailSerializer(user, context={'request': request}).data, 'tokens': tokens},
            status=status.HTTP_200_OK,
        )


class ContractorPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class ContractorProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet publico para visualizar contratistas del marketplace.
    """
    queryset = ContractorProfileSelector.list_public()
    serializer_class = PublicContractorProfileSerializer
    lookup_field = 'uuid'
    permission_classes = [permissions.AllowAny]
    pagination_class = ContractorPagination

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='search')
    def search(self, request):
        """Busqueda filtrada de contratistas por categoria y filtros avanzados."""
        category_slug = request.query_params.get('category')
        filters = {}
        for key in ('max_hourly_rate', 'user_type', 'min_rating'):
            val = request.query_params.get(key)
            if val is not None:
                filters[key] = val

        qs = ContractorSearchSelector.search_contractors(
            category_slug=category_slug, filters=filters
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(PublicContractorProfileSerializer(page, many=True).data)
        return Response(PublicContractorProfileSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny], url_path='recommendations')
    def recommendations(self, request):
        """
        Devuelve profesionales compatibles con una categoria de servicio.
        Params: category_id (int, requerido), limit (int, default 10)
        Ordenados por calificacion promedio DESC y certificaciones DESC.
        """
        category_id = request.query_params.get('category_id')
        if not category_id:
            return Response(
                {'detail': 'El parametro category_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            category_id = int(category_id)
        except ValueError:
            return Response(
                {'detail': 'category_id debe ser un entero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = request.query_params.get('limit', 10)
        try:
            limit = max(1, min(int(limit), 50))
        except (ValueError, TypeError):
            limit = 10

        priority = request.query_params.get('priority')
        qs = ContractorRecommendationSelector.get_compatible_professionals(
            service_category_id=category_id,
            priority=priority,
            limit=limit,
        )
        return Response(PublicContractorProfileSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated], url_path='review')
    def add_review(self, request, uuid=None):
        contractor = self.get_object()
        reviewer = request.user
        comment = request.data.get('comment', '')
        try:
            quality_rating = int(request.data.get('quality_rating', 5))
            punctuality_rating = int(request.data.get('punctuality_rating', 5))
            professionalism_rating = int(request.data.get('professionalism_rating', 5))
            communication_rating = int(request.data.get('communication_rating', 5))
            compliance_rating = int(request.data.get('compliance_rating', 5))
        except ValueError:
            return Response({"detail": "Las calificaciones deben ser numeros enteros."}, status=status.HTTP_400_BAD_REQUEST)
        
        review = AccountCommands.add_review(
            contractor=contractor,
            reviewer=reviewer,
            comment=comment,
            quality_rating=quality_rating,
            punctuality_rating=punctuality_rating,
            professionalism_rating=professionalism_rating,
            communication_rating=communication_rating,
            compliance_rating=compliance_rating
        )
        return Response(ContractorReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class ContractorProfileScopedMixin:
    """
    Restringe el queryset/creacion al propio UserProfile del profesional autenticado.
    Resuelve el perfil via ProfileResolver (nunca request.user.profile directo) -- centraliza
    el punto de resolucion para las 7 ViewSets de CV en vez de repetirlo en cada una.

    Usa IsServiceProviderOrUpgrading (no IsServiceProviderUser a secas) para
    que un CUSTOMER con un upgrade profesional en curso (ver
    KycCommands.request_upgrade) pueda completar su perfil profesional aqui
    ANTES de que el KYC del upgrade sea aprobado -- su user_type real sigue
    siendo CUSTOMER hasta la aprobacion, por eso own_profile ya no exige
    expected_types (la autorizacion la hace el permission_classes).
    """
    permission_classes = [IsServiceProviderOrUpgrading]

    @property
    def own_profile(self):
        return ProfileResolver.resolve(self.request.user)


class ContractorSpecialtyViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContractorSpecialtySerializer

    def get_queryset(self):
        return ContractorCVSelector.list_specialties(self.own_profile)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spec = AccountCommands.add_specialty(
            user_profile=self.own_profile,
            category_id=serializer.validated_data['category_id']
        )
        return Response(ContractorSpecialtySerializer(spec).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        AccountCommands.remove_specialty(self.own_profile, instance.category.id)


class ContractorSkillViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContractorSkillSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_skills(self.own_profile)

    def perform_create(self, serializer):
        AccountCommands.add_skill(
            user_profile=self.own_profile,
            name=serializer.validated_data['name'],
            level=serializer.validated_data.get('level', '')
        )

    def perform_destroy(self, instance):
        AccountCommands.remove_skill(self.own_profile, instance.id)


class ProfessionalExperienceViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProfessionalExperienceSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_experiences(self.own_profile)

    def perform_create(self, serializer):
        AccountCommands.add_experience(
            user_profile=self.own_profile,
            company=serializer.validated_data['company'],
            position=serializer.validated_data['position'],
            description=serializer.validated_data.get('description', ''),
            start_date=serializer.validated_data['start_date'],
            end_date=serializer.validated_data.get('end_date'),
            is_current=serializer.validated_data.get('is_current', False)
        )

    def perform_destroy(self, instance):
        AccountCommands.remove_experience(self.own_profile, instance.id)


class AcademicTrainingViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = AcademicTrainingSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_academic_trainings(self.own_profile)

    def perform_create(self, serializer):
        AccountCommands.add_academic_training(
            user_profile=self.own_profile,
            institution=serializer.validated_data['institution'],
            degree=serializer.validated_data['degree'],
            field_of_study=serializer.validated_data.get('field_of_study', ''),
            start_date=serializer.validated_data['start_date'],
            end_date=serializer.validated_data.get('end_date'),
            is_current=serializer.validated_data.get('is_current', False)
        )

    def perform_destroy(self, instance):
        AccountCommands.remove_academic_training(self.own_profile, instance.id)


class ProfessionalCourseViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProfessionalCourseSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_courses(self.own_profile)

    def perform_create(self, serializer):
        AccountCommands.add_course(
            user_profile=self.own_profile,
            title=serializer.validated_data['title'],
            institution=serializer.validated_data['institution'],
            completion_date=serializer.validated_data['completion_date'],
            hours=serializer.validated_data.get('hours')
        )

    def perform_destroy(self, instance):
        AccountCommands.remove_course(self.own_profile, instance.id)


class ProfessionalCertificationViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = ProfessionalCertificationSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_certifications(self.own_profile)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cert = AccountCommands.add_certification(
            user_profile=self.own_profile,
            name=serializer.validated_data['name'],
            issuing_organization=serializer.validated_data['issuing_organization'],
            issue_date=serializer.validated_data['issue_date'],
            expiration_date=serializer.validated_data.get('expiration_date'),
            credential_id=serializer.validated_data.get('credential_id', ''),
            credential_url=serializer.validated_data.get('credential_url', ''),
            document=request.FILES.get('document')
        )
        return Response(ProfessionalCertificationSerializer(cert).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        AccountCommands.remove_certification(self.own_profile, instance.id)


class SuccessCaseViewSet(ContractorProfileScopedMixin, viewsets.ModelViewSet):
    serializer_class = SuccessCaseSerializer

    def get_queryset(self):
        return ContractorCVSelector.list_success_cases(self.own_profile)

    def create(self, request, *args, **kwargs):
        title = request.data.get('title')
        description = request.data.get('description')
        completion_date = request.data.get('completion_date')
        images = request.FILES.getlist('images') or request.data.getlist('images', [])

        case = AccountCommands.add_success_case(
            user_profile=self.own_profile,
            title=title,
            description=description,
            completion_date=completion_date,
            images=images
        )
        return Response(SuccessCaseSerializer(case).data, status=status.HTTP_201_CREATED)

    def perform_destroy(self, instance):
        AccountCommands.remove_success_case(self.own_profile, instance.id)


# ─── Availability ViewSet ───────────────────────────────────────────────────

class AvailabilityViewSet(viewsets.GenericViewSet):
    """
    Gestiona slots de disponibilidad profesional.

    Endpoints publicos (GET):
      - GET /availability/?profile=<uuid>&start=<date>&end=<date>

    Endpoints del profesional (autenticado + propietario):
      - GET  /availability/my-schedule/
      - POST /availability/bulk-create/
      - PATCH /availability/{id}/update-status/

    Endpoints del cliente (autenticado):
      - POST /availability/{id}/lock/
    """
    queryset = AvailabilitySelector.list_all()
    serializer_class = AvailabilityOutputSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return AvailabilitySelector.list_all()

    # ── GET /availability/ ──────────────────────────────────────────
    def list(self, request):
        """Lista slots AVAILABLE filtrados por ?profile=<uuid>&start=&end=."""
        profile_uuid = request.query_params.get('profile')
        start        = request.query_params.get('start')
        end          = request.query_params.get('end')

        if not profile_uuid:
            return Response(
                {'detail': 'El parametro ?profile=<uuid> es obligatorio.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slots = AvailabilitySelector.get_available_slots(
            profile_uuid=profile_uuid,
            start_date=start,
            end_date=end,
        )
        serializer = AvailabilityOutputSerializer(slots, many=True)
        return Response(serializer.data)

    # ── GET /availability/my-schedule/ ─────────────────────────────
    @action(
        detail=False,
        methods=['get'],
        url_path='my-schedule',
        permission_classes=[IsServiceProviderUser],
    )
    def my_schedule(self, request):
        """Retorna todos los slots del profesional autenticado (agenda completa)."""
        try:
            profile = ProfileResolver.resolve(request.user, expected_types=SERVICE_PROVIDER_TYPES)
        except MissingRequiredProfile:
            return Response(
                {'detail': 'El usuario no tiene un perfil de profesional.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        start = request.query_params.get('start')
        end   = request.query_params.get('end')

        slots = AvailabilitySelector.get_full_schedule(
            profile_uuid=str(profile.uuid),
            start_date=start,
            end_date=end,
        )
        serializer = AvailabilityOutputSerializer(slots, many=True)
        return Response(serializer.data)

    # ── POST /availability/bulk-create/ ──────────────────────────
    @action(
        detail=False,
        methods=['post'],
        url_path='bulk-create',
        permission_classes=[IsServiceProviderUser],
    )
    def bulk_create(self, request):
        """Genera bloques de disponibilidad masivos para el profesional autenticado."""
        try:
            profile = ProfileResolver.resolve(request.user, expected_types=SERVICE_PROVIDER_TYPES)
        except MissingRequiredProfile:
            return Response(
                {'detail': 'El usuario no tiene un perfil de profesional.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = AvailabilityBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        created = AvailabilityCommands.create_availability_blocks(
            user_profile=profile,
            start_date=d['start_date'],
            end_date=d['end_date'],
            work_start_hour=d['work_start_hour'],
            work_end_hour=d['work_end_hour'],
            slot_duration_hours=d['slot_duration_hours'],
            exclude_weekends=d['exclude_weekends'],
            notes=d.get('notes', ''),
        )
        return Response(
            {
                'created_count': len(created),
                'created': len(created),
                'detail': f'{len(created)} slots generados exitosamente.'
            },
            status=status.HTTP_201_CREATED,
        )

    # ── POST /availability/{id}/lock/ ────────────────────────────
    @action(
        detail=True,
        methods=['post'],
        url_path='lock',
        permission_classes=[permissions.IsAuthenticated],
    )
    def lock(self, request, pk=None):
        """Bloquea un slot temporalmente (15 min) para el cliente autenticado."""
        import datetime
        from django.utils import timezone

        slot = AvailabilityCommands.lock_slot_temporarily(
            slot_id=pk,
            requesting_user=request.user,
        )
        # Calcular timestamp de expiracion (ahora + 15 min) para el frontend
        expires_at = timezone.now() + datetime.timedelta(seconds=900)
        return Response(
            {
                'status': 'success',
                'slot': AvailabilityOutputSerializer(slot).data,
                'expires_at': expires_at.isoformat(),
                'countdown_seconds': 900,
                'detail': 'Slot bloqueado. Tienes 15 minutos para completar el pago.',
            },
            status=status.HTTP_200_OK,
        )

    # ── PATCH /availability/{id}/update-status/ ──────────────────
    @action(
        detail=True,
        methods=['patch'],
        url_path='update-status',
        permission_classes=[permissions.IsAuthenticated],
    )
    def update_status(self, request, pk=None):
        """Permite al profesional cambiar el estado de su propio slot."""
        serializer = AvailabilityStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # [CORREGIDO 2026-08-04, hallazgo M7 de AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md]:
        # notes ahora viaja al Command (que decide si escribirlo) en vez de que el ViewSet
        # mute el modelo directo despues de la llamada.
        slot = AvailabilityCommands.update_slot_status(
            slot_id=pk,
            new_status=serializer.validated_data['status'],
            requesting_user=request.user,
            notes=serializer.validated_data.get('notes'),
        )
        return Response(AvailabilityOutputSerializer(slot).data)


class AdminContractorPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminContractorViewSet(viewsets.GenericViewSet):
    """
    Panel administrativo de profesionales del marketplace (/panel/profesionales).
    Solo admin -- a diferencia de ContractorProfileViewSet (marketplace publico),
    lista TODOS los perfiles service-provider (activos e inactivos).
    """
    queryset = UserProfile.objects.none()
    serializer_class = AdminContractorSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminContractorPagination
    lookup_field = 'uuid'

    def get_queryset(self):
        params = self.request.query_params
        return ContractorAdminSelector.list_all_for_admin(
            user_type=params.get('user_type', ''),
            is_active=params.get('is_active', ''),
            is_available=params.get('is_available', ''),
            search=params.get('search', ''),
        )

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(AdminContractorSerializer(page, many=True).data)
        return Response(AdminContractorSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def metrics(self, request):
        return Response(ContractorAdminSelector.get_metrics())

    @action(detail=True, methods=['patch'], url_path='toggle-availability')
    def toggle_availability(self, request, uuid=None):
        profile = ContractorProfileSelector.get_by_uuid(uuid)
        is_available = request.data.get('is_available')
        if not isinstance(is_available, bool):
            return Response(
                {'detail': 'El campo is_available es requerido y debe ser booleano.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        AccountCommands.set_technician_availability(profile.user, is_available)
        return Response(AdminContractorSerializer(profile).data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, uuid=None):
        """Agenda completa (todos los estados) del profesional -- uso exclusivo del admin."""
        get_object_or_404(UserProfile, uuid=uuid, is_deleted=False)
        slots = AvailabilitySelector.get_full_schedule(profile_uuid=uuid)
        return Response(AvailabilityOutputSerializer(slots, many=True).data)
