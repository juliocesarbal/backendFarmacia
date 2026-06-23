from django.urls import path

from .views import (
    ReporteAlertasView,
    ReporteBajasView,
    ReporteComprasView,
    ReporteInventarioView,
    ReporteTrazabilidadView,
    ReporteVentasView,
)

urlpatterns = [
    path("reportes/compras/", ReporteComprasView.as_view(), name="reporte-compras"),
    path("reportes/ventas/", ReporteVentasView.as_view(), name="reporte-ventas"),
    path("reportes/bajas/", ReporteBajasView.as_view(), name="reporte-bajas"),
    path("reportes/inventario/", ReporteInventarioView.as_view(), name="reporte-inventario"),
    path("reportes/trazabilidad/", ReporteTrazabilidadView.as_view(), name="reporte-trazabilidad"),
    path("reportes/alertas/", ReporteAlertasView.as_view(), name="reporte-alertas"),
]
