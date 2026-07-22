from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shop.api.views import (
    ProductViewSet,
    ProductVariantViewSet,
    CategoryViewSet,
    BrandViewSet,
    TaxViewSet,
)

app_name = 'shop'

router = DefaultRouter(trailing_slash=True)
router.register(r'products',  ProductViewSet,        basename='product')
router.register(r'variants',  ProductVariantViewSet, basename='variant')
router.register(r'categories', CategoryViewSet,      basename='category')
router.register(r'brands',    BrandViewSet,          basename='brand')
router.register(r'taxes',     TaxViewSet,            basename='tax')

urlpatterns = [
    path('', include(router.urls)),
]
