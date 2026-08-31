"""
Jerarquia de errores de la frontera Meta. Mismo criterio que
payment/online/wompi_client.py: se distingue explicitamente un fallo
DEFINITIVO (no reintentar, propagar) de uno TRANSITORIO (seguro de reintentar
con backoff), para que los callers (Celery tasks, commands) no tengan que
adivinar a partir del texto del error.
"""


class MetaApiError(Exception):
    """Error definitivo de la Graph API (4xx de negocio, parametros invalidos,
    activo inexistente). No reintentar automaticamente -- se propaga al caller."""


class MetaApiTransientError(MetaApiError):
    """Error transitorio (timeout, error de red, 5xx de Meta). Seguro de
    reintentar con backoff."""


class MetaAuthError(MetaApiError):
    """401/403: token invalido, expirado o sin los permisos/scope necesarios.
    Reintentar no ayuda -- requiere renovar el token en el secret manager."""


class MetaConfigError(MetaApiError):
    """Falta un valor de configuracion obligatorio (access token, phone number
    id, ad account id, ...). Se lanza ANTES de tocar la red, con el nombre del
    setting que falta, para no depender de un 400 opaco de Meta."""


class MetaRateLimitError(MetaApiTransientError):
    """Rate limit / throttling de la Graph API (HTTP 429 o error code de Meta
    4 / 17 / 32 / 613 / 80004). Transitorio pero conviene un backoff mas largo
    que un 5xx normal."""
