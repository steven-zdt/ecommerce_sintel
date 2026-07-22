from django.urls import path
from orders.api.dashboard import DashboardMetricsView

urlpatterns = [
    path('metrics/', DashboardMetricsView.as_view(), name='dashboard-metrics'),
]
