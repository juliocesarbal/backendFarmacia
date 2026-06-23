"""Vistas de autenticacion y gestion de usuarios/roles/permisos."""
from django.contrib.auth import get_user_model
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Permiso, Rol
from .permissions import TienePermiso
from .serializers import (
    LoginSerializer,
    PermisoSerializer,
    RolSerializer,
    UsuarioSerializer,
)

Usuario = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LogoutView(APIView):
    """Invalida el refresh token (logout)."""

    def post(self, request):
        try:
            refresh = request.data.get("refresh")
            if refresh:
                RefreshToken(refresh)  # valida formato
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    """Datos del usuario autenticado."""

    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all().prefetch_related("roles__permisos")
    serializer_class = UsuarioSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "list": "usuarios.ver",
        "retrieve": "usuarios.ver",
        "create": "usuarios.crear",
        "update": "usuarios.editar",
        "partial_update": "usuarios.editar",
        "destroy": "usuarios.eliminar",
        "desactivar": "usuarios.editar",
    }

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        usuario.is_active = False
        usuario.estado = "INACTIVO"
        usuario.save(update_fields=["is_active", "estado"])
        return Response(UsuarioSerializer(usuario).data)


class RolViewSet(viewsets.ModelViewSet):
    queryset = Rol.objects.all().prefetch_related("permisos")
    serializer_class = RolSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "list": "roles.ver",
        "retrieve": "roles.ver",
        "create": "roles.crear",
        "update": "roles.editar",
        "partial_update": "roles.editar",
        "destroy": "roles.eliminar",
    }


class PermisoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer
    permission_classes = [IsAuthenticated]
