from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.api.views import StockRecordViewSet, InventoryTransactionViewSet

router = DefaultRouter()
router.register(r'stock-records', StockRecordViewSet, basename='stock-record')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventory-transaction')

urlpatterns = [
    path('', include(router.urls)),
]
