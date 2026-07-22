from django.urls import path, include
from rest_framework.routers import DefaultRouter
from payment.cards.views import TokenizedCardViewSet

router = DefaultRouter()
router.register(r'', TokenizedCardViewSet, basename='tokenized-card')

urlpatterns = [
    path('', include(router.urls)),
]
