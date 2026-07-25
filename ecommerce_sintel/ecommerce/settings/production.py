from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = config('DEBUG', default=False, cast=bool)

# Fail-safe: settings.production NUNCA debe correr con DEBUG=True (expondria
# stack traces, SQL y configuracion a cualquier visitante ante un 500). Si se
# necesita DEBUG, usar ecommerce.settings.development. Ver C-01 de la auditoria.
if DEBUG:
    raise ImproperlyConfigured(
        'DEBUG=True es invalido con ecommerce.settings.production. '
        'Para desarrollo usa DJANGO_SETTINGS_MODULE=ecommerce.settings.development.'
    )

# Cache: ver switch CACHE_BACKEND (redis|locmem) en base.py

# Configuración de base de datos para producción (PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default=5432, cast=int),
    }
}

# Seguridad adicional en producción
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Nginx/cloudflared terminan TLS antes de Daphne (ver roadmap Fase 9 y 11):
# sin esto, Django ve toda request como HTTP plano y SECURE_SSL_REDIRECT
# entraria en bucle de redirects.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Dominios de produccion (ver roadmap Fase 6). Vacio por defecto -- se
# configura via .env.production, nunca hardcodeado (Fase 16).
CSRF_TRUSTED_ORIGINS = [
    origin for origin in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if origin
]

# Segunda capa de F-01: en produccion el secreto de eventos de Wompi es
# obligatorio. Sin el, _verify_wompi_event_signature() ya rechaza (fail-closed),
# pero es mejor no arrancar en absoluto que operar sin poder verificar webhooks
# de pago.
if not config('WOMPI_EVENTS_SECRET', default=''):
    raise ImproperlyConfigured(
        'WOMPI_EVENTS_SECRET es obligatorio en produccion (verificacion de '
        'firma de los webhooks de pago Wompi).'
    )

# Optimización de archivos estáticos (Whitenoise)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
