"""
Permisos DRF centralizados.

Con la nueva arquitectura:
  - Administradores: is_staff=True + is_superuser=True (solo via createsuperuser CLI)
  - Clasificacion de perfil: accounts.UserProfile.user_type, resuelto siempre via
    accounts.services.profile_resolver.ProfileResolver (nunca acceder a
    request.user.profile/.technician_profile/.dispatcher_profile directamente).
  - No existe campo 'role' en User.

Grupos de tipos (accounts.services.profile_registry — fuente unica de verdad, agregar un tipo
nuevo ahi no requiere tocar ninguna clase de acá):
  BUYER_TYPES            — pueden comprar / alquilar / contratar servicios
  SERVICE_PROVIDER_TYPES — pueden ofrecer servicios, gestionar agenda y CV profesional
  OPERATIONAL_TYPES      — personal operativo (incluye TRANSPORTER, excluye CUSTOMER)
"""
from rest_framework.permissions import BasePermission
from accounts.services.profile_resolver import ProfileResolver
from accounts.services.profile_registry import BUYER_TYPES, SERVICE_PROVIDER_TYPES, OPERATIONAL_TYPES


def _active(user) -> bool:
    return bool(user and user.is_authenticated and user.is_active)


def _is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff and user.is_superuser)


class IsAdminUser(BasePermission):
    """
    Solo usuarios con is_staff=True y is_superuser=True pueden acceder.
    Creados exclusivamente por CLI (createsuperuser); la API nunca los crea.
    """
    message = "Solo administradores pueden acceder a este recurso."

    def has_permission(self, request, view):
        return _is_admin(request.user)


class IsAuthenticatedActiveUser(BasePermission):
    """
    Cualquier usuario autenticado y activo (no admin requerido).
    Reemplaza al antiguo IsCustomerUser basado en rol.
    """
    message = "Solo usuarios autenticados pueden acceder a este recurso."

    def has_permission(self, request, view):
        return _active(request.user)


# Alias de compatibilidad para codigo que importa IsCustomerUser
IsCustomerUser = IsAuthenticatedActiveUser


class RequiresProfileType(BasePermission):
    """
    Base reutilizable: las subclases solo declaran `allowed_types`. Evita duplicar la logica de
    "usuario activo + user_type en el conjunto permitido" en cada clase nueva.
    """
    allowed_types: frozenset = frozenset()
    message = "Tu perfil no tiene acceso a este recurso."

    def has_permission(self, request, view):
        return _active(request.user) and ProfileResolver.has_type(request.user, self.allowed_types)


class IsTechnicianUser(RequiresProfileType):
    """Solo usuarios cuyo perfil tenga user_type=TECHNICIAN."""
    allowed_types = frozenset({'TECHNICIAN'})
    message = "Solo tecnicos pueden acceder a este recurso."


class IsOwnerOrAdmin(BasePermission):
    """
    El usuario accede a su propio objeto, o cualquier admin accede a cualquiera.
    """
    message = "Solo puedes acceder a tus propios datos."

    def has_object_permission(self, request, view, obj):
        if _is_admin(request.user):
            return True
        if obj == request.user:
            return True
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        return False


class IsDispatcherUser(BasePermission):
    """
    Solo usuarios que tienen un DispatcherProfile activo y disponible.
    """
    message = "Solo despachadores activos pueden acceder a este recurso."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        dispatcher = ProfileResolver.get_dispatcher_profile(request.user)
        return dispatcher is not None and dispatcher.is_active


class IsDispatcherOrAdmin(BasePermission):
    """
    Despachadores activos o administradores.
    """
    message = "Solo despachadores o administradores pueden acceder."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if _is_admin(request.user):
            return True
        dispatcher = ProfileResolver.get_dispatcher_profile(request.user)
        return dispatcher is not None and dispatcher.is_active


class IsOperationalUser(BasePermission):
    """Personal activo que puede consultar y ejecutar tareas asignadas."""
    message = "Solo personal operativo puede acceder a este recurso."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if ProfileResolver.has_type(request.user, OPERATIONAL_TYPES):
            return True
        dispatcher = ProfileResolver.get_dispatcher_profile(request.user)
        return bool(dispatcher and dispatcher.is_active)


class IsAdminOrReadOnly(BasePermission):
    """
    Admins pueden escribir; el resto solo lee (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return _is_admin(request.user)


# ---------------------------------------------------------------------------
# Permisos granulares por perfil de usuario (Plan A)
# ---------------------------------------------------------------------------

class IsBuyerUser(RequiresProfileType):
    """
    Tipos que pueden comprar, alquilar y contratar servicios:
    CUSTOMER, TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR.
    Excluye TRANSPORTER y ACCOUNTANT (personal operativo sin acceso a compras).
    """
    allowed_types = BUYER_TYPES
    message = "Solo compradores pueden acceder a este recurso."


class IsBuyerOrAdmin(BasePermission):
    """
    IsBuyerUser + administradores. Usar en cart, orders, renting.
    """
    message = "Solo compradores o administradores pueden acceder a este recurso."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if _is_admin(request.user):
            return True
        return ProfileResolver.has_type(request.user, BUYER_TYPES)


class IsServiceProviderUser(RequiresProfileType):
    """
    Tipos que proveen servicios y gestionan agenda / CV profesional:
    TECHNICIAN, PROFESSIONAL, SPECIALIST, CONTRACTOR.
    Excluye CUSTOMER, TRANSPORTER y ACCOUNTANT.
    """
    allowed_types = SERVICE_PROVIDER_TYPES
    message = "Solo proveedores de servicio pueden acceder a este recurso."


class IsServiceProviderOrAdmin(BasePermission):
    """
    IsServiceProviderUser + administradores.
    """
    message = "Solo proveedores de servicio o administradores pueden acceder."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if _is_admin(request.user):
            return True
        return ProfileResolver.has_type(request.user, SERVICE_PROVIDER_TYPES)


class IsServiceProviderOrUpgrading(BasePermission):
    """
    SERVICE_PROVIDER_TYPES ya aprobados, O un CUSTOMER con una solicitud de
    upgrade en curso (kyc.UserVerification.requested_user_type seteado por
    KycCommands.request_upgrade) -- necesario para que pueda completar su
    perfil profesional (especialidades/skills/CV/certificaciones) ANTES de
    que el KYC del upgrade sea aprobado, siguiendo el orden del wizard
    "Convertirme en Profesional" (tipo -> perfil -> documentos -> revision).
    Usar SOLO en las 7 ViewSets de CV (ContractorProfileScopedMixin) -- no
    reemplaza IsServiceProviderUser en otros dominios (agenda de tecnicos,
    etc.), donde un upgrade pendiente NO debe dar acceso todavia.
    """
    message = "Solo proveedores de servicio (o con un upgrade profesional en curso) pueden acceder."

    def has_permission(self, request, view):
        if not _active(request.user):
            return False
        if ProfileResolver.has_type(request.user, SERVICE_PROVIDER_TYPES):
            return True
        verification = ProfileResolver.get_verification(request.user)
        return bool(verification and verification.requested_user_type)


class IsTransporterUser(RequiresProfileType):
    """
    Solo usuarios con user_type == TRANSPORTER.
    """
    allowed_types = frozenset({'TRANSPORTER'})
    message = "Solo transportistas pueden acceder a este recurso."


class IsAccountantUser(RequiresProfileType):
    """
    Solo usuarios con user_type == ACCOUNTANT.
    """
    allowed_types = frozenset({'ACCOUNTANT'})
    message = "Solo contadores pueden acceder a este recurso."
