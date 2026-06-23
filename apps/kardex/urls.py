from django.urls import path

from .views import KardexExcelView, KardexPdfView, KardexProductoView

urlpatterns = [
    path(
        "kardex/producto/<int:producto_id>/",
        KardexProductoView.as_view(),
        name="kardex-producto",
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
