from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AjusteInventarioViewSet,
    BajaViewSet,
    InventarioProductoDetalleView,
    InventarioViewSet,
    MotivoBajaViewSet,
    MovimientoInventarioViewSet,
)

router = DefaultRouter()
router.register("inventario", InventarioViewSet, basename="inventario")
router.register("movimientos", MovimientoInventarioViewSet, basename="movimiento")
router.register("bajas", BajaViewSet, basename="baja")
router.register("motivos-baja", MotivoBajaViewSet, basename="motivo-baja")
router.register("ajustes", AjusteInventarioViewSet, basename="ajuste")

urlpatterns = [
    path(
        "inventario/producto/<int:producto_id>/",
        InventarioProductoDetalleView.as_view(),
        name="inventario-producto",
    ),
] + router.urls
