from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.seguridad.permissions import TienePermiso

from .models import Compra, Proveedor
from .serializers import CompraSerializer, ProveedorSerializer
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
        compra = self.get_object()
        if request.query_params.get("formato") == "pdf":
            from apps.reportes.boletas import boleta_pdf
            return boleta_pdf(
                "Boleta de Compra",
                [("N Factura", compra.numero_factura), ("N Orden", compra.numero_orden),
                 ("Proveedor", compra.proveedor.nombre), ("Fecha", compra.fecha_compra),
                 ("Estado", compra.estado)],
                [("Producto", "producto"), ("Cant.", "cantidad"),
                 ("Costo Unit.", "costo_unitario"), ("Subtotal", "costo_total")],
                [{"producto": d.producto.nombre, "cantidad": d.cantidad,
                  "costo_unitario": d.costo_unitario, "costo_total": d.costo_total}
                 for d in compra.detalles.select_related("producto")],
                "Total", compra.total_compra, nombre_archivo=f"boleta_compra_{compra.id}",
            )
        return Response(self.get_serializer(compra).data)


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
