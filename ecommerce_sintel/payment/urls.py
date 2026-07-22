from django.urls import path, include

urlpatterns = [
    path('payments/', include('payment.online.urls')),
    path('nequi/', include('payment.nequi.urls')),
    path('cards/', include('payment.cards.urls')),
]
