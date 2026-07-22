from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.api.views import (
    AccountViewSet,
    ContractorProfileViewSet,
    ContractorSpecialtyViewSet,
    ContractorSkillViewSet,
    ProfessionalExperienceViewSet,
    AcademicTrainingViewSet,
    ProfessionalCourseViewSet,
    ProfessionalCertificationViewSet,
    SuccessCaseViewSet,
    AvailabilityViewSet,
    AdminContractorViewSet,
    GatedTokenObtainPairView,
)
from rest_framework_simplejwt.views import TokenRefreshView

router = DefaultRouter()
router.register(r'contractors', ContractorProfileViewSet, basename='contractor')
router.register(r'specialties', ContractorSpecialtyViewSet, basename='contractor-specialty')
router.register(r'skills', ContractorSkillViewSet, basename='contractor-skill')
router.register(r'experiences', ProfessionalExperienceViewSet, basename='contractor-experience')
router.register(r'academic-training', AcademicTrainingViewSet, basename='contractor-academic-training')
router.register(r'courses', ProfessionalCourseViewSet, basename='contractor-course')
router.register(r'certifications', ProfessionalCertificationViewSet, basename='contractor-certification')
router.register(r'success-cases', SuccessCaseViewSet, basename='contractor-success-case')
router.register(r'availability', AvailabilityViewSet, basename='availability')
router.register(r'admin/professionals', AdminContractorViewSet, basename='admin-professional')
router.register(r'', AccountViewSet, basename='account')

urlpatterns = [
    path('token/', GatedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
