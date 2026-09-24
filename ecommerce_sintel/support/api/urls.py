from django.urls import path
from support.api.views import CreateSupportTicketView, RateConversationView, ResumeAiView

urlpatterns = [
    path('chats/<str:room_uuid>/rate/', RateConversationView.as_view(), name='support-rate-conversation'),
    path('chats/<str:room_uuid>/resume-ai/', ResumeAiView.as_view(), name='support-resume-ai'),
    path('tickets/create/', CreateSupportTicketView.as_view(), name='support-create-ticket'),
]
