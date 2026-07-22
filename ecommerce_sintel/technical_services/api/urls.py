from django.urls import path, include
from rest_framework.routers import DefaultRouter
from technical_services.api.views import (
    TechnicalServiceViewSet,
    ServiceCategoryViewSet,
    ServiceLevelViewSet,
    ServiceVariantViewSet,
    ServiceMaterialViewSet,
    ServiceConfigurationViewSet,
)

router = DefaultRouter(trailing_slash=True)
router.register(r'services',        TechnicalServiceViewSet,    basename='technical-service')
router.register(r'categories',      ServiceCategoryViewSet,     basename='service-category')
router.register(r'levels',          ServiceLevelViewSet,        basename='service-level')
router.register(r'variants',        ServiceVariantViewSet,      basename='service-variant')
router.register(r'materials',       ServiceMaterialViewSet,     basename='service-material')
router.register(r'configurations',  ServiceConfigurationViewSet, basename='service-configuration')

urlpatterns = [
    path('', include(router.urls)),
]
