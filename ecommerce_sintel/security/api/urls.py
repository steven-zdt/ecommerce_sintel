from django.urls import path
from rest_framework.routers import DefaultRouter

from security.api.views import SecurityHealthView, SecurityEventViewSet

router = DefaultRouter()
router.register('security/events', SecurityEventViewSet, basename='security-event')

urlpatterns = [
    path('security/health/', SecurityHealthView.as_view(), name='security-health'),
] + router.urls
