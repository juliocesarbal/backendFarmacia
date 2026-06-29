from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.seguridad.permissions import TienePermiso

from .models import (
    AjusteInventario,
    Baja,
    InventarioProducto,
    MotivoBaja,
    MovimientoInventario,
)
from .serializers import (
    AjusteInventarioSerializer,
    BajaSerializer,
    InventarioProductoSerializer,
    MotivoBajaSerializer,
    MovimientoInventarioSerializer,
)
from .services import AjusteError, BajaError, confirmar_ajuste, confirmar_baja


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
        baja = self.get_object()
        if request.query_params.get("formato") == "pdf":
            from apps.reportes.boletas import boleta_pdf
            total = sum((d.costo_total_baja for d in baja.detalles.all()), 0)
            return boleta_pdf(
                "Boleta de Baja",
                [("N Baja", baja.numero_baja or baja.id),
                 ("Motivo", baja.motivo_baja.nombre),
                 ("Fecha", baja.fecha_baja), ("Estado", baja.estado)],
                [("Producto", "producto"), ("Cant.", "cantidad"), ("Costo", "costo")],
                [{"producto": d.producto.nombre, "cantidad": d.cantidad,
                  "costo": d.costo_total_baja}
                 for d in baja.detalles.select_related("producto")],
                "Total baja", total, nombre_archivo=f"boleta_baja_{baja.id}",
            )
        return Response(self.get_serializer(baja).data)


class AjusteInventarioViewSet(viewsets.ModelViewSet):
    queryset = AjusteInventario.objects.prefetch_related("detalles__producto")
    serializer_class = AjusteInventarioSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "ajustes.crear",
        "update": "ajustes.editar",
        "partial_update": "ajustes.editar",
        "confirmar": "ajustes.confirmar",
    }

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            ajuste = confirmar_ajuste(pk, usuario=request.user)
        except AjusteError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(ajuste).data)
