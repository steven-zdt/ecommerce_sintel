from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payment.online.api.views import WompiPaymentViewSet

router = DefaultRouter()
router.register(r'', WompiPaymentViewSet, basename='wompi-payments')

urlpatterns = [
    path('', include(router.urls)),
]
