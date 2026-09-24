"""HARDENING F7 (2026-09-24): rutas para que el PROPIO cliente vea y borre su memoria (Habeas Data)."""
from django.urls import path

from .views import CustomerMemoryOwnerDetailView, CustomerMemoryOwnerListView

urlpatterns = [
    path('', CustomerMemoryOwnerListView.as_view(), name='customer-memory-list'),
    path('<uuid:record_uuid>/', CustomerMemoryOwnerDetailView.as_view(), name='customer-memory-detail'),
]
