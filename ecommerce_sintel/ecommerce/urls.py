"""
ecommerce/urls.py — Router principal del proyecto.

ARQUITECTURA API-FIRST:
- /api/v1/*: Todos los endpoints REST (DRF). Consumidos por el frontend Vue/Vite.
- El panel admin es una SPA Vue.js servida por Vite en desarrollo (puerto 5173).
"""
from django.contrib import admin
from django.urls import path, re_path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from users.api.admin_auth import AdminLoginView
from users.api.admin_password_reset import (
    AdminForgotPasswordRequestView,
    AdminForgotPasswordVerifyView,
    AdminResetPasswordView,
)
from users.api.internal import AiContextView
from users.api.permissions import IsAdminUser
from seo import views as seo_views

def health_check(request):
    """
    Fase 15 (AUDITORIA/29_AUDITORIA_OBSERVABILIDAD.md, 2026-08-03): antes devolvia
    {"status": "ok"} incondicionalmente -- el HEALTHCHECK de docker-compose.prod.yml para el
    servicio `django` (que hace curl -f contra este endpoint) era un falso positivo total: podia
    reportar el contenedor como "healthy" (sin reiniciarlo) mientras Postgres/Redis eran
    inalcanzables DESDE Django (ej. credenciales rotas, pool agotado), aunque los contenedores
    de Postgres/Redis en si mismos estuvieran sanos por su propio healthcheck independiente.
    Reusa SecuritySelector.get_health_snapshot() (ya existia, ya probado, solo expuesto antes
    detras de auth de admin) -- curl -f interpreta un status >=400 como fallo, lo que hace que
    Docker reinicie el contenedor via su politica `restart: unless-stopped` cuando corresponde.
    Celery se reporta mas no bloquea (el servicio celery_worker ya tiene su propio HEALTHCHECK
    independiente -- acoplarlo aqui duplicaria esa responsabilidad).
    """
    from security.services.selectors import SecuritySelector
    snapshot = SecuritySelector.get_health_snapshot()
    healthy = snapshot['db'] and snapshot['redis']
    return JsonResponse(
        {'status': 'ok' if healthy else 'degraded', **snapshot},
        status=200 if healthy else 503,
    )

urlpatterns = [
    # ── HEALTH CHECK ───────────────────────────────────────────────────────────
    path('api/v1/health/', health_check, name='health_check'),

    # ── DJANGO ADMIN ───────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ── API DOCS ───────────────────────────────────────────────────────────────
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[IsAdminUser]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[IsAdminUser]), name='swagger-ui'),

    # ── ADMIN AUTH — ruta aislada exclusiva para superusuarios ────────────────
    # REGLA: no modificar ni fusionar con api/v1/auth/. Ver users/api/admin_auth.py.
    path('api/v1/admin-auth/login/', AdminLoginView.as_view(), name='admin-login'),
    path('api/v1/admin-auth/forgot-password-request/', AdminForgotPasswordRequestView.as_view(), name='admin-forgot-password-request'),
    path('api/v1/admin-auth/forgot-password-verify/', AdminForgotPasswordVerifyView.as_view(), name='admin-forgot-password-verify'),
    path('api/v1/admin-auth/reset-password/', AdminResetPasswordView.as_view(), name='admin-reset-password'),

    # ── INTERNAL — consumido solo por el AI Engine via red Docker ─────────────
    # Fase 1 AI Core: el motor reenvia el JWT del usuario final a esta ruta
    # para resolver identidad/perfil sin reimplementar ProfileResolver.
    path('api/v1/internal/ai-context/', AiContextView.as_view(), name='ai-context'),
    # Fase 2 AI Core: endpoints read-only que respaldan las Tools del motor.
    path('api/v1/internal/ai/', include('ecommerce.internal_ai_urls')),

    # ── API ENDPOINTS (v1) ─────────────────────────────────────────────────────
    path('api/v1/auth/',      include('accounts.urls')),
    path('api/v1/auth/',      include('kyc.api.urls')),
    path('api/v1/users/',     include('users.urls')),
    path('api/v1/dashboard/', include('dashboard.api.urls')),
    path('api/v1/shop/',      include('shop.urls')),
    path('api/v1/cart/',      include('cart.urls')),
    path('api/v1/orders/',    include('orders.urls')),
    path('api/v1/payment/',   include('payment.urls')),
    path('api/v1/inventory/', include('inventory.urls')),
    path('api/v1/services/',  include('technical_services.urls')),
    path('api/v1/service-operations/', include('technical_services.api.operation_urls')),
    path('api/v1/services/',  include('technical_services.api.availability_urls')),
    path('api/v1/quotes/',    include('quotes.urls')),
    path('api/v1/marketing/', include('marketing.urls')),
    path('api/v1/renting/',   include('renting.urls')),
    path('api/v1/support/',   include('support.api.urls')),
    path('api/v1/core/',          include('core.urls')),
    path('api/v1/notifications/', include('notifications.api.urls')),
    path('api/v1/operations/',   include('operations.api.urls')),
    path('api/v1/organization/', include('organization.api.urls')),
    path('api/v1/',              include('security.api.urls')),
    path('api/v1/',              include('shared.api.urls')),

    # ── SILENCER (Chrome DevTools 404) ────────────────────────────────────────
    path('.well-known/appspecific/com.chrome.devtools.json', lambda r: JsonResponse({})),

    # ── SEO — archivos de verificacion en la raiz del dominio ─────────────────
    # Debe ir ANTES del catch-all de la SPA: sirve seo.SiteVerificationFile
    # (metodo "Subir archivo HTML" de Meta Business Suite / Google Search
    # Console / etc.), o 404 si el filename no esta registrado/activo.
    path('<str:filename>.html', seo_views.serve_verification_file, name='seo-verification-file'),

    # ── SPA (Vue) — catch-all, debe ir al final ───────────────────────────────
    # Sirve el shell HTML (src/apps/admin/main.js, monta en #shop-spa-root)
    # para cualquier ruta no capturada arriba. Vue Router (createWebHistory)
    # maneja el routing real en el cliente -- incluye tienda publica y /panel/*.
    re_path(r'^(?!api/|admin/|static/|media/).*$', TemplateView.as_view(template_name='spa_shell.html'), name='spa'),
]

# ── MEDIA FILES ─────────────────────────────────────────────────────────────
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
