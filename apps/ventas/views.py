from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import TienePermiso

from .models import Venta
from .serializers import VentaSerializer
from .services import VentaError, anular_venta, confirmar_venta


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.prefetch_related("detalles__producto")
    serializer_class = VentaSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "ventas.crear",
        "update": "ventas.editar",
        "partial_update": "ventas.editar",
        "confirmar": "ventas.confirmar",
        "anular": "ventas.anular",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            venta = confirmar_venta(pk, usuario=request.user)
        except VentaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(venta).data)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        motivo = request.data.get("motivo", "")
        try:
            venta = anular_venta(pk, motivo=motivo, usuario=request.user)
        except VentaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(venta).data)

    @action(detail=True, methods=["get"])
    def boleta(self, request, pk=None):
        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=False, methods=["get"])
    def anuladas(self, request):
        qs = self.get_queryset().filter(estado="ANULADA")
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page else Response(ser.data)
