from django.urls import path, include

urlpatterns = [
    path('', include('marketing.api.urls')),
]
