from django.urls import path, include
from rest_framework.routers import DefaultRouter

from technical_services.api.operation_views import ServiceOperationViewSet

router = DefaultRouter(trailing_slash=True)
router.register(r'', ServiceOperationViewSet, basename='service-operation')

urlpatterns = [
    path('', include(router.urls)),
]
