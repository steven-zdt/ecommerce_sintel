from django.urls import path, include

urlpatterns = [
    path('', include('technical_services.api.urls')),
]
