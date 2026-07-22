from django.urls import path
from support.api.views import RateConversationView

urlpatterns = [
    path('chats/<str:room_uuid>/rate/', RateConversationView.as_view(), name='support-rate-conversation'),
]
