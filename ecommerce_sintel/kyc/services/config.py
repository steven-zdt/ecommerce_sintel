from accounts.services.profile_registry import SERVICE_PROVIDER_TYPES
from kyc.models import UserVerification, VerificationDocument, VerificationEvent

# Version vigente de los documentos legales de Habeas Data. Subir este valor
# cuando cambie el contenido de la Politica/Autorizacion/Terminos -- el
# ConsentRecord de cada aceptacion queda con la version vigente al momento,
# nunca se reescribe.
CURRENT_CONSENT_DOCUMENT_VERSION = '1.0'

ALLOWED_TRANSITIONS = {
    UserVerification.STATUS_PENDING: [
        UserVerification.STATUS_UNDER_REVIEW,
        UserVerification.STATUS_BLOCKED,
    ],
    UserVerification.STATUS_UNDER_REVIEW: [
        UserVerification.STATUS_APPROVED,
        UserVerification.STATUS_REJECTED,
        UserVerification.STATUS_PENDING,
        UserVerification.STATUS_BLOCKED,
    ],
    UserVerification.STATUS_REJECTED: [
        UserVerification.STATUS_UNDER_REVIEW,
        UserVerification.STATUS_BLOCKED,
    ],
    UserVerification.STATUS_APPROVED: [
        UserVerification.STATUS_BLOCKED,
    ],
    UserVerification.STATUS_BLOCKED: [],
    UserVerification.STATUS_EXPIRED: [
        UserVerification.STATUS_PENDING,
    ],
}

STATUS_TO_EVENT_TYPE = {
    UserVerification.STATUS_UNDER_REVIEW: VerificationEvent.SUBMITTED_FOR_REVIEW,
    UserVerification.STATUS_APPROVED:     VerificationEvent.APPROVED,
    UserVerification.STATUS_REJECTED:     VerificationEvent.REJECTED,
    UserVerification.STATUS_PENDING:      VerificationEvent.INFO_REQUESTED,
    UserVerification.STATUS_BLOCKED:      VerificationEvent.BLOCKED,
}

REQUIRED_DOC_TYPES = [
    VerificationDocument.CEDULA_FRONTAL,
    VerificationDocument.CEDULA_REVERSO,
    VerificationDocument.RUT,
    VerificationDocument.HOJA_VIDA,
    VerificationDocument.DIPLOMA,
]

# Motor de requisitos por tipo -- hoy los 4 SERVICE_PROVIDER_TYPES comparten
# exactamente los mismos documentos (no hay ninguna diferencia real todavia,
# no se inventa una), pero la forma de diccionario permite agregar un tipo
# nuevo (ej. ACCOUNTANT con TARJETA_PROFESIONAL) sumando una entrada, sin
# tocar KycCommands. REQUIRED_DOC_TYPES se conserva como fallback para
# verificaciones sin requested_user_type (profesionales previos a este
# rediseno, grandfathering).
REQUIRED_DOC_TYPES_BY_TYPE = {
    user_type: REQUIRED_DOC_TYPES for user_type in SERVICE_PROVIDER_TYPES
}


def get_required_doc_types(requested_user_type: str | None) -> list:
    return REQUIRED_DOC_TYPES_BY_TYPE.get(requested_user_type, REQUIRED_DOC_TYPES)

OPTIONAL_DOC_TYPES = [
    VerificationDocument.CERTIFICACION,
    VerificationDocument.ANTECEDENTES_POLICIA,
    VerificationDocument.ANTECEDENTES_CONTRALORIA,
    VerificationDocument.ANTECEDENTES_PROCURADURIA,
]

# doc_type -> (max_size_mb, extensiones permitidas)
DOC_TYPE_LIMITS = {
    VerificationDocument.CEDULA_FRONTAL: (5, ['.pdf', '.jpg', '.jpeg']),
    VerificationDocument.CEDULA_REVERSO: (5, ['.pdf', '.jpg', '.jpeg']),
    VerificationDocument.RUT:            (5, ['.pdf']),
    VerificationDocument.HOJA_VIDA:      (8, ['.pdf']),
    VerificationDocument.DIPLOMA:        (8, ['.pdf']),
    VerificationDocument.CERTIFICACION:  (8, ['.pdf']),
    VerificationDocument.ANTECEDENTES_POLICIA:      (5, ['.pdf']),
    VerificationDocument.ANTECEDENTES_CONTRALORIA:  (5, ['.pdf']),
    VerificationDocument.ANTECEDENTES_PROCURADURIA: (5, ['.pdf']),
    VerificationDocument.OTRO: (5, ['.pdf', '.jpg', '.jpeg', '.png']),
}
