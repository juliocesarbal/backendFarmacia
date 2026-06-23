from rest_framework.routers import DefaultRouter

from .views import AjusteInventarioViewSet

router = DefaultRouter()
router.register("ajustes", AjusteInventarioViewSet, basename="ajuste")

urlpatterns = router.urls
