from django.urls import path, include
from rest_framework.routers import DefaultRouter
from kyc.api.views import KycViewSet, VerificationDocumentViewSet, AdminKycViewSet

router = DefaultRouter()
router.register(r'documents', VerificationDocumentViewSet, basename='kyc-document')
router.register(r'admin/verifications', AdminKycViewSet, basename='admin-kyc')
router.register(r'', KycViewSet, basename='kyc')

urlpatterns = [
    path('', include(router.urls)),
]
