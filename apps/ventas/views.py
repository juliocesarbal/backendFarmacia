from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.seguridad.permissions import TienePermiso

from .models import Venta
from .serializers import VentaSerializer
from .services import (
    VentaError,
    anular_venta,
    entregar_venta,
    registrar_comprobante,
    verificar_pago,
)


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.prefetch_related("detalles__producto", "comprobantes")
    serializer_class = VentaSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "ventas.crear",
        "update": "ventas.editar",
        "partial_update": "ventas.editar",
        "registrar_comprobante": "ventas.confirmar",
        "verificar_pago": "ventas.confirmar",
        "entregar": "ventas.confirmar",
        "anular": "ventas.anular",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        for campo in ("estado", "estado_pago", "estado_entrega", "tipo_venta"):
            val = self.request.query_params.get(campo)
            if val:
                qs = qs.filter(**{campo: val})
        return qs

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    def _accion(self, func, request, pk, **kw):
        try:
            venta = func(pk, usuario=request.user, **kw)
        except VentaError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(venta).data)

    @action(detail=True, methods=["post"], url_path="registrar-comprobante")
    def registrar_comprobante(self, request, pk=None):
        return self._accion(registrar_comprobante, request, pk, datos=request.data)

    @action(detail=True, methods=["post"], url_path="verificar-pago")
    def verificar_pago(self, request, pk=None):
        return self._accion(verificar_pago, request, pk)

    @action(detail=True, methods=["post"])
    def entregar(self, request, pk=None):
        return self._accion(entregar_venta, request, pk)

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        return self._accion(anular_venta, request, pk, motivo=request.data.get("motivo", ""))

    @action(detail=True, methods=["get"])
    def boleta(self, request, pk=None):
        venta = self.get_object()
        if request.query_params.get("formato") == "pdf":
            from apps.reportes.boletas import boleta_pdf
            return boleta_pdf(
                "Boleta de Venta",
                [("N Boleta", venta.numero_boleta or venta.id),
                 ("Tipo", venta.tipo_venta), ("Fecha", venta.fecha_venta),
                 ("Pago", venta.estado_pago), ("Entrega", venta.estado_entrega)],
                [("Producto", "producto"), ("Cant.", "cantidad"),
                 ("P. Unit.", "precio_unitario"), ("Subtotal", "subtotal")],
                [{"producto": d.producto.nombre, "cantidad": d.cantidad,
                  "precio_unitario": d.precio_unitario, "subtotal": d.subtotal}
                 for d in venta.detalles.select_related("producto")],
                "Total", venta.total_venta, nombre_archivo=f"boleta_venta_{venta.id}",
            )
        return Response(self.get_serializer(venta).data)

    @action(detail=False, methods=["get"])
    def anuladas(self, request):
        qs = self.get_queryset().filter(estado="ANULADA")
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page or qs, many=True)
        return self.get_paginated_response(ser.data) if page else Response(ser.data)
