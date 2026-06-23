from rest_framework.routers import DefaultRouter

from .views import VentaViewSet

router = DefaultRouter()
router.register("ventas", VentaViewSet, basename="venta")

urlpatterns = router.urls
