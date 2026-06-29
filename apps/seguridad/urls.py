"""Rutas de usuarios, roles y permisos."""
from rest_framework.routers import DefaultRouter

from .views import PermisoViewSet, RolViewSet, UsuarioViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("roles", RolViewSet, basename="rol")
router.register("permisos", PermisoViewSet, basename="permiso")

urlpatterns = router.urls
