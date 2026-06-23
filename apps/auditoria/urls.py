from rest_framework.routers import DefaultRouter

from .views import BitacoraOperacionViewSet

router = DefaultRouter()
router.register("trazabilidad", BitacoraOperacionViewSet, basename="trazabilidad")

urlpatterns = router.urls
