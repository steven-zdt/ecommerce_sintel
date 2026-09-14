from decimal import Decimal
from django.db.models import Avg, Count, FloatField, Q, QuerySet, Value, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings


class ContractorRecommendationSelector:
    """
    Recomienda contratistas compatibles con una categoria de servicio.
    Ordenamiento: calificacion promedio DESC, numero de certificaciones DESC.
    Solo devuelve perfiles activos con especialidad en la categoria.
    """

    @staticmethod
    def get_compatible_professionals(service_category_id, priority=None, limit=10):
        from accounts.models import UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        qs = (
            UserProfile.objects
            .filter(
                is_deleted=False,
                user__is_active=True,
                user_type__in=SERVICE_PROVIDER_TYPES,
                contractor_specialties__category_id=service_category_id,
                contractor_specialties__is_deleted=False,
            )
            .select_related('user')
            .prefetch_related(
                'contractor_specialties__category',
                'contractor_skills',
                'professional_certifications',
                'academic_trainings',
                'professional_courses',
                'professional_experiences',
                'success_cases',
                'contractor_reviews',
            )
            .annotate(
                avg_rating=Coalesce(
                    (
                        Avg('contractor_reviews__quality_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__punctuality_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__professionalism_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__communication_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__compliance_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField())
                    ) / 5,
                    Value(0.0, output_field=FloatField()),
                    output_field=FloatField(),
                ),
                cert_count=Count(
                    'professional_certifications',
                    filter=Q(professional_certifications__is_deleted=False),
                ),
            )
            .order_by('-avg_rating', '-cert_count')
            .distinct()
        )

        if limit:
            qs = qs[:limit]

        return qs


class AccountSelector:
    @staticmethod
    def get_tokens_for_user(user) -> dict:
        refresh = RefreshToken.for_user(user)
        refresh['is_staff'] = user.is_staff
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }


class ContractorCVSelector:
    """
    Lectura del CV profesional propio (ARCH-M1).

    Las 7 ViewSets de CV (ContractorProfileScopedMixin) hacian el mismo
    filtro ORM inline en su get_queryset(). El scope real (owner) lo sigue
    imponiendo el caller pasando su propio user_profile -- estos metodos no
    resuelven el perfil, solo filtran por el que reciben.
    """

    @staticmethod
    def list_specialties(user_profile) -> QuerySet:
        from accounts.models import ContractorSpecialty
        return ContractorSpecialty.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_skills(user_profile) -> QuerySet:
        from accounts.models import ContractorSkill
        return ContractorSkill.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_experiences(user_profile) -> QuerySet:
        from accounts.models import ProfessionalExperience
        return ProfessionalExperience.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_academic_trainings(user_profile) -> QuerySet:
        from accounts.models import AcademicTraining
        return AcademicTraining.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_courses(user_profile) -> QuerySet:
        from accounts.models import ProfessionalCourse
        return ProfessionalCourse.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_certifications(user_profile) -> QuerySet:
        from accounts.models import ProfessionalCertification
        return ProfessionalCertification.objects.filter(user_profile=user_profile, is_deleted=False)

    @staticmethod
    def list_success_cases(user_profile) -> QuerySet:
        from accounts.models import SuccessCase
        return SuccessCase.objects.filter(user_profile=user_profile, is_deleted=False)


class ContractorProfileSelector:
    """Perfiles de contratista del marketplace publico (ARCH-M1)."""

    @staticmethod
    def list_public() -> QuerySet:
        from accounts.models import UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
        return UserProfile.objects.filter(
            is_deleted=False,
            user_type__in=SERVICE_PROVIDER_TYPES,
        )

    @staticmethod
    def get_by_uuid(profile_uuid: str):
        from django.shortcuts import get_object_or_404
        from accounts.models import UserProfile
        return get_object_or_404(
            UserProfile.objects.select_related('user'), uuid=profile_uuid, is_deleted=False,
        )


class ContractorSearchSelector:
    @staticmethod
    def search_contractors(category_slug=None, filters=None):
        from accounts.models import UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        filters = filters or {}

        qs = (
            UserProfile.objects
            .filter(
                is_deleted=False,
                user__is_active=True,
                user_type__in=SERVICE_PROVIDER_TYPES,
            )
            .select_related('user')
            .prefetch_related(
                'contractor_specialties__category',
                'contractor_skills',
                'professional_certifications',
                'academic_trainings',
                'professional_courses',
                'professional_experiences',
                'success_cases',
                'contractor_reviews',
            )
            .annotate(
                avg_rating=Coalesce(
                    (
                        Avg('contractor_reviews__quality_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__punctuality_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__professionalism_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__communication_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField()) +
                        Avg('contractor_reviews__compliance_rating',
                            filter=Q(contractor_reviews__is_deleted=False),
                            output_field=FloatField())
                    ) / 5,
                    Value(0.0, output_field=FloatField()),
                    output_field=FloatField(),
                ),
                review_count=Count(
                    'contractor_reviews',
                    filter=Q(contractor_reviews__is_deleted=False),
                ),
                cert_count=Count(
                    'professional_certifications',
                    filter=Q(professional_certifications__is_deleted=False),
                ),
            )
        )

        if category_slug:
            qs = qs.filter(
                contractor_specialties__category__slug=category_slug,
                contractor_specialties__is_deleted=False,
            ).distinct()

        max_hourly_rate = filters.get('max_hourly_rate')
        if max_hourly_rate:
            qs = qs.filter(hourly_rate__lte=Decimal(str(max_hourly_rate)))

        user_type = filters.get('user_type')
        if user_type:
            qs = qs.filter(user_type=user_type)

        min_rating = filters.get('min_rating')
        if min_rating:
            qs = qs.filter(avg_rating__gte=Decimal(str(min_rating)))

        return qs.order_by('-avg_rating', '-review_count', '-cert_count')


class ContractorAdminSelector:
    """
    Consultas para el panel administrativo de profesionales (/panel/profesionales).
    A diferencia de ContractorSearchSelector (marketplace publico), no filtra por
    is_active/is_available -- el admin necesita ver TODOS los perfiles service-provider.
    """

    @staticmethod
    def list_all_for_admin(user_type='', is_active='', is_available='', search=''):
        from accounts.models import UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        from orders.models import Order
        qs = (
            UserProfile.objects
            .filter(is_deleted=False, user_type__in=SERVICE_PROVIDER_TYPES)
            .select_related('user', 'user__technician_profile')
            .prefetch_related(
                'contractor_specialties__category',
                'contractor_skills',
                'professional_certifications',
                'academic_trainings',
                'professional_courses',
                'professional_experiences',
                'success_cases',
                'contractor_reviews',
            )
            .annotate(
                total_services_completed=Count(
                    'user__assigned_services',
                    filter=Q(user__assigned_services__order__status=Order.STATUS_COMPLETED),
                    distinct=True,
                )
            )
        )

        if user_type:
            qs = qs.filter(user_type=user_type)
        if is_active in ('true', 'false'):
            qs = qs.filter(user__is_active=(is_active == 'true'))
        if is_available in ('true', 'false'):
            qs = qs.filter(user__technician_profile__is_available=(is_available == 'true'))
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(user__email__icontains=search)
            )

        return qs.order_by('-created_at')

    @staticmethod
    def get_metrics():
        from accounts.models import ContractorReview, UserProfile
        from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES

        base = UserProfile.objects.filter(is_deleted=False, user_type__in=SERVICE_PROVIDER_TYPES)
        total = base.count()
        by_type = dict(
            base.values('user_type').annotate(count=Count('id')).values_list('user_type', 'count')
        )
        active_count = base.filter(user__is_active=True).count()
        available_count = base.filter(user__technician_profile__is_available=True).count()
        unavailable_count = base.filter(user__technician_profile__is_available=False).count()

        rating_agg = ContractorReview.objects.filter(
            is_deleted=False, contractor__in=base,
        ).aggregate(
            avg_quality=Avg('quality_rating'),
            avg_punctuality=Avg('punctuality_rating'),
            avg_professionalism=Avg('professionalism_rating'),
            avg_communication=Avg('communication_rating'),
            avg_compliance=Avg('compliance_rating'),
        )
        factor_averages = [v for v in rating_agg.values() if v is not None]
        avg_rating = round(sum(factor_averages) / len(factor_averages), 2) if factor_averages else 0.0

        return {
            'total': total,
            'by_type': by_type,
            'active_count': active_count,
            'inactive_count': total - active_count,
            'available_count': available_count,
            'unavailable_count': unavailable_count,
            'average_rating': avg_rating,
        }


class AvailabilitySelector:
    """
    Consultas de lectura para los slots de disponibilidad.
    """

    @staticmethod
    def list_all() -> QuerySet:
        """Todos los slots no eliminados (ARCH-M1).

        Base de AvailabilityViewSet.get_queryset(); el filtrado real por
        perfil/rango lo hacen get_available_slots()/get_full_schedule().
        """
        from accounts.models import ProfessionalAvailability
        return ProfessionalAvailability.objects.filter(is_deleted=False).select_related(
            'user_profile__user', 'booked_by',
        )

    @staticmethod
    def get_available_slots(profile_uuid, start_date=None, end_date=None):
        """
        Retorna solo los slots con estado AVAILABLE para el perfil indicado.
        Se puede acotar el rango de fechas con start_date / end_date (str ISO o date).
        """
        from accounts.models import ProfessionalAvailability, UserProfile
        import datetime

        try:
            profile = UserProfile.objects.get(uuid=profile_uuid, is_deleted=False)
        except UserProfile.DoesNotExist:
            return ProfessionalAvailability.objects.none()

        qs = ProfessionalAvailability.objects.filter(
            user_profile=profile,
            status=ProfessionalAvailability.AVAILABLE,
            is_deleted=False,
        )

        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.date.fromisoformat(start_date)
            qs = qs.filter(date__gte=start_date)

        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.date.fromisoformat(end_date)
            qs = qs.filter(date__lte=end_date)

        return qs.order_by('date', 'start_time')

    @staticmethod
    def get_full_schedule(profile_uuid, start_date=None, end_date=None):
        """
        Retorna TODOS los slots (cualquier estado) del profesional.
        Para uso exclusivo del panel del profesional.
        """
        from accounts.models import ProfessionalAvailability, UserProfile
        import datetime

        try:
            profile = UserProfile.objects.get(uuid=profile_uuid, is_deleted=False)
        except UserProfile.DoesNotExist:
            return ProfessionalAvailability.objects.none()

        qs = ProfessionalAvailability.objects.filter(
            user_profile=profile,
            is_deleted=False,
        )

        if start_date:
            if isinstance(start_date, str):
                try:
                    from datetime import date
                    start_date = date.fromisoformat(start_date)
                except ValueError:
                    start_date = None
            if start_date:
                qs = qs.filter(date__gte=start_date)

        return qs.order_by('date', 'start_time')
