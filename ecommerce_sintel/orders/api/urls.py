from django.urls import path, include
from rest_framework.routers import DefaultRouter
from orders.api.views import OrderViewSet, ShippingAddressViewSet
from orders.api.service_orders import ServiceOrderViewSet

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'addresses', ShippingAddressViewSet, basename='shipping-address')
router.register(r'service-orders', ServiceOrderViewSet, basename='service-order')

urlpatterns = [
    path('', include(router.urls)),
]
