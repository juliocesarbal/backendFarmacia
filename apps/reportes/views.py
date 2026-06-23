"""Reportes consolidados (JSON) por rango de fechas."""
from datetime import date, timedelta

from django.db.models import Count, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bajas.models import Baja
from apps.compras.models import Compra
from apps.inventario.models import CapaCosto, InventarioProducto
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
        agg = qs.filter(estado="CONFIRMADA").aggregate(
            total=Sum("total_venta"), cantidad=Count("id")
        )
        items = list(
            qs.values("id", "numero_boleta", "fecha_venta", "tipo_venta",
                      "total_venta", "estado")
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
    HU10: detectar vencimientos y stock critico.
      - por_vencer: lotes (capas activas) que vencen dentro de `dias` (default 30)
        o ya vencidos.
      - stock_critico: productos cuyo stock <= umbral (stock_minimo si esta
        definido, si no STOCK_CRITICO_DEFAULT=5).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hoy = date.today()
        try:
            dias = int(request.query_params.get("dias", 30))
        except (TypeError, ValueError):
            dias = 30
        limite = hoy + timedelta(days=dias)

        # --- Lotes por vencer / vencidos ---
        capas = (
            CapaCosto.objects.filter(
                estado="ACTIVA",
                fecha_vencimiento__isnull=False,
                fecha_vencimiento__lte=limite,
            )
            .select_related("producto")
            .order_by("fecha_vencimiento", "id")
        )
        por_vencer = []
        for c in capas:
            dias_rest = (c.fecha_vencimiento - hoy).days
            por_vencer.append(
                {
                    "capa_id": c.id,
                    "producto_id": c.producto_id,
                    "codigo": c.producto.codigo_producto,
                    "producto": c.producto.nombre,
                    "lote": c.numero_lote or f"#{c.id}",
                    "fecha_vencimiento": c.fecha_vencimiento,
                    "dias_restantes": dias_rest,
                    "vencido": dias_rest < 0,
                    "cantidad_disponible": c.cantidad_disponible,
                    "costo_unitario": c.costo_unitario,
                }
            )

        # --- Stock critico ---
        tipo = request.query_params.get("tipo")
        inv = InventarioProducto.objects.select_related("producto").filter(
            producto__estado="ACTIVO"
        )
        if tipo:
            inv = inv.filter(producto__tipo_producto=tipo)
        stock_critico = []
        for i in inv:
            minimo = i.producto.stock_minimo or 0
            umbral = minimo if minimo > 0 else STOCK_CRITICO_DEFAULT
            if i.cantidad_actual <= umbral:
                stock_critico.append(
                    {
                        "producto_id": i.producto_id,
                        "codigo": i.producto.codigo_producto,
                        "producto": i.producto.nombre,
                        "tipo": i.producto.tipo_producto,
                        "stock": i.cantidad_actual,
                        "umbral": umbral,
                        "agotado": i.cantidad_actual <= 0,
                    }
                )
        stock_critico.sort(key=lambda x: x["stock"])

        return Response(
            {
                "dias": dias,
                "por_vencer": por_vencer,
                "stock_critico": stock_critico,
                "resumen": {
                    "por_vencer": len(por_vencer),
                    "vencidos": sum(1 for p in por_vencer if p["vencido"]),
                    "stock_critico": len(stock_critico),
                },
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
