from django.urls import path, include
from rest_framework.routers import DefaultRouter
from operations.api.views import CustomerOperationViewSet, OperationalTaskViewSet

router = DefaultRouter()
router.register('my', CustomerOperationViewSet, basename='customer-operations')
router.register('tasks', OperationalTaskViewSet, basename='operational-tasks')

urlpatterns = [
    path('', include(router.urls)),
]
