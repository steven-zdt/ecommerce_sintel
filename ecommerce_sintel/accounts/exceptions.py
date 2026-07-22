"""
Excepciones de dominio para el sistema de perfiles de usuario.

Politica de arquitectura de perfiles (ver accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md):
ningun consumidor de un perfil (permiso, comando, selector) debe continuar silenciosamente cuando
el perfil esperado no existe o no coincide con el tipo requerido -- debe lanzar una de estas
excepciones explicitas via accounts.services.profile_resolver.ProfileResolver.
"""


class ProfileError(Exception):
    """Base de todos los errores del dominio de perfiles."""


class MissingRequiredProfile(ProfileError):
    """El usuario no tiene el perfil requerido (UserProfile, TechnicianProfile, DispatcherProfile)."""

    def __init__(self, user, profile_kind: str = 'accounts.UserProfile'):
        self.user = user
        self.profile_kind = profile_kind
        super().__init__(
            f"El usuario {getattr(user, 'email', user)} no tiene un perfil de tipo '{profile_kind}'."
        )


class ProfileMismatchError(ProfileError):
    """El usuario tiene un perfil, pero su user_type no esta entre los tipos esperados."""

    def __init__(self, user, expected_types, actual_type):
        self.user = user
        self.expected_types = expected_types
        self.actual_type = actual_type
        super().__init__(
            f"El usuario {getattr(user, 'email', user)} tiene perfil '{actual_type}', "
            f"se esperaba uno de {sorted(expected_types)}."
        )
