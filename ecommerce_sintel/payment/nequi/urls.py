from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payment.nequi.api.views import NequiPaymentViewSet

router = DefaultRouter()
router.register(r'', NequiPaymentViewSet, basename='wompi-nequi')

urlpatterns = [
    path('', include(router.urls)),
]
