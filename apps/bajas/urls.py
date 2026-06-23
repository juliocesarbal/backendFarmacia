from rest_framework.routers import DefaultRouter

from .views import BajaViewSet, MotivoBajaViewSet

router = DefaultRouter()
router.register("bajas", BajaViewSet, basename="baja")
router.register("motivos-baja", MotivoBajaViewSet, basename="motivo-baja")

urlpatterns = router.urls
