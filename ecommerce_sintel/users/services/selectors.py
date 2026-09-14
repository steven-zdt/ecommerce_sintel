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


class UserTimelineSelector:
    """
    Fusiona 3 fuentes YA existentes en un timeline cronologico unico para un usuario:
    UserAuditLog (acciones administrativas), kyc.VerificationEvent (proceso KYC) y
    security.SecurityEvent (login/seguridad, con IP/user-agent ya capturados). Ninguna
    de las 3 se modifica -- solo se leen y normalizan a un shape comun. Imports diferidos
    (dentro del metodo) para evitar ciclos, mismo patron que security/notifications al
    ser consumidos desde otras apps.
    """

    @staticmethod
    def get_timeline(user, limit: int = 100) -> list[dict]:
        from kyc.models import VerificationEvent
        from security.models import SecurityEvent

        entries = []

        for log in UserAuditLog.objects.filter(target_user=user).order_by('-created_at')[:limit]:
            entries.append({
                'timestamp': log.created_at,
                'source': 'audit',
                'event_type': log.action,
                'description': log.get_action_display(),
                'actor_email': log.actor_email,
                'metadata': log.metadata,
            })

        for ev in VerificationEvent.objects.filter(verification__user=user).order_by('-created_at')[:limit]:
            entries.append({
                'timestamp': ev.created_at,
                'source': 'kyc',
                'event_type': ev.event_type,
                'description': ev.description or ev.get_event_type_display(),
                'actor_email': ev.actor_email,
                'metadata': ev.metadata,
            })

        for sec in SecurityEvent.objects.filter(user=user).order_by('-created_at')[:limit]:
            entries.append({
                'timestamp': sec.created_at,
                'source': 'security',
                'event_type': sec.event_type,
                'description': sec.get_event_type_display(),
                'actor_email': '',
                'metadata': {**sec.metadata, 'ip_address': sec.ip_address, 'user_agent': sec.user_agent},
            })

        entries.sort(key=lambda e: e['timestamp'], reverse=True)
        return entries[:limit]
