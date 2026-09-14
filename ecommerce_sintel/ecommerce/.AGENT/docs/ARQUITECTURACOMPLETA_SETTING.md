# Arquitectura Completa - Core del Proyecto (ecommerce)

> **Auditado y actualizado: 2026-08-08.** Segunda pasada contra el codigo real en
> `ecommerce_sintel/ecommerce/` (la primera fue 2026-07-12). Entre ambas fechas el proyecto
> paso de 18 a **21 apps de proyecto** (`organization`, `seo`, `shared`), se agrego el bloque
> completo de **AI Core** (`internal_ai_urls.py`, `internal_ai_utils.py`, settings
> `AI_ENGINE_URL`/`AI_SUPPORT_CHAT_ENABLED`/etc.), `health_check` paso de un stub fijo a un
> chequeo real de DB/Redis, y se cerraron varios hallazgos de auditoria (JWT de 60 a 15 min,
> `CORS_ALLOW_ALL_ORIGINS=False` explicito, fail-safe de `DEBUG` en `production.py`, limites de
> tiempo/ack en Celery, capacity explicita en `CHANNEL_LAYERS`). Detalle de cada cambio en las
> secciones correspondientes abajo.

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
├── internal_ai_urls.py                  # Rutas /api/v1/internal/ai/* — solo AI Engine (no expuestas por nginx)
├── internal_ai_utils.py                 # log_ai_action() — auditoria compartida de escrituras del AI Engine
├── base_models.py                       # Modelo abstracto base (SintelBaseModel)
├── api_base_serializers.py              # Serializers base para reutilización
├── api_exceptions.py                    # Exception handler global de DRF
├── validators.py                        # ComplexPasswordValidator
├── celery.py                            # Configuración de Celery
├── routing.py                           # Rutas de WebSocket (Channels) — agrega support + operations
├── consumers.py                         # Consumer de WebSocket general (grupo sintel_notifications)
├── ws_notify.py                         # Utilidad para notificaciones WebSocket
├── tests.py                             # Test de regresion C-01: production.py debe fallar al importar si DEBUG=True
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
┌──────▼─────────┐ ┌────▼────┐ ┌──▼────┐
│  Applications  │ │  Redis  │ │  BD   │
│ accounts, users│ │ (cache, │ │Postgre│
│ shop, inventory│ │ broker, │ │SQL    │
│ cart, orders,  │ │ channel │ │(prod) │
│ payment, tech_ │ │ layer)  │ │/SQLite│
│ services,quotes│ │         │ │(dev   │
│ marketing,rent-│ │         │ │sin    │
│ ing,notificat.,│ │         │ │Docker)│
│ support,dash-  │ │         │ │       │
│ board,core,op- │ │         │ │       │
│ erations,kyc,  │ │         │ │       │
│ security,org-  │ │         │ │       │
│ anization,seo, │ │         │ │       │
│ shared         │ │         │ │       │
└────────────────┘ └─────────┘ └───────┘

┌───────────────────────────────────────────┐
│ AI Engine (sintel_ai) — NUNCA expuesto a   │
│ Internet. Django lo alcanza via            │
│ AI_ENGINE_URL; el AI Engine llama de vuelta│
│ solo a /api/v1/internal/ai-context/ y      │
│ /api/v1/internal/ai/* (nginx no proxea     │
│ /internal/ hacia afuera en ningun sentido) │
└───────────────────────────────────────────┘
```
(21 apps de proyecto — ver la sección [Installed Apps](#2-installed-apps) para el detalle
completo y los 3 agregados después de la auditoría 2026-07-12.)

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
4. Celery Worker (background), enrutado por CELERY_TASK_ROUTES + CELERY_TASK_DEFAULT_QUEUE:
   - notifications.* → cola "notifications"
   - marketing.*     → cola "marketing"
   - accounts.*      → cola "default"
   - el resto        → cola "default" (via CELERY_TASK_DEFAULT_QUEUE, ver [CRITICAL] abajo)
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
    'kyc', 'security', 'organization', 'seo', 'shared',

    'django_vite',
]
```

**21 apps de proyecto** (18 en la auditoría anterior de 2026-07-12, +3 desde entonces).
Cambios de nombre relevantes frente a versiones antiguas del código:
- `wompi` → **`payment`** (procesamiento de pagos, incluye Wompi Colombia)
- `coreui` → dividida en **`dashboard`** (panel admin/backoffice) + **`core`** (home pública, config del sitio)
- Apps agregadas hasta 2026-07-12: `notifications`, `support`, `operations`, `kyc`, `security`
- Apps agregadas después de esa fecha:
  - **`organization`** (en construcción, ver tabla de routing en `CLAUDE.md` raíz)
  - **`seo`** (2026-07-31) — gestiona `<head>` meta tags y archivos de verificación de dominio
    desde el panel admin (ver `seo_views.serve_verification_file` en [urls.py](#urlspy---rutas-principales))
  - **`shared`** (2026-07-29, "UPDP Phase 1") — DTOs/Presenters/Serializers centralizados para
    unificar las páginas de detalle de Renting, Shop y Technical Services detrás de un solo
    endpoint (`GET /api/v1/unified/detail/<uuid>/?module=...`); ver
    `shared/.AGENT/docs/ARQUITECTURA_COMPLETA_SHARED.md`

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
            "capacity": 1000,
            "expiry": 60,
        },
    },
}
```

**`capacity`/`expiry` explícitos (agregado 2026-08-03, `AUDITORIA/18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md`
B3):** antes no se declaraban y `channels_redis` corría con sus defaults (`capacity=100`,
`expiry=60`) sin que nadie los hubiera evaluado a propósito. Al superar `capacity`, el mensaje
simplemente **no se encola** (solo un log `INFO` de la librería, sin excepción ni señal a
nadie). El grupo de mayor riesgo real es `support_admins`: cada agente conectado + cada
broadcast de chat consume cupo de la misma cola. `capacity=1000` da margen ante una ráfaga
(varios admins conectados durante un pico de mensajes) sin cambiar el comportamiento observable
hoy (muy por debajo del límite actual).

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
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('JWT_SECRET_KEY'),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```
> Historial: la primera versión de este documento decía `ACCESS_TOKEN_LIFETIME=5 min` y
> `SIGNING_KEY=SECRET_KEY` — ambos eran incorrectos entonces (usa `JWT_SECRET_KEY`, una env var
> separada del `SECRET_KEY` de Django). La auditoría de 2026-07-12 corrigió el valor a 60
> minutos, que sí era correcto en ese momento.
>
> **Cambio real posterior (QW-17, quick win de la auditoría 2026-07-16):** `ACCESS_TOKEN_LIFETIME`
> bajó de 60 a **15 minutos** — 60 min era una ventana demasiado larga para un access token
> robado. Es transparente para el usuario porque el frontend ya hace refresh silencioso
> automático en un 401 (interceptor de `useApi.js`).

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
        'admin_login': '5/hour',
        'kyc_upload': '20/hour',
        'kyc_upgrade': '5/hour',
        'order_create': '30/hour',
        'password_reset_request': '5/hour',
        'password_reset_verify': '20/hour',
        'admin_password_reset_request': '5/hour',
        'admin_password_reset_verify': '20/hour',
        'register_verify': '20/hour',
        'register_resend': '5/hour',
        'payment_initialize': '30/hour',
        'payment_card_create': '10/hour',
        'payment_nequi_initialize': '10/hour',
        'payment_reconciliation': '60/hour',
        'quote_from_template': '30/hour',
        'quote_download_pdf': '60/hour',
        'cart_mutate': '120/hour',
        'cart_checkout': '20/hour',
        'ai_support_ticket': '30/hour',
        'communication_event': '60/hour',
    },
}
```
- `EXCEPTION_HANDLER` apunta al handler custom (ver [api_exceptions.py](#api_exceptionspy---exception-handler-global-no-documentado-antes)).
- Los `DEFAULT_THROTTLE_RATES` son *scopes* nombrados; cada ViewSet asigna el scope por acción
  vía `ScopedRateThrottle` en su `get_throttles()` (patrón usado en `accounts.api.views.AccountViewSet`).

**Ampliación real frente a los 5 scopes de la auditoría 2026-07-12 (todos resultado de la
"auditoría enterprise" que cerró hallazgos de endpoints sin throttle propio):**
- `admin_login`, `admin_password_reset_request`, `admin_password_reset_verify`,
  `password_reset_request`, `password_reset_verify`, `register_verify`, `register_resend` —
  cobertura completa del flujo de auth/reset de contraseña, admin incluido.
- `payment_initialize`, `payment_card_create`, `payment_nequi_initialize`,
  `payment_reconciliation` (F-03) — la premisa original de que estos endpoints eran "solo
  lectura" era incorrecta: internamente disparan `_sync_wompi_status()`, que puede mutar el
  estado de la `Transaction` (corregido 2026-08-04, hallazgo C1 de
  `AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md`). El webhook de Wompi en sí queda **sin** scope
  a propósito (público, verificado por firma HMAC en vez de rate limit).
- `quote_from_template`, `quote_download_pdf` (Q-06), `cart_mutate`, `cart_checkout` (S-04) —
  mismo patrón, endpoints de negocio sin límite previo.
- `ai_support_ticket` (D-03) — `AiOpenSupportTicketView` invoca un LLM con costo real por
  mensaje; necesitaba su propio límite, no el genérico.
- `communication_event` (2026-07-31) — endpoint público (`AllowAny`, incluye visitantes
  anónimos) del Centro de Comunicación que solo escribe telemetría; límite generoso para uso
  legítimo con tope real contra abuso.

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
    'formatters': {'verbose': {'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'}},
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
```
Logging simple a consola (nivel `INFO`), sin Sentry ni ELK — ver [Mejoras Potenciales](#mejoras-potenciales).

> **Cambio real (Fase 15, `AUDITORIA/29_AUDITORIA_OBSERVABILIDAD.md`, 2026-08-03):** el
> formatter usaba `{module}`, que solo da el nombre de archivo (ej. `tasks`) — 9 apps distintas
> tienen su propio `tasks.py` (`support`, `notifications`, `marketing`, `orders`, `payment`,
> `quotes`, `renting`, `accounts`, `operations`), todas indistinguibles entre sí en logs crudos
> de producción. Se cambió a `{name}` (el logger completo vía `logging.getLogger(__name__)`,
> ej. `support.tasks`/`notifications.tasks`), patrón ya usado en todo el proyecto — sin cambio
> de código necesario más allá del formatter.

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
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240
```

**[CRITICAL] `CELERY_TASK_DEFAULT_QUEUE` (agregado 2026-07-27, bug real cerrado):**
sin esta linea, cualquier tarea de una app SIN entrada en `CELERY_TASK_ROUTES` cae en la
cola nativa de Celery llamada literalmente `celery` -- **no** `default` como este mismo
documento afirmaba antes de este fix (el supuesto "el resto cae en default implicito" era
falso; Celery nunca hizo eso por si solo). `docker-compose.prod.yml` levanta `celery_worker`
con `-Q default,marketing,notifications` -- la cola `celery` NUNCA tuvo un worker
escuchandola. Con el tiempo se agregaron tareas en `payment`, `renting`, `orders` y `support`
sin entrada propia en `CELERY_TASK_ROUTES`, y todas caian en esa cola fantasma sin que nada
las procesara -- incluida `payment.tasks.reconcile_pending_wompi_transactions`, el fallback
que reconcilia pagos Wompi cuyo webhook se perdio (ver
`docs/.AGENT/AUDITORIA_FLUJO_VENTA_PAGO_CONFIRMACION.md`, verificacion 2026-07-27).
**Regla para el futuro:** toda app nueva con tareas Celery queda cubierta automaticamente por
`CELERY_TASK_DEFAULT_QUEUE = 'default'` (no requiere tocar nada) -- pero si se agrega una
entrada nueva a `CELERY_TASK_ROUTES` con una cola propia (como `notifications`/`marketing`),
esa cola nueva debe agregarse tambien al flag `-Q` de `celery_worker` en
`docker-compose.prod.yml` (y en `docker-compose.yml` de desarrollo), o esas tareas quedaran
sin worker igual que este bug.

**`CELERY_TASK_ACKS_LATE` / `CELERY_TASK_REJECT_ON_WORKER_LOST` / `CELERY_TASK_TIME_LIMIT` /
`CELERY_TASK_SOFT_TIME_LIMIT` (C-03, auditoría enterprise):** sin estos defaults, un worker que
muere a mitad de tarea (OOM, restart de contenedor) pierde la tarea sin dejar rastro (el ack
ocurría al *recibir*, no al *terminar*), y una tarea colgada (HTTP a Wompi/WhatsApp/LLM sin
límite) bloqueaba ese slot de worker para siempre. Seguro habilitarlo porque las tareas de este
proyecto ya son idempotentes por diseño (`unique_together` en `CampaignLog`, `idempotency_key`
en `Payment`/`Orders`).

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
# EMAIL_USE_TLS (STARTTLS, puerto tipico 587) y EMAIL_USE_SSL (SSL implicito, puerto
# tipico 465) son mutuamente excluyentes -- smtplib lanza ValueError si ambos son True.
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@sintel.co')
EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_USE_SSL, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD = ...  # SMTP Gmail
# SERVER_EMAIL: remitente de los correos internos de Django (errores 500 a ADMINS/MANAGERS,
# si se configuran); sin esto Django usa 'root@localhost' -- default a DEFAULT_FROM_EMAIL.
SERVER_EMAIL = config('SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
FRONTEND_BASE_URL = config('FRONTEND_BASE_URL', default='http://localhost:5173')  # enlaces en emails
ANYMAIL = {"SENDGRID_API_KEY": config('SENDGRID_API_KEY', default='')}  # configurado, no activo como EMAIL_BACKEND

# Meta (WhatsApp + Facebook + Instagram — misma Business App)
META_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, FACEBOOK_PAGE_ID, INSTAGRAM_BUSINESS_ACCOUNT_ID
# META_APP_SECRET: firma HMAC-SHA256 de los webhooks entrantes de WhatsApp
# (X-Hub-Signature-256). Sin valor, el webhook rechaza todo evento (fail-closed,
# ver notifications/api/whatsapp_webhook.py).
META_APP_SECRET = config('META_APP_SECRET', default='')
# [2026-08-31] FASE 1 integracion Meta Business — inventario de activos. IDs
# publicos (no secretos), pero misma regla: aqui, nunca en BD. Vacio => el
# MetaGraphClient (marketing/integrations/meta/) lanza MetaConfigError con el
# nombre del setting que falta. Unica lectura via
# OrganizationSelector.get_integration_settings(). Ver
# Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md.
META_GRAPH_API_VERSION (default 'v20.0'), META_BUSINESS_ID, META_WABA_ID,
META_AD_ACCOUNT_ID (numero sin 'act_'), META_CATALOG_ID, META_PIXEL_ID, META_DATASET_ID

# SMS (modem GSM SIM5360 fisico, SIM Movistar Colombia -- ver sms_bridge/bridge.py). Django
# corre en un contenedor Linux y no puede abrir un puerto COM de Windows directamente, asi
# que le habla por HTTP a un puente que SI corre en el host y es dueno del puerto serie.
SMS_BRIDGE_URL = config('SMS_BRIDGE_URL', default='http://host.docker.internal:8765')
SMS_BRIDGE_TOKEN = config('SMS_BRIDGE_TOKEN', default='')

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

# SEO / Metaetiquetas (app 'seo', 2026-07-31) — override explicito del entorno usado por
# seo.services.environment para filtrar SiteMetaTag.environment. Vacio por defecto: se
# infiere de DEBUG (solo distingue development/production, ya que no existen
# settings/testing.py ni settings/staging.py). Permite declarar un contenedor de
# testing/staging sin tocar codigo.
SEO_ACTIVE_ENVIRONMENT = config('SEO_ACTIVE_ENVIRONMENT', default='')
```

Ver la arquitectura propia de cada app (`marketing/.AGENT/docs/...`, `payment/.AGENT/docs/...`,
`seo/.AGENT/docs/...`) para el detalle de cómo se consumen estas variables.

**Nuevo frente a la auditoría 2026-07-12:** `SERVER_EMAIL`, `META_APP_SECRET`, `SMS_BRIDGE_URL`/
`SMS_BRIDGE_TOKEN`, `EMAIL_USE_SSL` y `SEO_ACTIVE_ENVIRONMENT` no existían o no estaban
documentados en la versión anterior.

---

#### 18. **CORS** (no documentado en la versión anterior)

```python
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='').split(',')
CORS_ALLOW_ALL_ORIGINS = False
```

**`CORS_ALLOW_ALL_ORIGINS = False` explícito (SEC-M2, auditoría, ver `AUDITORIA/06_SEGURIDAD.md`):**
`development.py` fija `CORS_ALLOW_ALL_ORIGINS = True` para desarrollo. Sin este `False`
explícito en `base.py`, un `DJANGO_SETTINGS_MODULE` mal configurado en producción (que solo
cargue `base.py` sin `production.py`) heredaría el default de `django-cors-headers`, que
también es `False` — pero dejar la intención explícita evita depender de ese default implícito
si la librería cambia su comportamiento en el futuro.

---

#### 19. **AI Core** (Fase 7 — multicanal; no existía en la versión anterior)

```python
# sintel_ai NUNCA se expone a Internet: todos los canales (widget web, WhatsApp) llegan
# al Action Graph a traves de Django via esta URL interna.
AI_ENGINE_URL = config('AI_ENGINE_URL', default='http://sintel_ai:8100')
# Modo AI del chat de soporte (el widget web reusa support/consumers.py).
AI_SUPPORT_CHAT_ENABLED = config('AI_SUPPORT_CHAT_ENABLED', default=False, cast=bool)
# Usuario bot que firma los mensajes del asistente en ChatMessage (FK sender NOT NULL).
# Inactivo y sin password utilizable -- jamas puede autenticarse.
AI_BOT_EMAIL = config('AI_BOT_EMAIL', default='asistente.ia@sintel.internal')
# Verify token del webhook entrante de WhatsApp (Meta Cloud API).
WHATSAPP_WEBHOOK_VERIFY_TOKEN = config('WHATSAPP_WEBHOOK_VERIFY_TOKEN', default='')
# Las trazas [WS]/[CHAT] de support/consumers.py, support/channels_auth.py y
# support/services/ai_bridge.py corren siempre a nivel INFO (conexion, sala, latencia,
# tools, status) sin contenido de mensajes. Con este flag en True, ademas incluyen el
# texto (truncado) del mensaje del cliente y de la respuesta del AI Engine -- para
# diagnosticar un recorrido completo puntual sin dejar contenido de conversaciones en
# logs de produccion por defecto.
SUPPORT_DEBUG_MODE = config('SUPPORT_DEBUG_MODE', default=False, cast=bool)
# Event Bus (Componente 8): slugs de NotificationTemplate que ademas de sus canales
# normales generan un mensaje proactivo del bot en la sala del cliente.
AI_PROACTIVE_SLUGS = [s.strip() for s in config('AI_PROACTIVE_SLUGS', default='').split(',') if s.strip()]
```

Bloque completamente nuevo desde la auditoría 2026-07-12. Consume estos settings el módulo
`ai_engine/` (fuera de `ecommerce_sintel/`, ver `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`)
más `support/channels_auth.py` y `support/services/ai_bridge.py` dentro de `ecommerce_sintel/`.
También se agregaron `ecommerce/internal_ai_urls.py` e `ecommerce/internal_ai_utils.py` como
la superficie HTTP interna que el AI Engine consume — ver
[urls.py](#urlspy---rutas-principales) más abajo.

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
from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = config('DEBUG', default=False, cast=bool)

# Fail-safe: settings.production NUNCA debe correr con DEBUG=True (expondria stack
# traces, SQL y configuracion a cualquier visitante ante un 500). Si se necesita
# DEBUG, usar ecommerce.settings.development.
if DEBUG:
    raise ImproperlyConfigured(
        'DEBUG=True es invalido con ecommerce.settings.production. '
        'Para desarrollo usa DJANGO_SETTINGS_MODULE=ecommerce.settings.development.'
    )

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

# Segunda capa de F-01: en produccion el secreto de eventos de Wompi es obligatorio.
# Sin el, _verify_wompi_event_signature() ya rechaza (fail-closed), pero es mejor no
# arrancar en absoluto que operar sin poder verificar webhooks de pago.
if not config('WOMPI_EVENTS_SECRET', default=''):
    raise ImproperlyConfigured(
        'WOMPI_EVENTS_SECRET es obligatorio en produccion (verificacion de '
        'firma de los webhooks de pago Wompi).'
    )

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

> Corrección frente a la auditoría 2026-07-12: se agregaron `SECURE_PROXY_SSL_HEADER` (necesario
> por el proxy TLS de Cloudflare Tunnel/nginx, ver `project_cloudflare_tunnel_deploy_roadmap`
> en memoria) y `CSRF_TRUSTED_ORIGINS` — ninguno de los dos estaba documentado entonces.
>
> **Nuevo desde entonces — dos fail-safes que abortan el arranque del proceso (no solo loguean):**
> - **C-01** (auditoría enterprise, test de regresión real en `ecommerce/tests.py`): si
>   `DEBUG=True` se cuela en `ecommerce.settings.production` (ej. variable de entorno mal
>   copiada), el módulo lanza `ImproperlyConfigured` al **importarse** — el proceso ni siquiera
>   arranca, en vez de servir stack traces completos a cualquier visitante ante un 500.
> - **F-01, segunda capa** (`AUDITORIA_INTEGRAL_PRODUCCION_2026-08-04.md`): si
>   `WOMPI_EVENTS_SECRET` está vacío en producción, también aborta el arranque. La primera capa
>   (`_verify_wompi_event_signature()` rechazando en runtime) ya existía; esta segunda capa evita
>   operar sin poder verificar webhooks de pago en absoluto, en vez de descubrirlo en el primer
>   webhook recibido.

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
def health_check(request):
    """Fase 15 (2026-08-03): reusa SecuritySelector.get_health_snapshot() para
    chequear DB + Redis de verdad, no solo responder {"status": "ok"} fijo."""
    from security.services.selectors import SecuritySelector
    snapshot = SecuritySelector.get_health_snapshot()
    healthy = snapshot['db'] and snapshot['redis']
    return JsonResponse(
        {'status': 'ok' if healthy else 'degraded', **snapshot},
        status=200 if healthy else 503,
    )

urlpatterns = [
    path('api/v1/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[IsAdminUser]), name='swagger-ui'),

    # Ruta aislada exclusiva para superusuarios — NO fusionar con api/v1/auth/
    path('api/v1/admin-auth/login/', AdminLoginView.as_view(), name='admin-login'),
    path('api/v1/admin-auth/forgot-password-request/', AdminForgotPasswordRequestView.as_view(), name='admin-forgot-password-request'),
    path('api/v1/admin-auth/forgot-password-verify/', AdminForgotPasswordVerifyView.as_view(), name='admin-forgot-password-verify'),
    path('api/v1/admin-auth/reset-password/', AdminResetPasswordView.as_view(), name='admin-reset-password'),

    # Internal — consumido solo por el AI Engine via red Docker
    path('api/v1/internal/ai-context/', AiContextView.as_view(), name='ai-context'),
    path('api/v1/internal/ai/', include('ecommerce.internal_ai_urls')),

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
    path('api/v1/services/',  include('technical_services.api.availability_urls')),  # 2do include, mismo prefijo
    path('api/v1/quotes/',    include('quotes.urls')),
    path('api/v1/marketing/', include('marketing.urls')),
    path('api/v1/renting/',   include('renting.urls')),
    path('api/v1/support/',   include('support.api.urls')),
    path('api/v1/core/',          include('core.urls')),
    path('api/v1/notifications/', include('notifications.api.urls')),
    path('api/v1/operations/',   include('operations.api.urls')),
    path('api/v1/organization/', include('organization.api.urls')),
    path('api/v1/',              include('security.api.urls')),  # security define su propio sub-prefijo
    path('api/v1/',              include('shared.api.urls')),    # idem, shared define su propio sub-prefijo

    # Silenciador de 404 ruidoso de Chrome DevTools
    path('.well-known/appspecific/com.chrome.devtools.json', lambda r: JsonResponse({})),

    # SEO — archivos de verificacion en la raiz del dominio, ANTES del catch-all SPA
    path('<str:filename>.html', seo_views.serve_verification_file, name='seo-verification-file'),

    # SPA (Vue) — catch-all, DEBE ir al final
    re_path(r'^(?!api/|admin/|static/|media/).*$',
            TemplateView.as_view(template_name='spa_shell.html'), name='spa'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Cambios de fondo frente a la primera versión de este documento** (que solo listaba 12
`include()` simples y sin catch-all):

1. **`wompi` → `payment`**: el include ya no es `wompi.urls`.
2. **`coreui` → `dashboard.api.urls`**: el dashboard admin es ahora su propia app.
3. **`kyc.api.urls` comparte prefijo `/api/v1/auth/`** con `accounts.urls` — es intencional
   (login/registro y verificación KYC viven bajo el mismo namespace de auth).
4. **`api/v1/admin-auth/login/` es una ruta aislada** para el login de superusuarios del panel
   Django (`AdminLoginView`); regla explícita en el código: no modificar ni fusionar con
   `api/v1/auth/`.
5. **Catch-all SPA real**: a diferencia de versiones muy antiguas (que solo servían `MEDIA_URL`
   en `DEBUG`), hay un `re_path` que sirve `spa_shell.html` para **cualquier** ruta que no
   empiece por `api/`, `admin/`, `static/` o `media/`. Esto es lo que permite que Vue Router
   (modo `createWebHistory`) maneje rutas como `/mi-cuenta/verificacion` o `/panel/usuarios`
   sin un 404 de Django al refrescar la página.

**Cambios reales posteriores a la auditoría 2026-07-12** (esta era la versión que documentaba
únicamente `security.api.urls` como el "6to include nuevo" — desde entonces se agregaron
varios más):

6. **`health_check` dejó de ser un stub** (`{"status": "ok"}` fijo) y ahora reutiliza
   `SecuritySelector.get_health_snapshot()` para comprobar DB y Redis de verdad, devolviendo
   `503` si alguno falla (Fase 15, `AUDITORIA/29_AUDITORIA_OBSERVABILIDAD.md`, 2026-08-03). El
   `HEALTHCHECK` de `docker-compose.prod.yml` para el servicio `django` (que hace `curl -f`
   contra este endpoint) era un falso positivo total antes de este cambio: podía reportar el
   contenedor como "healthy" (sin reiniciarlo) aunque Postgres/Redis fueran inalcanzables
   *desde Django* (credenciales rotas, pool agotado), incluso con los contenedores de
   Postgres/Redis sanos según su propio healthcheck independiente. Celery se reporta en el
   snapshot pero no bloquea el `200`/`503` — ya tiene su propio `HEALTHCHECK` independiente.
7. **`api/schema/` y `api/docs/` ahora exigen `IsAdminUser`** — antes cualquiera con sesión
   autenticada (`IsAuthenticated`, el default de `REST_FRAMEWORK`) podía ver el schema OpenAPI
   completo y el Swagger UI, exponiendo la superficie entera de la API a cualquier cliente
   registrado, no solo a administradores.
8. **3 endpoints nuevos de recuperación de contraseña para admin**:
   `admin-forgot-password-request/verify/reset-password` (`users.api.admin_password_reset`) —
   mismo patrón aislado que `admin-auth/login/`, no comparten namespace con `api/v1/auth/`.
9. **Bloque `internal/ai/` completo, nuevo**: `api/v1/internal/ai-context/` (`AiContextView`,
   resuelve identidad/perfil del usuario final para el AI Engine sin reimplementar
   `ProfileResolver`) y `api/v1/internal/ai/` (`include('ecommerce.internal_ai_urls')`, ~28
   endpoints de solo-lectura y escritura que respaldan las Tools del motor — ver
   [internal_ai_urls.py](#internal_ai_urlspy-y-internal_ai_utilspy---superficie-http-del-ai-core)
   abajo). Nginx no proxea `/internal/` hacia afuera.
10. **`technical_services` ahora tiene 2 includes** bajo el mismo prefijo `/api/v1/services/`:
    `operation_urls` (ya existía) + `availability_urls` (nuevo).
11. **`api/v1/support/` → `support.api.urls`**: antes `support` solo aportaba rutas WebSocket
    (vía `routing.py`); ahora también tiene su propio namespace REST.
12. **`api/v1/organization/` → `organization.api.urls`**: app nueva en construcción.
13. **`api/v1/` → `shared.api.urls`**: app nueva (UPDP Phase 1), define su propio sub-prefijo
    igual que `security.api.urls` (endpoint unificado `GET /api/v1/unified/detail/<uuid>/`).
14. **Ruta de verificación SEO** (`<str:filename>.html` → `seo_views.serve_verification_file`):
    debe ir **antes** del catch-all SPA — sirve archivos de verificación de dominio (Meta
    Business Suite, Google Search Console, etc.) o 404 si el filename no está
    registrado/activo en `seo.SiteVerificationFile`.

---

### **internal_ai_urls.py** y **internal_ai_utils.py** - Superficie HTTP del AI Core

Nuevos desde la auditoría 2026-07-12. `internal_ai_urls.py` (`app_name = "internal_ai"`)
concentra ~28 rutas bajo `/api/v1/internal/ai/*`, cada una envolviendo Selectors/Commands ya
existentes de su app dueña (ninguna lógica de negocio nueva vive aquí):

```python
urlpatterns = [
    # Fase 2 - lectura
    path("orders/", AiOrderStatusView.as_view(), name="ai-orders"),
    path("rentals/", AiRentalStatusView.as_view(), name="ai-rentals"),
    path("payments/", AiPaymentStatusView.as_view(), name="ai-payments"),
    # ... services/, kyc/, inventory/stock/, marketing/promos/
    # Fase 5 - CRM
    path("customer-context/", AiCustomerContextView.as_view(), name="ai-customer-context"),
    # Fase 4 - escritura (permission classes reales + SecurityEvent audit)
    path("rentals/create/", AiCreateRentalRequestView.as_view(), name="ai-rentals-create"),
    path("quotes/create/", AiStartQuotationView.as_view(), name="ai-quotes-create"),
    path("support/ticket/", AiOpenSupportTicketView.as_view(), name="ai-support-ticket"),
    # ... rentals/cancel/, quotes/templates/, kyc/request-upgrade/
    # Fase 8 - AI Business Automation (marketing/dashboard, stale-stock, campaign-targets,
    # recommendation; renting/maintenance; core/home, navbar, footer, brand-slider, banners)
]
```

`internal_ai_utils.py` da un único punto de auditoría compartido para las vistas de escritura:

```python
def log_ai_action(request, tool: str, metadata: dict) -> None:
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(
        SecurityEvent.AI_ACTION_EXECUTED, request=request,
        metadata={'tool': tool, **metadata},
    )
```

Cada módulo `<app>/api/internal_ai.py` debe importar `log_ai_action` desde aquí en vez de
definir su propia copia de `_log_ai_action` — evita que la lógica de auditoría diverja
silenciosamente entre las ~10 apps que exponen Tools de escritura al AI Engine.

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

Todos los modelos de negocio de las 21 apps de proyecto heredan `SintelBaseModel` en vez de
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
`default` para `accounts.*`), el resto de tareas cae en `default` vía
`CELERY_TASK_DEFAULT_QUEUE` (ver [CRITICAL] en la sección 16 de settings arriba — antes de
2026-07-27 esta linea no existia y el "resto" caia en la cola `celery`, sin worker
escuchandola). **Si agregas una tarea Celery en una app nueva o en una que ya tiene tareas,
verifica que su cola quede cubierta por `default` o por una entrada explícita en
`CELERY_TASK_ROUTES` que a su vez esté en el `-Q` de `celery_worker` en
`docker-compose.prod.yml` — de lo contrario la tarea se encola pero nunca se ejecuta, sin
ningún error visible.**

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
│   │   ├── health/                         [GET]  (DB + Redis reales, 503 si degradado)
│   │   ├── admin-auth/
│   │   │   ├── login/                      [POST]  (aislada, solo superusuarios)
│   │   │   ├── forgot-password-request/    [POST]
│   │   │   ├── forgot-password-verify/     [POST]
│   │   │   └── reset-password/             [POST]
│   │   ├── internal/                       (solo AI Engine, nginx NO proxea esto hacia afuera)
│   │   │   ├── ai-context/                 [GET]   → AiContextView
│   │   │   └── ai/                         → ecommerce.internal_ai_urls (~28 rutas)
│   │   ├── auth/          → accounts.urls + kyc.api.urls (mismo prefijo)
│   │   ├── users/         → users.urls
│   │   ├── dashboard/     → dashboard.api.urls
│   │   ├── shop/          → shop.urls
│   │   ├── cart/          → cart.urls
│   │   ├── orders/        → orders.urls
│   │   ├── payment/       → payment.urls
│   │   ├── inventory/     → inventory.urls
│   │   ├── services/      → technical_services.urls + technical_services.api.availability_urls
│   │   ├── service-operations/ → technical_services.api.operation_urls
│   │   ├── quotes/        → quotes.urls
│   │   ├── marketing/     → marketing.urls
│   │   ├── renting/       → renting.urls
│   │   ├── support/       → support.api.urls
│   │   ├── core/          → core.urls
│   │   ├── notifications/ → notifications.api.urls
│   │   ├── operations/    → operations.api.urls
│   │   ├── organization/  → organization.api.urls
│   │   └── (raíz)         → security.api.urls + shared.api.urls
│   ├── schema/                             [GET]  (OpenAPI schema, solo IsAdminUser)
│   └── docs/                               [GET]  (Swagger UI, solo IsAdminUser)
├── admin/                                  [GET, POST] (Django Admin)
├── ws/  y  ws                              [WebSocket]
├── .well-known/appspecific/com.chrome.devtools.json   [GET]  (silenciador de 404)
├── media/                                  (solo si DEBUG=True)
├── <filename>.html                         [GET]  (verificacion de dominio, seo.SiteVerificationFile)
└── <cualquier otra ruta>                   → spa_shell.html (Vue Router SPA)
```

> El árbol de la primera versión de este documento (`wompi/`, `dashboard/overview` inventado,
> sin catch-all SPA) no reflejaba el `urls.py` real de entonces; se reemplazó por la lista
> literal de `include()`s. Este árbol se actualizó de nuevo el 2026-08-08 para reflejar los
> cambios reales posteriores a la auditoría 2026-07-12 (bloque `internal/ai/`, `support/`,
> `organization/`, `shared`, verificación SEO, `schema`/`docs` restringidos a admin, y
> `health/` chequeando DB/Redis de verdad — ver [urls.py](#urlspy---rutas-principales) arriba
> para el detalle de cada cambio).

---

## Stack Tecnológico

### Backend
- **Django 5.2.13** (ver `CLAUDE.md` raíz del proyecto)
- **Django REST Framework** + `drf-spectacular` (Swagger/OpenAPI, `schema`/`docs` restringidos
  a `IsAdminUser`)
- **Django SimpleJWT** (access **15 min** / refresh 7 días, rotación + blacklist — bajó de 60
  min tras QW-17)
- **django-channels** + **channels_redis**: WebSocket con auth JWT custom, `capacity=1000`/
  `expiry=60` explícitos
- **Celery** + **django_celery_beat** (`DatabaseScheduler`, no dict en settings) — `ACKS_LATE`,
  `REJECT_ON_WORKER_LOST`, límites de tiempo (300s duro / 240s soft)
- **PostgreSQL** (producción y Docker dev) / **SQLite** (dev local sin Docker)
- **Redis**: cache (db 1), broker/result-backend de Celery y channel layer (db 0)
- **Wompi Colombia** + **Nequi**: pasarelas de pago
- **AI Core** (`ai_engine/`, sintel_ai): motor de IA interno, nunca expuesto a Internet —
  Django lo alcanza vía `AI_ENGINE_URL` y expone `internal_ai_urls.py` como su única superficie
  HTTP hacia adentro

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
- **GitHub Actions** (`.github/workflows/ci.yml`, Quality Gate): existe desde la auditoría
  enterprise — corrige el punto 5 de "Mejoras Potenciales" de la versión anterior de este
  documento, que decía que no había CI/CD.

### Testing
- `python manage.py test` (Django `TestCase`), no pytest — confirmado en
  `project_wompi_payment_app_sync` (memoria del agente)

---

## Mejoras Potenciales

Actualizado 2026-08-08 — varias de las mejoras que listaba la auditoría 2026-07-12 **ya están
resueltas**:

1. ~~Rate Limiting~~ → **Ya implementado**: `DEFAULT_THROTTLE_RATES` (ahora 22 scopes, ver
   sección 13 de settings) + `ScopedRateThrottle` por acción, con logging a `SecurityEvent` en
   `api_exceptions.py`.
2. ~~CI/CD~~ → **Ya implementado**: `.github/workflows/ci.yml` (Quality Gate) corre en el repo.
3. **Logging centralizado**: sigue siendo solo consola (`LOGGING` en settings) — no hay Sentry
   ni stack ELK. Sigue siendo una mejora pendiente real.
4. **Caching avanzado**: existe el switch Redis/locmem, pero no hay cache a nivel de
   serializers/vistas más allá de lo puntual (p. ej. `core.home-feed` con cache de 5 min, ver
   `project_home_page` en memoria).
5. **2FA**: no implementado a nivel de settings/auth (KYC es verificación de identidad, no
   2FA de login).
6. **Monitoring** (Prometheus/Grafana): pendiente.

---

## Conclusión

El módulo **ecommerce** (core) sigue siendo la base del proyecto, y ha seguido creciendo desde
la primera auditoría (2026-07-12): de ~12 a 18 apps de proyecto entonces, y de 18 a **21 apps**
ahora (`organization`, `seo`, `shared`). Se agregó el bloque completo de **AI Core**
(`internal_ai_urls.py`/`internal_ai_utils.py`, ~28 endpoints internos, settings
`AI_ENGINE_URL`/`AI_SUPPORT_CHAT_ENABLED`/`AI_BOT_EMAIL`/etc.), `health_check` pasó de un stub
fijo a verificar DB/Redis de verdad, y se cerraron varios hallazgos reales de auditoría:
`schema`/`docs` restringidos a admin, JWT de 60 a 15 minutos, `CORS_ALLOW_ALL_ORIGINS=False`
explícito, dos fail-safes nuevos en `production.py` (aborta el arranque si `DEBUG=True` o si
falta `WOMPI_EVENTS_SECRET`), límites de tiempo/ack en Celery, y `capacity`/`expiry` explícitos
en `CHANNEL_LAYERS`.

Los cambios estructurales previos siguen vigentes: renombres importantes (`wompi`→`payment`,
`coreui`→`dashboard`+`core`), auth de WebSocket por JWT (`support.channels_auth`), exception
handler global integrado con el Security Center, validador de contraseña propio, SPA catch-all
real, y el bloque de configuración de integraciones externas (marketing, IA, pagos, SMS).

Todos los módulos de negocio siguen heredando `SintelBaseModel` y usando `ws_notify()` /
`dispatch_notification()` para tiempo real, manteniendo el patrón original de este core.
