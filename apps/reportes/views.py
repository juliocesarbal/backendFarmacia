"""Reportes consolidados (JSON) por rango de fechas."""
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogo.models import Producto
from apps.inventario.models import AjusteInventario, Baja, CapaCosto
from apps.compras.models import Compra
from apps.inventario.models import InventarioProducto
from apps.ventas.models import Venta

from .export import exportar_reporte

# Umbral por defecto de stock critico cuando el producto no define stock_minimo
STOCK_CRITICO_DEFAULT = 5


def _rango(request):
    hoy = date.today()
    desde = request.query_params.get("desde")
    hasta = request.query_params.get("hasta")
    desde = date.fromisoformat(desde) if desde else hoy - timedelta(days=30)
    hasta = date.fromisoformat(hasta) if hasta else hoy
    return desde, hasta


class ReporteComprasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        desde, hasta = _rango(request)
        qs = Compra.objects.filter(fecha_compra__gte=desde, fecha_compra__lte=hasta)
        estado = request.query_params.get("estado")
        proveedor = request.query_params.get("proveedor")
        if estado:
            qs = qs.filter(estado=estado)
        if proveedor:
            qs = qs.filter(proveedor_id=proveedor)
        agg = qs.filter(estado="CONFIRMADA").aggregate(
            total=Sum("total_compra"), cantidad=Count("id")
        )
        items = list(
            qs.values("id", "numero_factura", "fecha_compra", "estado",
                      "total_compra", "proveedor__nombre")
        )
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("#", "id"), ("Factura", "numero_factura"),
                ("Proveedor", "proveedor__nombre"), ("Fecha", "fecha_compra"),
                ("Estado", "estado"), ("Total", "total_compra"),
            ]
            exp = exportar_reporte(formato, "Reporte de compras", cols, items, agg)
            if exp:
                return exp
        return Response({"desde": desde, "hasta": hasta, "resumen": agg, "items": items})


class ReporteVentasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        desde, hasta = _rango(request)
        qs = Venta.objects.filter(
            fecha_venta__date__gte=desde, fecha_venta__date__lte=hasta
        )
        estado = request.query_params.get("estado")
        tipo = request.query_params.get("tipo")
        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo_venta=tipo)
        agg = qs.filter(estado="ACTIVA", estado_entrega="ENTREGADA").aggregate(
            total=Sum("total_venta"), cantidad=Count("id")
        )
        items = list(
            qs.values("id", "numero_boleta", "fecha_venta", "tipo_venta",
                      "total_venta", "estado", "estado_pago", "estado_entrega")
        )
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("#", "id"), ("Boleta", "numero_boleta"), ("Fecha", "fecha_venta"),
                ("Tipo", "tipo_venta"), ("Estado", "estado"), ("Total", "total_venta"),
            ]
            exp = exportar_reporte(formato, "Reporte de ventas", cols, items, agg)
            if exp:
                return exp
        return Response({"desde": desde, "hasta": hasta, "resumen": agg, "items": items})


class ReporteBajasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        desde, hasta = _rango(request)
        qs = Baja.objects.filter(
            fecha_baja__date__gte=desde, fecha_baja__date__lte=hasta
        )
        estado = request.query_params.get("estado")
        motivo = request.query_params.get("motivo")
        if estado:
            qs = qs.filter(estado=estado)
        if motivo:
            qs = qs.filter(motivo_baja_id=motivo)
        items = list(
            qs.values("id", "numero_baja", "fecha_baja", "estado", "motivo_baja__nombre")
        )
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("#", "id"), ("N° Baja", "numero_baja"), ("Fecha", "fecha_baja"),
                ("Estado", "estado"), ("Motivo", "motivo_baja__nombre"),
            ]
            exp = exportar_reporte(formato, "Reporte de bajas", cols, items)
            if exp:
                return exp
        return Response({"desde": desde, "hasta": hasta, "items": items})


class ReporteAjustesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        desde, hasta = _rango(request)
        qs = AjusteInventario.objects.filter(
            fecha_ajuste__date__gte=desde, fecha_ajuste__date__lte=hasta
        )
        estado = request.query_params.get("estado")
        tipo = request.query_params.get("tipo")
        if estado:
            qs = qs.filter(estado=estado)
        if tipo:
            qs = qs.filter(tipo_ajuste=tipo)
        items = list(
            qs.values("id", "fecha_ajuste", "tipo_ajuste", "estado", "motivo")
        )
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("#", "id"), ("Fecha", "fecha_ajuste"), ("Tipo", "tipo_ajuste"),
                ("Estado", "estado"), ("Motivo", "motivo"),
            ]
            exp = exportar_reporte(formato, "Reporte de ajustes", cols, items)
            if exp:
                return exp
        return Response({"desde": desde, "hasta": hasta, "items": items})


class ReporteInventarioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tipo = request.query_params.get("tipo")
        categoria = request.query_params.get("categoria")
        qs = InventarioProducto.objects.select_related("producto", "producto__categoria")
        if tipo:
            qs = qs.filter(producto__tipo_producto=tipo)
        if categoria:
            qs = qs.filter(producto__categoria_id=categoria)
        items = []
        valor_total = 0
        for inv in qs:
            valor = float(inv.cantidad_actual) * float(inv.costo_referencial)
            valor_total += valor
            items.append({
                "codigo": inv.producto.codigo_producto,
                "nombre": inv.producto.nombre,
                "tipo": inv.producto.tipo_producto,
                "cantidad": inv.cantidad_actual,
                "costo_referencial": inv.costo_referencial,
                "valor": round(valor, 4),
            })
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("Codigo", "codigo"), ("Producto", "nombre"), ("Tipo", "tipo"),
                ("Cantidad", "cantidad"), ("Costo", "costo_referencial"), ("Valor", "valor"),
            ]
            exp = exportar_reporte(
                formato, "Reporte de inventario", cols, items,
                {"Valor total": round(valor_total, 2)},
            )
            if exp:
                return exp
        return Response({"valor_total": round(valor_total, 4), "items": items})


class ReporteAlertasView(APIView):
    """
    Detecta stock critico: productos cuyo stock <= umbral (stock_minimo si esta
    definido, si no STOCK_CRITICO_DEFAULT=5).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Evalua TODOS los productos activos calculando el stock desde las capas
        # (igual que el catalogo), no solo los que tienen fila InventarioProducto.
        tipo = request.query_params.get("tipo")
        stock_sub = (
            CapaCosto.objects.filter(producto=OuterRef("pk"), estado="ACTIVA")
            .values("producto")
            .annotate(t=Sum("cantidad_disponible"))
            .values("t")
        )
        qs = Producto.objects.filter(estado="ACTIVO").annotate(
            stock=Coalesce(
                Subquery(stock_sub, output_field=DecimalField(max_digits=14, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        if tipo:
            qs = qs.filter(tipo_producto=tipo)
        stock_critico = []
        for p in qs:
            minimo = p.stock_minimo or 0
            umbral = minimo if minimo > 0 else STOCK_CRITICO_DEFAULT
            if p.stock <= umbral:
                stock_critico.append(
                    {
                        "producto_id": p.id,
                        "codigo": p.codigo_producto,
                        "producto": p.nombre,
                        "tipo": p.tipo_producto,
                        "stock": p.stock,
                        "umbral": umbral,
                        "agotado": p.stock <= 0,
                    }
                )
        stock_critico.sort(key=lambda x: x["stock"])

        return Response(
            {
                "stock_critico": stock_critico,
                "resumen": {"stock_critico": len(stock_critico)},
            }
        )


class ReporteTrazabilidadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.auditoria.models import BitacoraOperacion

        desde, hasta = _rango(request)
        qs = BitacoraOperacion.objects.filter(
            fecha_operacion__date__gte=desde, fecha_operacion__date__lte=hasta
        ).select_related("usuario")
        modulo = request.query_params.get("modulo")
        if modulo:
            qs = qs.filter(modulo=modulo)
        items = list(
            qs.values("id", "modulo", "accion", "entidad", "id_entidad",
                      "usuario__username", "fecha_operacion")[:500]
        )
        formato = request.query_params.get("formato")
        if formato:
            cols = [
                ("Modulo", "modulo"), ("Accion", "accion"), ("Entidad", "entidad"),
                ("ID", "id_entidad"), ("Usuario", "usuario__username"),
                ("Fecha", "fecha_operacion"),
            ]
            exp = exportar_reporte(formato, "Reporte de trazabilidad", cols, items)
            if exp:
                return exp
        return Response({"desde": desde, "hasta": hasta, "items": items})
