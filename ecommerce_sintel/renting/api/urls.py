from django.urls import path, include
from rest_framework.routers import DefaultRouter
from renting.api.views import (
    EquipmentViewSet,
    EquipmentVariantViewSet,
    RentingCategoryViewSet,
    RentingBrandViewSet,
    RentalLaborViewSet,
    RentalRequestViewSet,
    RentalRequestListCreateAPIView,
    EquipmentBlockViewSet,
)
from renting.api.operation_views import RentalOperationViewSet

router = DefaultRouter()
router.register(r'equipment',        EquipmentViewSet,       basename='equipment-rental')
router.register(r'variants',         EquipmentVariantViewSet,basename='equipment-variant')
router.register(r'categories',       RentingCategoryViewSet, basename='renting-category')
router.register(r'brands',           RentingBrandViewSet,    basename='renting-brand')
router.register(r'labor',            RentalLaborViewSet,     basename='rental-labor')
router.register(r'rental-requests',  RentalRequestViewSet,   basename='rental-request')
router.register(r'operations', RentalOperationViewSet, basename='rental-operation')
router.register(r'equipment-blocks', EquipmentBlockViewSet,  basename='equipment-block')

urlpatterns = [
    path('rental-requests/', RentalRequestListCreateAPIView.as_view(), name='rental-request-list-create'),
    path('', include(router.urls)),
]
