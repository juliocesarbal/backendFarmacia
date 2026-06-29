from django.urls import path

from .views import (
    KardexExcelView,
    KardexPdfView,
    KardexPorCodigoView,
    KardexProductoView,
)

urlpatterns = [
    path(
        "kardex/producto/<int:producto_id>/",
        KardexProductoView.as_view(),
        name="kardex-producto",
    ),
    path(
        "kardex/codigo/<str:codigo>/",
        KardexPorCodigoView.as_view(),
        name="kardex-codigo",
    ),
    path(
        "kardex/producto/<int:producto_id>/exportar-excel/",
        KardexExcelView.as_view(),
        name="kardex-excel",
    ),
    path(
        "kardex/producto/<int:producto_id>/exportar-pdf/",
        KardexPdfView.as_view(),
        name="kardex-pdf",
    ),
]
