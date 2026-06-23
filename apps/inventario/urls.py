from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InventarioProductoDetalleView,
    InventarioViewSet,
    MovimientoInventarioViewSet,
)

router = DefaultRouter()
router.register("inventario", InventarioViewSet, basename="inventario")
router.register("movimientos", MovimientoInventarioViewSet, basename="movimiento")

urlpatterns = [
    path(
        "inventario/producto/<int:producto_id>/",
        InventarioProductoDetalleView.as_view(),
        name="inventario-producto",
    ),
] + router.urls
