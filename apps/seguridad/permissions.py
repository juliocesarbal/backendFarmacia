"""Permisos DRF basados en roles/permisos del sistema (RNF12)."""
from rest_framework.permissions import BasePermission


class TienePermiso(BasePermission):
    """
    Permiso de DRF que valida un codigo concreto contra los roles del usuario.

    Uso en un ViewSet:
        permission_classes = [TienePermiso]
        permiso_requerido = "compras.crear"

    O por accion:
        permisos_por_accion = {
            "create": "compras.crear",
            "list": "compras.ver",
        }
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True

        codigo = self._codigo_requerido(view)
        if codigo is None:
            return True  # sin codigo declarado -> basta con estar autenticado
        return user.tiene_permiso(codigo)

    @staticmethod
    def _codigo_requerido(view):
        por_accion = getattr(view, "permisos_por_accion", None)
        if por_accion:
            accion = getattr(view, "action", None)
            if accion in por_accion:
                return por_accion[accion]
        return getattr(view, "permiso_requerido", None)
