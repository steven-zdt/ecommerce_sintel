from django.urls import path
from security.api.views import SecurityHealthView

urlpatterns = [
    path('security/health/', SecurityHealthView.as_view(), name='security-health'),
]
