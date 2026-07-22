"""
Registro central de perfiles permitidos por dominio.

Agregar un tipo de usuario nuevo en el futuro (o un nuevo grupo de dominio) solo requiere sumar
una entrada aca -- ninguna clase de permiso en users/api/permissions.py debe modificarse (Open/
Closed). Ver accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md para la politica completa.
"""
from accounts.models import UserProfile

BUYER_TYPES = frozenset({
    UserProfile.CUSTOMER,
    UserProfile.TECHNICIAN,
    UserProfile.PROFESSIONAL,
    UserProfile.SPECIALIST,
    UserProfile.CONTRACTOR,
})

SERVICE_PROVIDER_TYPES = frozenset({
    UserProfile.TECHNICIAN,
    UserProfile.PROFESSIONAL,
    UserProfile.SPECIALIST,
    UserProfile.CONTRACTOR,
})

OPERATIONAL_TYPES = SERVICE_PROVIDER_TYPES | {UserProfile.TRANSPORTER}

CONTRACTOR_ASSIGNABLE_TYPES = frozenset({
    UserProfile.CONTRACTOR,
    UserProfile.PROFESSIONAL,
    UserProfile.SPECIALIST,
})
