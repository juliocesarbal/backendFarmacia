from rest_framework.routers import DefaultRouter

from .views import (
    CategoriaProductoViewSet,
    ProductoViewSet,
    UnidadMedidaViewSet,
)

router = DefaultRouter()
router.register("productos", ProductoViewSet, basename="producto")
router.register("categorias", CategoriaProductoViewSet, basename="categoria")
router.register("unidades", UnidadMedidaViewSet, basename="unidad")

urlpatterns = router.urls
