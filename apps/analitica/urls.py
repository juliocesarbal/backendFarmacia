from django.urls import path

from .views import KMeansEjecutarView, KMeansExcelView, KMeansResultadosView

urlpatterns = [
    path("analitica/kmeans/ejecutar/", KMeansEjecutarView.as_view(), name="kmeans-ejecutar"),
    path(
        "analitica/kmeans/<int:pk>/resultados/",
        KMeansResultadosView.as_view(),
        name="kmeans-resultados",
    ),
    path(
        "analitica/kmeans/<int:pk>/exportar/",
        KMeansExcelView.as_view(),
        name="kmeans-exportar",
    ),
]
