from rest_framework.routers import DefaultRouter

from .views import CompraViewSet, ProveedorViewSet

router = DefaultRouter()
router.register("compras", CompraViewSet, basename="compra")
router.register("proveedores", ProveedorViewSet, basename="proveedor")

urlpatterns = router.urls
