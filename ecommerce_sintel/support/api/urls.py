from django.urls import path
from support.api.views import CreateSupportTicketView, RateConversationView

urlpatterns = [
    path('chats/<str:room_uuid>/rate/', RateConversationView.as_view(), name='support-rate-conversation'),
    path('tickets/create/', CreateSupportTicketView.as_view(), name='support-create-ticket'),
]
