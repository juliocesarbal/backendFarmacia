from django.db.models import Q
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import InventarioProducto, MovimientoInventario
from .serializers import (
    InventarioProductoSerializer,
    MovimientoInventarioSerializer,
)


class InventarioViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = InventarioProducto.objects.select_related("producto")
    serializer_class = InventarioProductoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        tipo = self.request.query_params.get("tipo")
        buscar = self.request.query_params.get("buscar")
        if tipo:
            qs = qs.filter(producto__tipo_producto=tipo)
        if buscar:
            qs = qs.filter(
                Q(producto__codigo_producto__icontains=buscar)
                | Q(producto__nombre__icontains=buscar)
            )
        return qs


class InventarioProductoDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, producto_id):
        inv = InventarioProducto.objects.filter(producto_id=producto_id).first()
        if not inv:
            return Response({"producto": producto_id, "cantidad_actual": 0})
        return Response(InventarioProductoSerializer(inv).data)


class MovimientoInventarioViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = MovimientoInventario.objects.select_related("producto")
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        producto = self.request.query_params.get("producto")
        if producto:
            qs = qs.filter(producto_id=producto)
        return qs
