from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import TienePermiso

from .models import Compra
from .serializers import CompraSerializer
from .services import CompraError, confirmar_compra


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related("proveedor").prefetch_related(
        "detalles__producto"
    )
    serializer_class = CompraSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "compras.crear",
        "update": "compras.editar",
        "partial_update": "compras.editar",
        "confirmar": "compras.confirmar",
    }

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            compra = confirmar_compra(pk, usuario=request.user)
        except CompraError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(compra).data)

    @action(detail=True, methods=["get"])
    def boleta(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)
