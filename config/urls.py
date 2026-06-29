"""URLs raiz del proyecto."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

api_v1 = [
    path("auth/", include("apps.seguridad.urls_auth")),
    path("", include("apps.seguridad.urls")),
    path("", include("apps.catalogo.urls")),
    path("", include("apps.compras.urls")),
    path("", include("apps.ventas.urls")),
    path("", include("apps.inventario.urls")),
    path("", include("apps.kardex.urls")),
    path("", include("apps.importacion.urls")),
    path("", include("apps.reportes.urls")),
    path("", include("apps.analitica.urls")),
    path("", include("apps.auditoria.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(api_v1)),
    # OpenAPI / Swagger
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
