# Arquitectura Completa - Core del Proyecto (ecommerce)

> **Auditado y actualizado: 2026-07-12.** Este documento estaba desactualizado (reflejaba una
> version anterior del proyecto con ~12 apps y `coreui`/`wompi`). Se corrigio contra el codigo
> real en `ecommerce_sintel/ecommerce/`.

## 📋 Tabla de Contenidos
1. [Descripción General](#descripción-general)
2. [Estructura de Directorios](#estructura-de-directorios)
3. [Arquitectura General del Proyecto](#arquitectura-general-del-proyecto)
4. [Sistema de Configuración (Settings)](#sistema-de-configuración-settings)
5. [Descripción de Cada Archivo](#descripción-de-cada-archivo)
6. [Modelos Base y Serializers](#modelos-base-y-serializers)
7. [Sistema de WebSocket y Notificaciones](#sistema-de-websocket-y-notificaciones)
8. [Celery y Tareas Asincrónicas](#celery-y-tareas-asincrónicas)
9. [Entry Points (WSGI/ASGI)](#entry-points-wsgasgi)
10. [Rutas Principales](#rutas-principales)
11. [Stack Tecnológico](#stack-tecnológico)

---

## Descripción General

El módulo **ecommerce** es el **core del proyecto** - el núcleo que orquesta toda la aplicación e-commerce. No contiene lógica de negocio específica, sino que:

- **Configura Django**: Settings para dev/prod, installed apps, middleware
- **Establece patrones base**: Modelo base (`SintelBaseModel`), serializers base, exception handler global
- **Gestiona comunicación en tiempo real**: WebSocket con Channels + Redis, autenticado por JWT
- **Organiza tareas asincrónicas**: Celery para procesamiento en background
- **Enruta requests**: Mapeo de URLs a apps (API-first architecture) + SPA shell para el frontend Vue
- **Gestiona ciclo de vida**: WSGI (fallback sincrónico), ASGI (HTTP + WebSocket, es lo que corre en producción)

**Característica principal**: **API-First Architecture**
- Todos los endpoints REST están en `/api/v1/*`
- Frontend Vue/Vite consume estos endpoints y se sirve como SPA (`spa_shell.html`) para cualquier ruta no-API
- Separación clara entre backend (Django) y frontend (Vue.js + Vite)

---

## Estructura de Directorios

```
ecommerce_sintel/ecommerce/
├── settings/
│   ├── __init__.py                      # Inicializador (vacío)
│   ├── base.py                          # Configuración base (dev + prod)
│   ├── development.py                   # Overrides para desarrollo
│   └── production.py                    # Overrides para producción
├── .AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md  # Este documento
├── __init__.py                          # Exporta celery_app
├── wsgi.py                              # Entry point WSGI (fallback sincrónico)
├── asgi.py                              # Entry point ASGI (HTTP + WebSocket, JWT auth)
├── urls.py                              # Rutas principales del proyecto + SPA catch-all
├── base_models.py                       # Modelo abstracto base (SintelBaseModel)
├── api_base_serializers.py              # Serializers base para reutilización
├── api_exceptions.py                    # Exception handler global de DRF
├── validators.py                        # ComplexPasswordValidator
├── celery.py                            # Configuración de Celery
├── routing.py                           # Rutas de WebSocket (Channels) — agrega support + operations
├── consumers.py                         # Consumer de WebSocket general (grupo sintel_notifications)
├── ws_notify.py                         # Utilidad para notificaciones WebSocket
├── CLAUDE.md / ANTIGRAVITY.md           # Instrucciones para el editor IA de esta app
```

---

## Arquitectura General del Proyecto

### Diagrama de Capas

```
┌────────────────────────────────────────────────────────┐
│                    Cliente                              │
│        (Vue.js + Vite Frontend — SPA)                   │
│     ecommerce_sintel/frontend/ → build en static/panel  │
└─────────────────┬──────────────────────────────────────┘
                  │
        HTTP + WebSocket
    (JWT Auth, REST JSON)
                  │
┌─────────────────▼──────────────────────────────────────┐
│              Servidor Django (Daphne/ASGI)              │
│  ecommerce_sintel/ecommerce (CORE)                      │
│                                                         │
│  ┌─ Middleware (CORS, Auth, Sessions, HTMX)             │
│  ├─ URLs Router (/api/v1/* + SPA catch-all)             │
│  ├─ Authentication (JWT SimpleJWT)                      │
│  └─ Error Handling & Logging (api_exceptions.py)        │
└─────────────────┬──────────────────────────────────────┘
                  │
        ┌─────────┼──────────┬──────────┐
        │         │          │          │
┌───────▼──┐ ┌────▼────┐ ┌──▼───┐ ┌──▼───┐
│   HTTP   │ │WebSocket│ │ Tasks│ │Admin │
│ (WSGI)   │ │ (ASGI)  │ │(CEL.)│ │      │
└────┬─────┘ └────┬────┘ └──┬───┘ └──┬───┘
     │            │         │        │
     │            │         │        │
     └─┬──────────┴────┬────┴───┬────┘
       │                │       │
┌──────▼─────────┐ ┌────▼──┐ ┌─▼─────┐
│  Applications  │ │ Redis │ │  BD   │
│ accounts, users│ │(cache,│ │PostgreSQL
│ shop, inventory│ │broker,│ │(prod) /
│ cart, orders,  │ │channel│ │SQLite (dev
│ payment, tech_ │ │layer) │ │ sin Docker)
│ services,quotes│ │       │ │       │
│ marketing,rent-│ │       │ │       │
│ ing,notificat.,│ │       │ │       │
│ support,dash-  │ │       │ │       │
│ board,core,op- │ │       │ │       │
│ erations,kyc,  │ │       │ │       │
│ security       │ │       │ │       │
└────────────────┘ └───────┘ └───────┘
```

### Flujo de Request HTTP

```
1. Cliente (navegador) → GET /api/v1/shop/products/
2. Django ASGI recibe request (protocolo "http" del ProtocolTypeRouter)
3. Middleware:
   - CorsMiddleware: Valida CORS
   - SecurityMiddleware + WhiteNoiseMiddleware
   - SessionMiddleware / CsrfViewMiddleware
   - AuthenticationMiddleware: Procesa JWT token
   - HtmxMiddleware
4. URL Router (urls.py) mapea a shop.urls
5. shop.urls mapea a shop.api.views.ProductViewSet
6. ViewSet procesa request:
   - Usa shop.api.serializers para validación/serialización
   - Llama shop.services.selectors para lógica de lectura
   - Accede BD vía ORM
7. Si ocurre una excepción no manejada, pasa por
   ecommerce.api_exceptions.api_exception_handler antes de convertirse en 500
8. Response JSON con status 200
```

### Flujo de WebSocket (Real-time)

```
1. Cliente (navegador) abre conexión WebSocket
   → ws://host/ws/?token=<access_token JWT>

2. ASGI recibe conexión
3. ProtocolTypeRouter:
   - HTTP → django_asgi_app (normal)
   - WebSocket → JWTAuthMiddlewareStack(URLRouter(...)) → consumers.py

4. JWTAuthMiddleware (support/channels_auth.py) lee "token" de la query string,
   valida el AccessToken con SimpleJWT y llena scope['user']
   (imports diferidos dentro de la funcion para evitar problemas de
   inicializacion de apps de Django en el arranque de Daphne)

5. NotificationConsumer.connect():
   - Se une al grupo 'sintel_notifications' (usuarios de gestion/admin)
   - support.routing y operations.routing agregan sus propios consumers
     (chat de soporte, dashboard de operaciones) al mismo websocket_urlpatterns

6. Alguna acción genera evento:
   - user registrado → ws_notify('admin_notifications', 'new_user_registered', {...})
   - producto actualizado → ws_notify(..., 'product_updated', {...})

7. ws_notify() envía mensaje al grupo vía channel layer (Redis)
   → Todos los clientes en ese grupo reciben notificación

8. Cliente recibe JSON con evento → Frontend actualiza UI en tiempo real
```

### Flujo de Tarea Asincrónica (Celery)

```
1. Service layer ejecuta código crítico (transacción)
2. Después de SUCCESS, schedule tarea async (email, notificacion, reconciliacion)
3. Signal o código directo: task.delay()
4. Celery Worker (background), enrutado por CELERY_TASK_ROUTES:
   - notifications.* → cola "notifications"
   - marketing.*     → cola "marketing"
   - accounts.*      → cola "default"
   - el resto        → cola "default" (implicito)
5. En caso de error: autoretry_for + max_retries (patron usado en notifications/tasks.py)
6. Frontend (opcional): Polling o WebSocket para estado
7. Task completada → BD actualizada, WebSocket notifica si aplica
```

---

## Sistema de Configuración (Settings)

### Estructura de Settings

```
ecommerce/settings/
├── __init__.py          # Empty (marks as package)
├── base.py              # Configuración común (dev + prod) — ~360 líneas
├── development.py       # Overrides para desarrollo
└── production.py        # Overrides para producción
```

**Patrón de Herencia**:
```python
# development.py
from .base import *
# Sobrescribe settings específicas para dev

# production.py
from .base import *
# Sobrescribe settings específicas para prod
```

> **Nota operativa (ver `feedback_production_gate` en memoria del agente):** el `.env` de este
> repo tiene `DJANGO_SETTINGS_MODULE=ecommerce.settings.production` incluso para trabajo local.
> No cambiar ese valor ni "elevar" settings sin instrucción explícita del usuario.

---

### settings/base.py - Configuración Base

#### 1. **Rutas y Seguridad**
```python
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')
```

---

#### 2. **Installed Apps**

```python
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
    'accounts', 'users', 'shop', 'inventory', 'cart', 'orders',
    'payment', 'technical_services', 'quotes', 'marketing', 'renting',
    'notifications', 'support', 'dashboard', 'core', 'operations',
    'kyc', 'security',

    'django_vite',
]
```

**18 apps de proyecto** (vs. las ~12 que documentaba la versión anterior de este archivo).
Cambios de nombre relevantes frente a versiones antiguas del código:
- `wompi` → **`payment`** (procesamiento de pagos, incluye Wompi Colombia)
- `coreui` → dividida en **`dashboard`** (panel admin/backoffice) + **`core`** (home pública, config del sitio)
- Apps nuevas desde entonces: `notifications`, `support`, `operations`, `kyc`, `security`

---

#### 3. **Django-Vite**

```python
DJANGO_VITE = {
  "default": {
    "manifest_path": BASE_DIR / "static/panel/js/bundle/.vite/manifest.json",
    "static_url_prefix": "panel/js/bundle",
    "dev_mode": config('VITE_DEV_MODE', default=False, cast=bool),
    "dev_server_host": config('VITE_DEV_SERVER_HOST', default='localhost'),
    "dev_server_port": config('VITE_DEV_SERVER_PORT', default=5173, cast=int),
  }
}
```

- `manifest_path` DEBE coincidir con el `outDir` de `vite.config.js` (`../ecommerce_sintel/static/panel/js/bundle/`).
- `static_url_prefix`: se agregó tras un 404 real en producción (Fase 22 del roadmap de
  Cloudflare Tunnel) — `STATICFILES_DIRS` preserva la ruta completa en `collectstatic`
  (`STATIC_ROOT/panel/js/bundle/...`), pero `vite_asset` sin este prefijo generaba URLs
  relativas a la raíz de `STATIC_URL` (`/static/assets/...`), que no existían.
- `dev_mode`: en `development.py` se fuerza a `True` para HMR.

---

#### 4. **Middleware**

```python
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
```
Sin cambios frente a versiones anteriores.

---

#### 5. **Templates**

Sin cambios: `DjangoTemplates`, `DIRS=[BASE_DIR/'templates']`, `APP_DIRS=True`, context processors estándar de auth/messages.

---

#### 6. **ASGI/WSGI**

```python
WSGI_APPLICATION = 'ecommerce.wsgi.application'
ASGI_APPLICATION = 'ecommerce.asgi.application'
```

---

#### 7. **Channels y Redis**

```python
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [config('REDIS_URL', default='redis://localhost:6379/0')],
        },
    },
}
```

---

#### 8. **Cache** (no documentado en la versión anterior)

```python
CACHE_BACKEND = config('CACHE_BACKEND', default='redis')
if CACHE_BACKEND == 'locmem':
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
else:
    _redis_cache_base = config('REDIS_URL', default='redis://localhost:6379/0').rsplit('/', 1)[0]
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': f'{_redis_cache_base}/1',
        }
    }
```

- Redis por defecto, usando **db=1** (separado de Celery/Channels que usan db=0 vía `REDIS_URL`).
- `CACHE_BACKEND=locmem` (variable de entorno) permite correr sin Redis — útil para aislar
  errores de entorno al depurar sin tener que tocar `DJANGO_SETTINGS_MODULE`.

---

#### 9. **Base de Datos**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```
Base (SQLite) definida en `base.py` solo como fallback; tanto `development.py` como
`production.py` la sobrescriben (ver más abajo).

---

#### 10. **Password Validators** (no documentado en la versión anterior)

```python
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
    {'NAME': 'ecommerce.validators.ComplexPasswordValidator'},
]
```
Política real: mínimo 12 caracteres + mayúscula + minúscula + número + carácter especial
(ver [`validators.py`](#validatorspy---complexpasswordvalidator)).

---

#### 11. **Storage privado de KYC** (no documentado en la versión anterior)

```python
KYC_PRIVATE_STORAGE_ROOT = config(
    'KYC_PRIVATE_STORAGE_ROOT', default=str(BASE_DIR / 'private_media' / 'kyc')
)
```
Fuera de `MEDIA_ROOT` a propósito: ni `static()` en `DEBUG` ni el alias `/media/` de nginx en
producción lo exponen. Único acceso: `kyc.api.views.VerificationDocumentViewSet.download`.

---

#### 12. **JWT Configuration (SimpleJWT)**

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SECRET_KEY'),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```
> Corrección: la versión anterior de este documento decía `ACCESS_TOKEN_LIFETIME=5 min` y
> `SIGNING_KEY=SECRET_KEY`. En realidad el access token dura **60 minutos** y usa una env var
> **separada** (`JWT_SECRET_KEY`), distinta del `SECRET_KEY` de Django.

---

#### 13. **Django REST Framework**

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'ecommerce.api_exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_RATES': {
        'register': '5/hour',
        'login': '10/hour',
        'kyc_upload': '20/hour',
        'kyc_upgrade': '5/hour',
        'order_create': '30/hour',
    },
}
```
- `EXCEPTION_HANDLER` apunta al handler custom (ver [api_exceptions.py](#api_exceptionspy---exception-handler-global-no-documentado-antes)).
- Los `DEFAULT_THROTTLE_RATES` son *scopes* nombrados; cada ViewSet asigna el scope por acción
  vía `ScopedRateThrottle` en su `get_throttles()` (patrón usado en `accounts.api.views.AccountViewSet`).

---

#### 14. **Archivos Estáticos y Media**

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```
Sin cambios de fondo; en producción `STATICFILES_STORAGE` se sobrescribe (ver más abajo).

---

#### 15. **Logging** (no documentado en la versión anterior)

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
```
Logging simple a consola (nivel `INFO`), sin Sentry ni ELK — ver [Mejoras Potenciales](#mejoras-potenciales).

---

#### 16. **Celery**

```python
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
```

**[CRITICAL] Este proyecto NO usa un dict `CELERY_BEAT_SCHEDULE` en settings (verificado 2026-07-07,
sigue vigente):** el contenedor `celery_beat` se levanta con
`celery -A ecommerce beat --scheduler django_celery_beat.schedulers:DatabaseScheduler`
(ver `docker-compose.yml`), que lee su agenda de la BD (modelos `PeriodicTask`/
`CrontabSchedule` de `django_celery_beat`), no de un dict en `settings.py`. Para registrar una
tarea periódica real, sembrar un `PeriodicTask`+`CrontabSchedule` vía data migration (patrón
usado en `payment/migrations/0008_seed_reconcile_periodic_task.py` para
`payment.tasks.reconcile_pending_wompi_transactions`).

---

#### 17. **Integraciones Externas** (no documentado en la versión anterior)

`base.py` centraliza, vía `decouple.config()`, todas las credenciales de integraciones de
marketing, pagos e IA. Todas tienen default vacío/placeholder — nunca hay secretos
hardcodeados:

```python
# Email (SMTP) — usado tanto por notifications como por marketing.channels.email_channel
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@sintel.co')
EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD = ...  # SMTP Gmail
FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:5173')  # enlaces en emails
ANYMAIL = {"SENDGRID_API_KEY": config('SENDGRID_API_KEY', default='')}  # configurado, no activo como EMAIL_BACKEND

# Meta (WhatsApp + Facebook + Instagram — misma Business App)
META_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, FACEBOOK_PAGE_ID, INSTAGRAM_BUSINESS_ACCOUNT_ID

# YouTube (OAuth2), TikTok, X/Twitter, Google Business Profile
YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN, TIKTOK_ACCESS_TOKEN, X_BEARER_TOKEN,
GOOGLE_BUSINESS_CLIENT_ID/SECRET/REFRESH_TOKEN/LOCATION_NAME

# Marketing Intelligence Agent — proveedor seleccionable
MARKETING_AGENT_PROVIDER = config('MARKETING_AGENT_PROVIDER', default='gemini')  # openai|anthropic|gemini
OPENAI_API_KEY/MODEL, ANTHROPIC_API_KEY/MODEL, GEMINI_API_KEY/MODEL

# Wompi Colombia (pasarela de pago principal)
WOMPI_PUBLIC_KEY, WOMPI_PRIVATE_KEY, WOMPI_INTEGRITY_SECRET, WOMPI_EVENTS_SECRET,
WOMPI_ENVIRONMENT (default 'test'), WOMPI_WIDGET_URL (hardcodeado, no es secreto)

# Nequi (push notification de pago)
NEQUI_CLIENT_ID/SECRET, NEQUI_API_KEY, NEQUI_ENVIRONMENT (default 'sandbox')
```

Ver la arquitectura propia de cada app (`marketing/.AGENT/docs/...`, `payment/.AGENT/docs/...`)
para el detalle de cómo se consumen estas variables.

---

### settings/development.py - Configuración Desarrollo

```python
from .base import *

DEBUG = True
CORS_ALLOW_ALL_ORIGINS = True

# DB: PostgreSQL en Docker (si DB_HOST esta definido), SQLite en local sin Docker
if os.getenv('DB_HOST'):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': config('DB_NAME'), ...}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

DJANGO_VITE['default']['dev_mode'] = True
```

> Corrección frente a la versión anterior: `development.py` **ya no fuerza siempre SQLite**.
> Detecta `DB_HOST` (presente cuando se corre vía Docker Compose) y usa PostgreSQL en ese caso;
> solo cae a SQLite si se corre localmente sin Docker.
> `CACHE_BACKEND` (Redis/locmem) se controla desde `base.py`, no se toca aquí.

---

### settings/production.py - Configuración Producción

```python
from .base import *

DEBUG = config('DEBUG', default=False, cast=bool)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'), 'USER': config('DB_USER'), 'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'), 'PORT': config('DB_PORT', default=5432, cast=int),
    }
}

SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Nginx/cloudflared terminan TLS antes de Daphne: sin esto, Django ve toda
# request como HTTP plano y SECURE_SSL_REDIRECT entraria en bucle de redirects.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Dominios de produccion — vacio por defecto, se configura via .env.production
CSRF_TRUSTED_ORIGINS = [o for o in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if o]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

> Corrección frente a la versión anterior: se agregaron `SECURE_PROXY_SSL_HEADER` (necesario
> por el proxy TLS de Cloudflare Tunnel/nginx, ver `project_cloudflare_tunnel_deploy_roadmap`
> en memoria) y `CSRF_TRUSTED_ORIGINS` — ninguno de los dos estaba documentado.

---

## Descripción de Cada Archivo

### **wsgi.py** - Entry Point Sincrónico (fallback)

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings.development')
application = get_wsgi_application()
```

**Responsabilidad**: Exponer `application` WSGI para servidores como Gunicorn. En este proyecto
el servidor real en producción es **Daphne sobre ASGI** (ver abajo); WSGI queda como fallback
sincrónico (p. ej. para `manage.py runserver` en desarrollo, que internamente usa WSGI).

---

### **asgi.py** - Entry Point Asincrónico (ASGI, real en producción)

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from ecommerce.routing import websocket_urlpatterns
from support.channels_auth import JWTAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings.production')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

> Corrección frente a la versión anterior: el middleware de WebSocket **no** es el
> `channels.auth.AuthMiddlewareStack` genérico de Django Channels (basado en sesión/cookie).
> Es `support.channels_auth.JWTAuthMiddlewareStack` — un middleware custom que lee un JWT de la
> **query string** (`?token=...`), valida el `AccessToken` con SimpleJWT y llena `scope['user']`
> antes de delegar al `AuthMiddlewareStack` estándar. Ver la sección
> [Flujo de WebSocket](#flujo-de-websocket-real-time) más arriba.

**Comando para iniciar (producción)**:
```bash
daphne -b 0.0.0.0 -p 8000 --access-log - ecommerce.asgi:application
```

---

### **urls.py** - Rutas Principales

```python
urlpatterns = [
    path('api/v1/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # Ruta aislada exclusiva para superusuarios — NO fusionar con api/v1/auth/
    path('api/v1/admin-auth/login/', AdminLoginView.as_view(), name='admin-login'),

    path('api/v1/auth/',      include('accounts.urls')),
    path('api/v1/auth/',      include('kyc.api.urls')),   # comparte prefijo con accounts
    path('api/v1/users/',     include('users.urls')),
    path('api/v1/dashboard/', include('dashboard.api.urls')),
    path('api/v1/shop/',      include('shop.urls')),
    path('api/v1/cart/',      include('cart.urls')),
    path('api/v1/orders/',    include('orders.urls')),
    path('api/v1/payment/',   include('payment.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/services/',  include('technical_services.urls')),
    path('api/v1/service-operations/', include('technical_services.api.operation_urls')),
    path('api/v1/quotes/',    include('quotes.urls')),
    path('api/v1/marketing/', include('marketing.urls')),
    path('api/v1/renting/',   include('renting.urls')),
    path('api/v1/core/',          include('core.urls')),
    path('api/v1/notifications/', include('notifications.api.urls')),
    path('api/v1/operations/',   include('operations.api.urls')),
    path('api/v1/',              include('security.api.urls')),  # security define su propio sub-prefijo

    # Silenciador de 404 ruidoso de Chrome DevTools
    path('.well-known/appspecific/com.chrome.devtools.json', lambda r: JsonResponse({})),

    # SPA (Vue) — catch-all, DEBE ir al final
    re_path(r'^(?!api/|admin/|static/|media/).*$',
            TemplateView.as_view(template_name='spa_shell.html'), name='spa'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Cambios de fondo frente a la versión anterior de este documento** (que solo listaba 12
`include()` simples y sin catch-all):

1. **`wompi` → `payment`**: el include ya no es `wompi.urls`.
2. **`coreui` → `dashboard.api.urls`**: el dashboard admin es ahora su propia app.
3. **`kyc.api.urls` comparte prefijo `/api/v1/auth/`** con `accounts.urls` — es intencional
   (login/registro y verificación KYC viven bajo el mismo namespace de auth).
4. **`api/v1/admin-auth/login/` es una ruta aislada** para el login de superusuarios del panel
   Django (`AdminLoginView`); regla explícita en el código: no modificar ni fusionar con
   `api/v1/auth/`.
5. **6 includes nuevos** que no existían: `technical_services.api.operation_urls`, `core.urls`,
   `notifications.api.urls`, `operations.api.urls`, `security.api.urls`.
6. **Catch-all SPA real**: a diferencia de la versión anterior (que solo servía `MEDIA_URL` en
   `DEBUG`), ahora hay un `re_path` que sirve `spa_shell.html` para **cualquier** ruta que no
   empiece por `api/`, `admin/`, `static/` o `media/`. Esto es lo que permite que Vue Router
   (modo `createWebHistory`) maneje rutas como `/mi-cuenta/verificacion` o `/panel/usuarios`
   sin un 404 de Django al refrescar la página.

---

### **base_models.py** - Modelo Base Abstracto

```python
import uuid
from django.db import models

class SintelBaseModel(models.Model):
    """
    Modelo base abstracto que inyecta UUID, timestamps de auditoria y soft-delete.
    Usado por todos los modelos de negocio.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False, db_index=True)  # Soft-delete

    class Meta:
        abstract = True
```

> Correcciones frente a la versión anterior:
> - **No existe** un `Meta.indexes` con `models.Index(fields=['uuid'])` /
>   `models.Index(fields=['-created_at'])` como afirmaba el documento anterior. La indexación
>   se logra solo con `db_index=True` por campo — no hay índices compuestos declarados aquí.
> - `is_deleted` fue agregado el 2026-05-14 vía migración (`DEFAULT FALSE` para filas
>   existentes); los selectores que filtran `is_deleted=False` funcionan correctamente desde
>   entonces. Ver auditoría completa en `project_db_audit_duplicate_indexes` (memoria del
>   agente) para el detalle app por app de índices e integridad.

**Uso en otros modelos**: cualquier modelo de negocio hereda `SintelBaseModel` en vez de
`models.Model` directamente (`class Product(SintelBaseModel): ...`).

---

### **api_base_serializers.py** - Serializers Base

```python
from rest_framework import serializers

class BaseWriteSerializer(serializers.ModelSerializer):
    """Base serializer for write operations (Create/Update)."""
    def validate(self, data):
        return data

class BaseModelSerializerV1(serializers.ModelSerializer):
    """Base serializer for read operations."""
    class Meta:
        fields = ('uuid', 'inserted_at', 'updated_at')
        read_only_fields = ('uuid', 'inserted_at', 'updated_at')
```
Sin cambios frente a la versión anterior.

---

### **api_exceptions.py** - Exception Handler Global (no documentado antes)

```python
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status


def api_exception_handler(exc, context):
    if isinstance(exc, ObjectDoesNotExist):
        return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)

    if isinstance(exc, Throttled):
        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.RATE_LIMIT_HIT, request=context.get('request'),
            severity=SecurityEvent.SEVERITY_WARNING, metadata={'wait': exc.wait},
        )

    return drf_exception_handler(exc, context)
```

Registrado en `REST_FRAMEWORK['EXCEPTION_HANDLER']`. Dos responsabilidades:
1. Convierte un `Model.DoesNotExist` no capturado (ej. UUID válido pero soft-deleted, o
   inexistente, pasado a un `viewsets.ViewSet` plano sin `get_object_or_404`) en un **404
   limpio** en vez de un 500 sin manejar.
2. Cuando un request es bloqueado por throttling (`Throttled`), registra un `SecurityEvent`
   (`RATE_LIMIT_HIT`) vía `security.services.commands.SecurityCommands.log_event` — integra el
   sistema de throttling de DRF con el Security Center (ver
   `project_security_center` en memoria del agente).

---

### **validators.py** - `ComplexPasswordValidator` (no documentado antes)

```python
class ComplexPasswordValidator:
    """Exige mayuscula + minuscula + numero + caracter especial."""
    UPPER_RE, LOWER_RE, DIGIT_RE, SPECIAL_RE = ...

    def validate(self, password, user=None):
        # junta errores por cada clase de caracter faltante y los levanta como ValidationError
        ...

    def get_help_text(self):
        return 'Tu contrasena debe contener al menos una mayuscula, una minuscula, un numero y un caracter especial.'
```
Se combina con `MinimumLengthValidator(min_length=12)` en `AUTH_PASSWORD_VALIDATORS` (ver
sección de settings) para exigir 12+ caracteres con las 4 clases de carácter.

---

### **ws_notify.py** - Utilidad de Notificaciones WebSocket

```python
def ws_notify(group, event_type, payload):
    channel_layer = get_channel_layer()
    if channel_layer is None:
        logger.warning(f"[ws_notify] No channel layer available for group {group}")
        return
    try:
        async_to_sync(channel_layer.group_send)(group, {"type": event_type, "payload": payload})
    except Exception as e:
        logger.error(f"[ws_notify] Error sending to group {group}: {str(e)}")
```
Sin cambios frente a la versión anterior. Siempre debe llamarse dentro de
`transaction.on_commit(lambda: ...)` desde el service layer (regla del `CLAUDE.md` de esta app).

> Nota: desde la introducción de la app `notifications`, la mayoría de notificaciones de
> negocio (email/WhatsApp/WS combinados) pasan por
> `notifications.services.dispatch_notification()`, que internamente puede invocar `ws_notify`
> para el canal WebSocket. `ws_notify` sigue existiendo como utilidad de bajo nivel para casos
> puntuales — ver `project_notifications_app` en memoria del agente.

---

### **celery.py** - Configuración de Celery

```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings.production")
app = Celery("ecommerce")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
```
Sin cambios de fondo. Ver la nota **[CRITICAL]** sobre `CELERY_BEAT_SCHEDULE` en la sección de
settings — sigue vigente.

---

### **routing.py** - Rutas de WebSocket

```python
from ecommerce.consumers import NotificationConsumer
from support.routing import support_websocket_patterns
from operations.routing import operations_websocket_patterns

websocket_urlpatterns = [
    path('ws/', NotificationConsumer.as_asgi()),
    path('ws', NotificationConsumer.as_asgi()),
] + support_websocket_patterns + operations_websocket_patterns
```

> Corrección frente a la versión anterior: ya no son solo 2 rutas. `support` (chat de soporte
> en tiempo real) y `operations` (dashboard de operaciones) agregan sus propios patrones de
> WebSocket al mismo router raíz.

---

### **consumers.py** - Consumer de WebSocket General

```python
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Default group for all management users
        await self.channel_layer.group_add("sintel_notifications", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("sintel_notifications", self.channel_name)

    async def receive(self, text_data):
        pass  # Placeholder — este consumer no procesa mensajes entrantes del cliente

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({'message': event['message']}))
```
Sin cambios de fondo. Es el consumer genérico para notificaciones de gestión/admin; el chat de
soporte y el dashboard de operaciones tienen sus **propios** consumers (en `support/` y
`operations/` respectivamente), no pasan por este.

---

## Modelos Base y Serializers

### SintelBaseModel - Herencia en Todos los Modelos

Todos los modelos de negocio de las 18 apps de proyecto heredan `SintelBaseModel` en vez de
`models.Model` directamente, obteniendo `uuid`, `created_at`, `updated_at`, `is_deleted` sin
repetir código.

### BaseWriteSerializer - Reutilización de Validación

```python
from ecommerce.api_base_serializers import BaseWriteSerializer

class ProductCreateSerializer(BaseWriteSerializer):
    class Meta:
        model = Product
        fields = ('name', 'price', 'description')
```

---

## Sistema de WebSocket y Notificaciones

### Arquitectura Completa

```
Cliente → ws://host/ws/?token=<JWT>
       → ASGI (Daphne) → ProtocolTypeRouter["websocket"]
       → JWTAuthMiddlewareStack (support.channels_auth)
           - lee "token" de la query string
           - valida AccessToken (SimpleJWT), llena scope['user']
           - delega a channels.auth.AuthMiddlewareStack
       → URLRouter(websocket_urlpatterns)
           - NotificationConsumer          (grupo "sintel_notifications")
           - support_websocket_patterns    (chat de soporte)
           - operations_websocket_patterns (dashboard de operaciones)
       → group_add(...)

Servidor (desde el service layer, dentro de transaction.on_commit):
    ws_notify(group, event_type, payload)
        → channel_layer.group_send(group, {...})   [Redis channel layer]
        → todos los clientes conectados a ese grupo reciben el evento
```

### Grupos WebSocket Comunes

| Grupo | Usuarios | Función |
|-------|----------|---------|
| `sintel_notifications` | Gestión/admin (default de `NotificationConsumer`) | Notificaciones generales |
| `admin_notifications` | Admins | Notificaciones de usuarios, órdenes |
| `order_notifications_{user_id}` | Usuario específico | Cambios en sus órdenes |
| (grupos de `support`/`operations`) | Ver arquitectura propia de cada app | Chat de soporte, dashboard de operaciones |

---

## Celery y Tareas Asincrónicas

### Patrón real de tarea (ver `notifications/tasks.py`)

```python
@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3, default_retry_delay=60)
def send_email_task(self, ...):
    from django.core.mail import send_mail
    try:
        send_mail(...)
    except Exception as exc:
        raise self.retry(exc=exc)
```

- `autoretry_for` + `max_retries` + `default_retry_delay` es el patrón estándar en las tareas
  de `notifications.tasks` (con delays distintos por tipo de tarea: 10s, 60s, 120s).
- Importante: `send_mail()` se da por exitoso en cuanto el servidor SMTP **acepta** el mensaje
  para reenvío — no espera la entrega final. Un rebote (bounce) ocurre del lado del servidor de
  destino (p. ej. Gmail reintentando ~72h) y **no** dispara un retry de Celery.

### Enrutamiento a colas

Ver `CELERY_TASK_ROUTES` en settings — 3 colas explícitas (`notifications`, `marketing`,
`default` para `accounts.*`), el resto de tareas cae en `default` implícitamente.

**Iniciar Celery Worker**:
```bash
celery -A ecommerce worker -l info
celery -A ecommerce beat --scheduler django_celery_beat.schedulers:DatabaseScheduler -l info
```

---

## Entry Points (WSGI/ASGI)

### Comparación

| Aspecto | WSGI | ASGI |
|--------|------|------|
| Uso en este proyecto | Fallback / `manage.py runserver` | **Real en producción** (Daphne) |
| Protocolo | HTTP 1.1 | HTTP 1.1 + WebSocket |
| Servidor | Gunicorn (no usado activamente) | Daphne |
| WebSocket | No nativo | Sí (Channels + JWT custom middleware) |

`daphne` está primero en `INSTALLED_APPS` (requisito de Channels), confirmando que ASGI es el
modo de despliegue principal, no un añadido opcional.

---

## Rutas Principales

### Árbol de Rutas (real, ver `urls.py`)

```
/
├── api/
│   ├── v1/
│   │   ├── health/                         [GET]
│   │   ├── admin-auth/login/               [POST]  (aislada, solo superusuarios)
│   │   ├── auth/          → accounts.urls + kyc.api.urls (mismo prefijo)
│   │   ├── users/         → users.urls
│   │   ├── dashboard/     → dashboard.api.urls
│   │   ├── shop/          → shop.urls
│   │   ├── cart/          → cart.urls
│   │   ├── orders/        → orders.urls
│   │   ├── payment/       → payment.urls
│   │   ├── inventory/     → inventory.urls
│   │   ├── services/      → technical_services.urls
│   │   ├── service-operations/ → technical_services.api.operation_urls
│   │   ├── quotes/        → quotes.urls
│   │   ├── marketing/     → marketing.urls
│   │   ├── renting/       → renting.urls
│   │   ├── core/          → core.urls
│   │   ├── notifications/ → notifications.api.urls
│   │   ├── operations/    → operations.api.urls
│   │   └── (raíz)         → security.api.urls
│   ├── schema/                             [GET]  (OpenAPI schema)
│   └── docs/                               [GET]  (Swagger UI)
├── admin/                                  [GET, POST] (Django Admin)
├── ws/  y  ws                              [WebSocket]
├── .well-known/appspecific/com.chrome.devtools.json   [GET]  (silenciador de 404)
├── media/                                  (solo si DEBUG=True)
└── <cualquier otra ruta>                   → spa_shell.html (Vue Router SPA)
```

> El árbol de la versión anterior de este documento (`wompi/`, `dashboard/overview` inventado,
> sin catch-all SPA) no reflejaba el `urls.py` real; se reemplazó por la lista literal de
> `include()`s actuales.

---

## Stack Tecnológico

### Backend
- **Django 5.2.13** (ver `CLAUDE.md` raíz del proyecto — no 4.2 como decía la versión anterior)
- **Django REST Framework** + `drf-spectacular` (Swagger/OpenAPI)
- **Django SimpleJWT** (access 60 min / refresh 7 días, rotación + blacklist)
- **django-channels** + **channels_redis**: WebSocket con auth JWT custom
- **Celery** + **django_celery_beat** (`DatabaseScheduler`, no dict en settings)
- **PostgreSQL** (producción y Docker dev) / **SQLite** (dev local sin Docker)
- **Redis**: cache (db 1), broker/result-backend de Celery y channel layer (db 0)
- **Wompi Colombia** + **Nequi**: pasarelas de pago

### Frontend
- **Vue.js 3** + **Vite** (SPA servida vía `django_vite`, catch-all en `urls.py`)
- **Pinia**, **Axios**, Bootstrap 5 (vía `crispy_forms`/`crispy_bootstrap5` para templates
  server-side que aún existan)

### DevOps
- **Docker / Docker Compose**: orquestación local (Postgres, Redis, Django, Celery worker+beat,
  frontend)
- **Daphne**: servidor ASGI real de producción
- **Cloudflare Tunnel**: exposición pública (ver `project_cloudflare_tunnel_deploy_roadmap` en
  memoria del agente — despliegue completo y verificado end-to-end)
- **WhiteNoise**: archivos estáticos comprimidos en producción

### Testing
- `python manage.py test` (Django `TestCase`), no pytest — confirmado en
  `project_wompi_payment_app_sync` (memoria del agente)

---

## Mejoras Potenciales

Actualizado — algunas de las mejoras que listaba la versión anterior **ya están parcialmente
resueltas**:

1. ~~Rate Limiting~~ → **Ya implementado**: `DEFAULT_THROTTLE_RATES` + `ScopedRateThrottle` por
   acción, con logging a `SecurityEvent` en `api_exceptions.py`.
2. **Logging centralizado**: sigue siendo solo consola (`LOGGING` en settings) — no hay Sentry
   ni stack ELK. Sigue siendo una mejora pendiente real.
3. **Caching avanzado**: existe el switch Redis/locmem, pero no hay cache a nivel de
   serializers/vistas más allá de lo puntual (p. ej. `core.home-feed` con cache de 5 min, ver
   `project_home_page` en memoria).
4. **2FA**: no implementado a nivel de settings/auth (KYC es verificación de identidad, no
   2FA de login).
5. **CI/CD**: no hay GitHub Actions en el repo actualmente.
6. **Monitoring** (Prometheus/Grafana): pendiente.

---

## Conclusión

El módulo **ecommerce** (core) sigue siendo la base del proyecto, pero ha crecido
significativamente: de ~12 a **18 apps de proyecto**, con renombres importantes (`wompi`→
`payment`, `coreui`→`dashboard`+`core`) y piezas nuevas no triviales — auth de WebSocket por
JWT (`support.channels_auth`), exception handler global integrado con el Security Center,
validador de contraseña propio, SPA catch-all real, y un bloque grande de configuración de
integraciones externas (marketing, IA, pagos) que antes no existía o no estaba documentado.

Todos los módulos de negocio siguen heredando `SintelBaseModel` y usando `ws_notify()` /
`dispatch_notification()` para tiempo real, manteniendo el patrón original de este core.
