from django.urls import path, include

urlpatterns = [
    path('', include('renting.api.urls')),
]
