from django.urls import path
from .views import UnifiedPublicDetailViewSet

app_name = 'shared'

urlpatterns = [
    path(
        'unified/detail/<str:pk>/',
        UnifiedPublicDetailViewSet.as_view({'get': 'retrieve'}),
        name='unified-detail'
    ),
]
