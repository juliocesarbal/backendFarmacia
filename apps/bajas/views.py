from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import TienePermiso

from .models import Baja, MotivoBaja
from .serializers import BajaSerializer, MotivoBajaSerializer
from .services import BajaError, confirmar_baja


class MotivoBajaViewSet(viewsets.ModelViewSet):
    queryset = MotivoBaja.objects.all()
    serializer_class = MotivoBajaSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "bajas.gestionar",
        "update": "bajas.gestionar",
        "partial_update": "bajas.gestionar",
    }


class BajaViewSet(viewsets.ModelViewSet):
    queryset = Baja.objects.select_related("motivo_baja").prefetch_related(
        "detalles__producto"
    )
    serializer_class = BajaSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "bajas.crear",
        "update": "bajas.editar",
        "partial_update": "bajas.editar",
        "confirmar": "bajas.confirmar",
    }

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            baja = confirmar_baja(pk, usuario=request.user)
        except BajaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(baja).data)

    @action(detail=True, methods=["get"])
    def boleta(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)
