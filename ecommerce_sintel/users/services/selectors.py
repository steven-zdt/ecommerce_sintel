from django.http import Http404
from django.db.models import Q, QuerySet
from rest_framework_simplejwt.tokens import RefreshToken
from ..models import User, UserAuditLog


def _qs_with_profiles():
    return (
        User.objects
        .select_related('profile', 'technician_profile', 'dispatcher_profile')
        .prefetch_related('groups')
    )


_ORDERING_WHITELIST = {'date_joined', '-date_joined', 'email', '-email', 'last_login', '-last_login'}


class UserSelector:
    @staticmethod
    def get_by_email(email: str) -> User:
        try:
            return _qs_with_profiles().get(email=email)
        except User.DoesNotExist:
            raise Http404("Usuario no encontrado.")

    @staticmethod
    def get_by_id(user_id: int) -> User:
        try:
            return _qs_with_profiles().get(id=user_id)
        except User.DoesNotExist:
            raise Http404("Usuario no encontrado.")

    @staticmethod
    def list_all(
        search: str = '',
        user_type: str = '',
        is_active: str = '',
        is_verified: str = '',
        company: str = '',
        city: str = '',
        country: str = '',
        ordering: str = '-date_joined',
    ) -> QuerySet:
        qs = _qs_with_profiles().filter(is_deleted=False)

        if search:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(profile__first_name__icontains=search)
                | Q(profile__last_name__icontains=search)
                | Q(profile__document__icontains=search)
                | Q(profile__company__icontains=search)
                | Q(profile__phone_number__icontains=search)
            ).distinct()
        if user_type:
            qs = qs.filter(profile__user_type=user_type)
        if is_active in ('true', 'false'):
            qs = qs.filter(is_active=is_active == 'true')
        if is_verified in ('true', 'false'):
            qs = qs.filter(is_verified=is_verified == 'true')
        if company:
            qs = qs.filter(profile__company__icontains=company)
        if city:
            qs = qs.filter(profile__city__icontains=city)
        if country:
            qs = qs.filter(profile__country__icontains=country)

        return qs.order_by(ordering if ordering in _ORDERING_WHITELIST else '-date_joined')


class UserAuditLogSelector:
    @staticmethod
    def list_for_user(user) -> QuerySet:
        return UserAuditLog.objects.filter(target_user=user).order_by('-created_at')
