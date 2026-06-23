from django.urls import path

from .views import (
    ImportacionConfirmarView,
    ImportacionErroresView,
    ImportarComprasView,
    ImportarInventarioInicialView,
    ImportarVentasView,
)

urlpatterns = [
    path(
        "importaciones/inventario-inicial/",
        ImportarInventarioInicialView.as_view(),
        name="importar-inventario",
    ),
    path("importaciones/compras/", ImportarComprasView.as_view(), name="importar-compras"),
    path("importaciones/ventas/", ImportarVentasView.as_view(), name="importar-ventas"),
    path(
        "importaciones/<int:pk>/errores/",
        ImportacionErroresView.as_view(),
        name="importacion-errores",
    ),
    path(
        "importaciones/<int:pk>/confirmar/",
        ImportacionConfirmarView.as_view(),
        name="importacion-confirmar",
    ),
]
