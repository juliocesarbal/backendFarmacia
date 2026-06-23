from rest_framework.routers import DefaultRouter

from .views import ProveedorViewSet

router = DefaultRouter()
router.register("proveedores", ProveedorViewSet, basename="proveedor")

urlpatterns = router.urls
