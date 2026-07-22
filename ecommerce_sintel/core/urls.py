from rest_framework.routers import DefaultRouter
from core.api.views import HomeFeedView

router = DefaultRouter()
router.register(r'', HomeFeedView, basename='core')

urlpatterns = router.urls
