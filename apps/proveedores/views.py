from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import TienePermiso

from .models import Proveedor
from .serializers import ProveedorSerializer


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "proveedores.crear",
        "update": "proveedores.editar",
        "partial_update": "proveedores.editar",
        "desactivar": "proveedores.editar",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        buscar = self.request.query_params.get("buscar")
        if buscar:
            qs = qs.filter(Q(nombre__icontains=buscar) | Q(nit__icontains=buscar))
        return qs

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        proveedor = self.get_object()
        proveedor.estado = "INACTIVO"
        proveedor.save(update_fields=["estado"])
        return Response(self.get_serializer(proveedor).data)
