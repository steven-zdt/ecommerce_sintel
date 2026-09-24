import os
import logging
from pathlib import Path
from datetime import timedelta
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',  # Must be before django.contrib.staticfiles
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'channels',
    'django_celery_beat',
    'django_tables2',
    'django_htmx',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Project Modules
    'accounts',
    'users',
    'shop',
    'inventory',
    'cart',
    'orders',
    'payment',
    'technical_services',
    'quotes',
    'marketing',
    'renting',
    'notifications',
    'support',
    'dashboard',
    'core',
    'operations',
    'kyc',
    'security',
    'organization',
    'seo',
    'shared',
    'ai_provider',
    'ai_knowledge',
    'customer_memory',
    'whatsapp',
    'django_vite',
]

# Configuración de Django-Vite
# IMPORTANTE: manifest_path DEBE coincidir exactamente con outDir definido en vite.config.js
# vite.config.js outDir = '../ecommerce_sintel/static/panel/js/bundle/'
# Vite 5+ genera el manifest en <outDir>/.vite/manifest.json
DJANGO_VITE = {
  "default": {
    "manifest_path": BASE_DIR / "static/panel/js/bundle/.vite/manifest.json",
    # STATICFILES_DIRS = [BASE_DIR / 'static'] hace que collectstatic preserve
    # la ruta completa (STATIC_ROOT/panel/js/bundle/...), pero vite_asset sin
    # static_url_prefix genera URLs relativas a la raiz de STATIC_URL
    # (/static/assets/...) -- 404 real encontrado al probar el despliegue en
    # produccion (Fase 22 del roadmap de Cloudflare Tunnel). Este prefijo
    # alinea las URLs generadas con donde realmente quedan los archivos.
    "static_url_prefix": "panel/js/bundle",
    # En desarrollo con HMR activo, cambiar a True y configurar host/port
    "dev_mode": config('VITE_DEV_MODE', default=False, cast=bool),
    "dev_server_host": config('VITE_DEV_SERVER_HOST', default='localhost'),
    "dev_server_port": config('VITE_DEV_SERVER_PORT', default=5173, cast=int),
  }
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
]

ROOT_URLCONF = 'ecommerce.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI / Channels
WSGI_APPLICATION = 'ecommerce.wsgi.application'
ASGI_APPLICATION = 'ecommerce.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://localhost:6379/0')],
            # Repaso de backlog (AUDITORIA/18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md B3,
            # 2026-08-03): antes sin declarar -- defaults de channels_redis (capacity=100,
            # expiry=60) nunca evaluados a proposito. Al superar capacity, el mensaje
            # simplemente NO se encola (solo un log INFO de la libreria, sin excepcion ni senal
            # a nadie). 'support_admins' es el grupo de mayor riesgo real: cada agente conectado
            # + cada broadcast de chat consume cupo de la MISMA cola. capacity=1000 da margen
            # real ante una rafaga (varios admins conectados durante un pico de mensajes) sin
            # cambiar el comportamiento observable hoy (muy por debajo del limite actual).
            "capacity": 1000,
            "expiry": 60,
        },
    },
}

# Database (Production will override this)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Cache — Redis por defecto (db=1, separado de Celery/Channels que usan db=0).
# Override con CACHE_BACKEND=locmem (env var) para correr sin Redis, p.ej. para
# aislar errores de entorno al depurar, sin tener que cambiar DJANGO_SETTINGS_MODULE.
CACHE_BACKEND = config('CACHE_BACKEND', default='redis')
if CACHE_BACKEND == 'locmem':
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
else:
    _redis_cache_base = config('REDIS_URL', default='redis://localhost:6379/0').rsplit('/', 1)[0]
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f'{_redis_cache_base}/1',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'ecommerce.validators.ComplexPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files — Archivos subidos por usuarios
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Storage privado de documentos KYC -- fuera de MEDIA_ROOT a proposito: ni el
# static() de Django en DEBUG ni el alias /media/ de nginx en produccion lo
# exponen. Unico acceso: kyc.api.views.VerificationDocumentViewSet.download.
KYC_PRIVATE_STORAGE_ROOT = config(
    'KYC_PRIVATE_STORAGE_ROOT', default=str(BASE_DIR / 'private_media' / 'kyc')
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# User Model
AUTH_USER_MODEL = 'users.User'

# DRF Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'ecommerce.api_exceptions.api_exception_handler',
    # Rate limiting de registro/login (AccountViewSet.get_throttles asigna el
    # scope por accion via ScopedRateThrottle -- ver accounts/api/views.py).
    'DEFAULT_THROTTLE_RATES': {
        'register': '5/hour',
        'login': '10/hour',
        'admin_login': '5/hour',
        'kyc_upload': '20/hour',
        'kyc_upgrade': '5/hour',
        'order_create': '30/hour',
        'password_reset_request': '5/hour',
        'password_reset_verify': '20/hour',
        'admin_password_reset_request': '5/hour',
        'admin_password_reset_verify': '20/hour',
        # A-03 (auditoria enterprise): antes sin ningun scope propio.
        'register_verify': '20/hour',
        'register_resend': '5/hour',
        # F-03 (auditoria enterprise): endpoints de payment sin ningun
        # throttle -- webhook queda sin scope a proposito (publico, firma
        # HMAC verificada aparte). transaction_status/confirmation SI
        # necesitan uno: [CORREGIDO 2026-08-04, hallazgo C1 de
        # AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md] la premisa de F-03
        # ("son de lectura") era incorrecta -- internamente disparan
        # _sync_wompi_status(), que puede mutar el estado de la Transaction.
        'payment_initialize': '30/hour',
        'payment_card_create': '10/hour',
        'payment_nequi_initialize': '10/hour',
        'payment_reconciliation': '60/hour',
        # Q-06 (auditoria enterprise): endpoints de quotes sin throttle.
        'quote_from_template': '30/hour',
        'quote_download_pdf': '60/hour',
        # S-04 (auditoria enterprise): endpoints de carrito sin throttle.
        'cart_mutate': '120/hour',
        'cart_checkout': '20/hour',
        # D-03 (auditoria enterprise): AiOpenSupportTicketView invoca un LLM
        # con costo real por mensaje y no tenia scope propio registrado.
        'ai_support_ticket': '30/hour',
        # Centro de Comunicacion (2026-07-31): endpoint publico (AllowAny,
        # visitantes anonimos incluidos) que solo escribe telemetria -- limite
        # generoso para uso legitimo normal, pero con tope real contra abuso.
        'communication_event': '60/hour',
    },
}

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Django Tables 2
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"
DJANGO_TABLES2_PAGE_RANGE = 10

# SimpleJWT
SIMPLE_JWT = {
    # QW-17 (quick win, auditoria 2026-07-16): 60min era una ventana demasiado
    # larga para un access token robado -- el frontend ya hace refresh
    # silencioso automatico en 401 (ver interceptor de useApi.js), asi que
    # acortar esto es transparente para el usuario.
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SECRET_KEY'),
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# Celery
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ROUTES = {
    'notifications.*': {'queue': 'notifications'},
    'marketing.*':     {'queue': 'marketing'},
    'accounts.*':      {'queue': 'default'},
}
# Sin esto, cualquier tarea de una app SIN entrada arriba (payment, orders,
# renting, support, etc.) cae en la cola nativa de Celery llamada 'celery' --
# que docker-compose.prod.yml NUNCA escucha (celery_worker corre con
# `-Q default,marketing,notifications`). Esas tareas se encolaban en Redis
# sin ningun worker consumiendolas, entre ellas
# payment.tasks.reconcile_pending_wompi_transactions (el fallback que
# reconcilia pagos Wompi cuyo webhook se perdio). Con esto, cualquier tarea
# no enrutada explicitamente cae en 'default', que si tiene worker asignado.
CELERY_TASK_DEFAULT_QUEUE = 'default'
# C-03 (auditoria enterprise): sin estos defaults, un worker que muere a mitad
# de tarea (OOM, restart de contenedor) pierde la tarea sin dejar rastro (ack
# ocurre al recibir, no al terminar), y una tarea colgada (HTTP a Wompi/
# WhatsApp/LLM sin limite) bloquea ese slot de worker para siempre. Seguro
# habilitarlo porque las tareas de este proyecto ya son idempotentes por
# diseno (unique_together en CampaignLog, idempotency_key en Payment/Orders).
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

# El scheduler de beat en este proyecto es django_celery_beat.schedulers.DatabaseScheduler
# (ver docker-compose: celery beat --scheduler django_celery_beat.schedulers:DatabaseScheduler),
# que lee su agenda de la BD (modelos PeriodicTask/CrontabSchedule), no de un dict
# CELERY_BEAT_SCHEDULE en settings -- ese dict seria ignorado por completo. Las tareas
# periodicas se registran via data migration (ver payment/migrations/0008_...py para
# reconcile_pending_wompi_transactions).

# CORS
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
# SEC-M2 (auditoria, doc 06): guard explicito -- development.py fija
# CORS_ALLOW_ALL_ORIGINS=True; sin este False explicito aqui, un
# DJANGO_SETTINGS_MODULE mal configurado en produccion (que solo cargue
# base.py sin production.py) heredaria el default de django-cors-headers,
# que es False, pero dejar la intencion explicita evita depender de ese
# default implicito si la libreria cambia su comportamiento en el futuro.
CORS_ALLOW_ALL_ORIGINS = False

# ── AI Core (Fase 7 — multicanal) ────────────────────────────────────────────
# sintel_ai NUNCA se expone a Internet: todos los canales (widget web,
# WhatsApp) llegan al Action Graph a traves de Django via esta URL interna.
AI_ENGINE_URL = config('AI_ENGINE_URL', default='http://sintel_ai:8100')
# Modo AI del chat de soporte (widget web reusa support/consumers.py).
AI_SUPPORT_CHAT_ENABLED = config('AI_SUPPORT_CHAT_ENABLED', default=False, cast=bool)
# Usuario bot que firma los mensajes del asistente en ChatMessage (FK sender
# NOT NULL). Inactivo y sin password utilizable -- jamas puede autenticarse.
AI_BOT_EMAIL = config('AI_BOT_EMAIL', default='asistente.ia@sintel.internal')
# Admin AI Assistant (/panel/asistente, mision Fase 3, 2026-09-16) -- kill
# switch independiente de AI_SUPPORT_CHAT_ENABLED (dominios distintos: ese es
# el chat de soporte al CLIENTE, este es el asistente de catalogo para el
# ADMIN). Congelado a pedido explicito del usuario (2026-09-16) hasta nueva
# orden -- default False. El codigo (Tools/agente/vista/UI) sigue intacto,
# solo el gateway de Django (dashboard/api/ai_assistant_views.py) lo bloquea.
ADMIN_AI_ASSISTANT_ENABLED = config('ADMIN_AI_ASSISTANT_ENABLED', default=False, cast=bool)
# Marketing -- CampaignMedia (PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md,
# Fase 12/13, 2026-09-23): limites reales y configurables, sin hardcodear en el modelo/serializer.
MARKETING_MEDIA_MAX_IMAGE_MB = config('MARKETING_MEDIA_MAX_IMAGE_MB', default=5, cast=int)
MARKETING_MEDIA_MAX_VIDEO_MB = config('MARKETING_MEDIA_MAX_VIDEO_MB', default=100, cast=int)
# Clave dedicada para cifrar en reposo AIProvider.api_key (shared/fields.py::
# EncryptedTextField, plan "CONFIGURACION DINAMICA DE MODELOS LOCALES", FASE 1,
# 2026-08-13). Si no se configura, el campo cae a derivar la clave de SECRET_KEY
# (funciona en dev sin configuracion extra) -- en produccion se recomienda fijar
# esta variable de forma independiente para poder rotarla sin tocar SECRET_KEY.
AI_PROVIDER_ENCRYPTION_KEY = config('AI_PROVIDER_ENCRYPTION_KEY', default='')
# Mision "Migracion Arquitectonica de WhatsApp" (2026-09-16, renombrado
# desde "QR"/"REST" de la mision anterior): unico switch real de mecanismo
# de conexion -- "QR_WEB_SESSION" (experimental, tercero) o
# "META_CLOUD_API" (oficial), nunca variables dispersas (USE_QR/
# ENABLE_WHATSAPP_API/etc). Default "META_CLOUD_API": es el UNICO mecanismo
# real que existe hoy en este repo (ver whatsapp/adapters/
# meta_cloud_api_adapter.py) -- "QR_WEB_SESSION" esta estructuralmente
# soportado pero BLOQUEADO por decision de negocio (ver
# AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md: riesgo real de perder la
# integracion oficial ya funcionando en el mismo numero de produccion).
WHATSAPP_CONNECTION_TYPE = config('WHATSAPP_CONNECTION_TYPE', default='META_CLOUD_API')

# Verify token del webhook entrante de WhatsApp (Meta Cloud API).
WHATSAPP_WEBHOOK_VERIFY_TOKEN = config('WHATSAPP_WEBHOOK_VERIFY_TOKEN', default='')

# Fase 6/22 del plan de migracion Baileys (AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md):
# secreto compartido con whatsapp_gateway/ (mismo valor que WA_GATEWAY_INTERNAL_TOKEN
# del lado del gateway) -- autentica el Event Bus Gateway->Django
# (notifications/api/whatsapp_gateway_webhook.py). Vacio por default: el
# endpoint queda fail-closed (rechaza todo) hasta que se configure
# explicitamente, igual criterio que META_APP_SECRET. Gateway todavia no
# esta en docker-compose (Fase 21) ni conectado a un numero real.
WHATSAPP_GATEWAY_TOKEN = config('WHATSAPP_GATEWAY_TOKEN', default='')

# Fase 8/22: URL base real de whatsapp_gateway/ (Django -> Gateway, direccion
# opuesta al Event Bus de arriba). Usado por whatsapp/clients/gateway_client.py
# desde whatsapp/adapters/qr_web_session_adapter.py. WHATSAPP_GATEWAY_ENABLED
# es el kill-switch explicito (Fase 22 lo pide separado de solo "hay URL") --
# ambos deben ser verdaderos para que QRWebSessionAdapter deje de comportarse
# como el stub original (WhatsAppQRNotImplementedError en cada metodo, ver
# whatsapp/adapters/qr_web_session_adapter.py) y empiece a hacer llamadas HTTP
# reales. Default deshabilitado: no cambia el comportamiento de dev/produccion
# existente sin configuracion explicita (mismo criterio "sin breaking change"
# que ya aplica WHATSAPP_CONNECTION_TYPE).
WHATSAPP_GATEWAY_URL = config('WHATSAPP_GATEWAY_URL', default='')
WHATSAPP_GATEWAY_ENABLED = config('WHATSAPP_GATEWAY_ENABLED', default=False, cast=bool)
# FASE 2 (auditoria WS/consumer/AI bridge, 2026-08-07): las trazas [WS]/[CHAT] de
# support/consumers.py, support/channels_auth.py y support/services/ai_bridge.py corren
# siempre a nivel INFO (conexion, sala, latencia, tools, status) sin contenido de mensajes.
# Con este flag en True, ademas incluyen el texto (truncado) del mensaje del cliente y de la
# respuesta del AI Engine -- para diagnosticar un recorrido completo puntual sin dejar
# contenido de conversaciones en logs de produccion por defecto.
SUPPORT_DEBUG_MODE = config('SUPPORT_DEBUG_MODE', default=False, cast=bool)
# Event Bus (Componente 8): slugs de NotificationTemplate que ademas de sus
# canales normales generan un mensaje proactivo del bot en la sala del cliente.
AI_PROACTIVE_SLUGS = [s.strip() for s in config('AI_PROACTIVE_SLUGS', default='').split(',') if s.strip()]

# Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sintel E-Commerce API',
    'DESCRIPTION': 'API REST para E-Commerce Headless con Tiempo Real',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # Fase 15 (AUDITORIA/29_AUDITORIA_OBSERVABILIDAD.md, 2026-08-03): {module} solo da
            # el nombre de archivo (ej. "tasks") -- 9 apps distintas tienen su propio tasks.py
            # (support/notifications/marketing/orders/payment/quotes/renting/accounts/
            # operations), todas indistinguibles entre si en los logs crudos de produccion.
            # {name} es el logger completo (logging.getLogger(__name__)), ej.
            # "support.tasks"/"notifications.tasks" -- ya usado consistentemente en todo el
            # proyecto via ese mismo patron, sin cambio de codigo necesario mas alla del
            # formatter.
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# ─── Marketing Channels ──────────────────────────────────────────────────────
# Email (SMTP). EMAIL_USE_TLS (STARTTLS, tipico puerto 587) y EMAIL_USE_SSL
# (SSL implicito, tipico puerto 465) son mutuamente excluyentes -- smtplib
# lanza ValueError si ambos son True. Configurar solo uno de los dos en True
# segun el puerto real del proveedor (ver EMAIL_PORT).
EMAIL_BACKEND    = config('EMAIL_BACKEND',    default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@sintel.co')
EMAIL_HOST       = config('EMAIL_HOST',       default='smtp.gmail.com')
EMAIL_PORT       = config('EMAIL_PORT',       default=587, cast=int)
EMAIL_USE_TLS    = config('EMAIL_USE_TLS',    default=True, cast=bool)
EMAIL_USE_SSL    = config('EMAIL_USE_SSL',    default=False, cast=bool)
EMAIL_HOST_USER  = config('EMAIL_HOST_USER',  default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
# SERVER_EMAIL: remitente de los correos internos de Django (errores 500 a
# ADMINS/MANAGERS, si se configuran). Sin esto, Django usa 'root@localhost'
# por defecto -- misma clase de problema de alineacion SPF/DKIM que tener un
# DEFAULT_FROM_EMAIL ajeno al dominio real.
SERVER_EMAIL     = config('SERVER_EMAIL',     default=DEFAULT_FROM_EMAIL)

# Base URL del frontend, usada para armar enlaces en emails (ej. verificacion de cuenta)
FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:5173')
ANYMAIL = {
    "SENDGRID_API_KEY": config('SENDGRID_API_KEY', default=''),
}

# Meta (WhatsApp + Facebook + Instagram — same Business App)
META_ACCESS_TOKEN = config('META_ACCESS_TOKEN', default='')
# App Secret de Meta -- firma HMAC-SHA256 de los webhooks entrantes de WhatsApp
# (X-Hub-Signature-256). Sin este valor, el webhook rechaza todo evento
# (fail-closed, ver notifications/api/whatsapp_webhook.py).
META_APP_SECRET = config('META_APP_SECRET', default='')
WHATSAPP_PHONE_NUMBER_ID = config('WHATSAPP_PHONE_NUMBER_ID', default='')
FACEBOOK_PAGE_ID = config('FACEBOOK_PAGE_ID', default='')
INSTAGRAM_BUSINESS_ACCOUNT_ID = config('INSTAGRAM_BUSINESS_ACCOUNT_ID', default='')

# Meta Business -- inventario de activos (FASE 1 del plan de integracion Meta
# Business, ver Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md).
# Todos son IDs publicos de activos, NO secretos -- pero siguen la misma regla
# que el resto de credenciales de integracion: viven en .env / secret manager,
# nunca en BD (decision de organization confirmada 2026-07-12). El unico punto
# de lectura sancionado es OrganizationSelector.get_integration_settings().
# Vacio por defecto: MetaGraphClient levanta MetaConfigError con un mensaje
# claro cuando una operacion necesita un id que no esta configurado.
META_GRAPH_API_VERSION = config('META_GRAPH_API_VERSION', default='v20.0')
META_BUSINESS_ID = config('META_BUSINESS_ID', default='')
META_WABA_ID = config('META_WABA_ID', default='')
# ID numerico de la cuenta publicitaria, SIN el prefijo "act_" (el cliente lo
# antepone cuando arma la ruta de Graph API).
META_AD_ACCOUNT_ID = config('META_AD_ACCOUNT_ID', default='')
META_CATALOG_ID = config('META_CATALOG_ID', default='')
META_PIXEL_ID = config('META_PIXEL_ID', default='')
META_DATASET_ID = config('META_DATASET_ID', default='')

# SMS (modem GSM SIM5360 fisico, SIM Movistar Colombia -- ver sms_bridge/bridge.py).
# Django corre en un contenedor Linux y no puede abrir un puerto COM de
# Windows directamente, asi que le habla por HTTP a un puente que SI corre
# en el host y es dueno del puerto serie. host.docker.internal es el nombre
# que Docker Desktop resuelve al host desde dentro del contenedor.
SMS_BRIDGE_URL = config('SMS_BRIDGE_URL', default='http://host.docker.internal:8765')
SMS_BRIDGE_TOKEN = config('SMS_BRIDGE_TOKEN', default='')

# YouTube (OAuth2 — pre-authorized refresh token)
YOUTUBE_CLIENT_ID = config('YOUTUBE_CLIENT_ID', default='')
YOUTUBE_CLIENT_SECRET = config('YOUTUBE_CLIENT_SECRET', default='')
YOUTUBE_REFRESH_TOKEN = config('YOUTUBE_REFRESH_TOKEN', default='')

# TikTok (Content Posting API v2)
TIKTOK_ACCESS_TOKEN = config('TIKTOK_ACCESS_TOKEN', default='')

# X / Twitter (API v2)
X_BEARER_TOKEN = config('X_BEARER_TOKEN', default='')

# Google Business Profile (My Business API)
GOOGLE_BUSINESS_CLIENT_ID = config('GOOGLE_BUSINESS_CLIENT_ID', default='')
GOOGLE_BUSINESS_CLIENT_SECRET = config('GOOGLE_BUSINESS_CLIENT_SECRET', default='')
GOOGLE_BUSINESS_REFRESH_TOKEN = config('GOOGLE_BUSINESS_REFRESH_TOKEN', default='')
GOOGLE_BUSINESS_LOCATION_NAME = config('GOOGLE_BUSINESS_LOCATION_NAME', default='')

# ─── Marketing Intelligence Agent ─────────────────────────────────────────────
MARKETING_AGENT_PROVIDER = config('MARKETING_AGENT_PROVIDER', default='gemini')  # openai | anthropic | gemini

# OpenAI
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
OPENAI_MODEL = config('OPENAI_MODEL', default='gpt-4o')

# Anthropic (Claude)
ANTHROPIC_API_KEY = config('ANTHROPIC_API_KEY', default='')
ANTHROPIC_MODEL = config('ANTHROPIC_MODEL', default='claude-3-5-sonnet-20241022')

# Google Gemini
GEMINI_API_KEY = config('GEMINI_API_KEY', default='')
GEMINI_MODEL = config('GEMINI_MODEL', default='gemini-1.5-pro')

# ─── Wompi Colombia ───────────────────────────────────────────────────────────
WOMPI_PUBLIC_KEY       = config('WOMPI_PUBLIC_KEY',       default='pub_test_placeholder')
WOMPI_PRIVATE_KEY      = config('WOMPI_PRIVATE_KEY',      default='prv_test_placeholder')
WOMPI_INTEGRITY_SECRET = config('WOMPI_INTEGRITY_SECRET', default='')
WOMPI_EVENTS_SECRET    = config('WOMPI_EVENTS_SECRET',    default='')
WOMPI_ENVIRONMENT      = config('WOMPI_ENVIRONMENT',      default='test')
WOMPI_WIDGET_URL       = 'https://checkout.wompi.co/widget.js'

# ─── Nequi Push Notification ──────────────────────────────────────────────────
NEQUI_CLIENT_ID     = config('NEQUI_CLIENT_ID',     default='')
NEQUI_CLIENT_SECRET = config('NEQUI_CLIENT_SECRET', default='')
NEQUI_API_KEY       = config('NEQUI_API_KEY',       default='')
NEQUI_ENVIRONMENT   = config('NEQUI_ENVIRONMENT',   default='')

# ─── SEO / Metaetiquetas ──────────────────────────────────────────────────────
# Override explicito del entorno usado por seo.services.environment para
# filtrar SiteMetaTag.environment ('development'/'testing'/'staging'/
# 'production'). Vacio por defecto: se infiere de DEBUG (solo distingue
# development/production, ya que hoy no existen settings/testing.py ni
# settings/staging.py). Seteando esta env var, un contenedor de testing o
# staging puede declararse sin tocar codigo.
SEO_ACTIVE_ENVIRONMENT = config('SEO_ACTIVE_ENVIRONMENT', default='')
