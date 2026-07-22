from django.urls import path, include
from rest_framework.routers import DefaultRouter

from technical_services.api.availability_views import (
    TechnicianAvailabilityViewSet,
    WorkingScheduleViewSet,
    WorkingExceptionViewSet,
)

router = DefaultRouter(trailing_slash=True)
router.register(r'technician-availability', TechnicianAvailabilityViewSet, basename='technician-availability')
router.register(r'working-schedules', WorkingScheduleViewSet, basename='working-schedule')
router.register(r'working-exceptions', WorkingExceptionViewSet, basename='working-exception')

urlpatterns = [
    path('', include(router.urls)),
]
