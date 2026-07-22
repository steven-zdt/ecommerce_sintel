"""
Punto unico de acceso a los perfiles de un User.

Ningun consumidor nuevo debe hacer user.profile / user.technician_profile /
user.dispatcher_profile directamente -- usar estos metodos. Ver
accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md para la politica completa.
"""
from accounts.exceptions import MissingRequiredProfile, ProfileMismatchError


class ProfileResolver:

    @staticmethod
    def get_profile(user):
        """UserProfile o None. No lanza -- para call sites que toleran ausencia de perfil."""
        return getattr(user, 'profile', None)

    @staticmethod
    def resolve(user, expected_types=None):
        """
        UserProfile obligatorio. Lanza MissingRequiredProfile si no existe, o
        ProfileMismatchError si expected_types fue provisto y el user_type no esta incluido.
        """
        profile = ProfileResolver.get_profile(user)
        if profile is None:
            raise MissingRequiredProfile(user, 'accounts.UserProfile')
        if expected_types is not None and profile.user_type not in expected_types:
            raise ProfileMismatchError(user, expected_types, profile.user_type)
        return profile

    @staticmethod
    def get_type(user):
        profile = ProfileResolver.get_profile(user)
        return profile.user_type if profile else None

    @staticmethod
    def has_type(user, allowed_types) -> bool:
        user_type = ProfileResolver.get_type(user)
        return user_type is not None and user_type in allowed_types

    @staticmethod
    def get_technician_profile(user):
        return getattr(user, 'technician_profile', None)

    @staticmethod
    def resolve_technician(user):
        profile = ProfileResolver.get_technician_profile(user)
        if profile is None:
            raise MissingRequiredProfile(user, 'accounts.TechnicianProfile')
        return profile

    @staticmethod
    def get_dispatcher_profile(user):
        return getattr(user, 'dispatcher_profile', None)

    @staticmethod
    def resolve_dispatcher(user):
        profile = ProfileResolver.get_dispatcher_profile(user)
        if profile is None:
            raise MissingRequiredProfile(user, 'operations.DispatcherProfile')
        return profile

    @staticmethod
    def get_verification(user):
        """UserVerification (KYC) o None. No lanza -- usado por el gate de login."""
        return getattr(user, 'kyc_verification', None)
