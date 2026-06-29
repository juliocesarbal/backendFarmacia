"""
Servicio de Kardex valorado.

Reconstruye el Kardex de un producto desde los MovimientoInventario en un rango
de fechas, arrastrando saldos (RN-05). Las salidas ya vienen valoradas por FIFO
desde inventario.services (valor_movimiento). El saldo final debe coincidir con
la suma de capas disponibles.
"""
from decimal import Decimal
from io import BytesIO

from django.db.models import Sum

from apps.catalogo.models import Producto
from apps.inventario.models import MovimientoInventario


def _saldo_inicial(producto_id, desde):
    """Saldo (cantidad, valor) acumulado antes de la fecha `desde`."""
    movs = MovimientoInventario.objects.filter(
        producto_id=producto_id, fecha_movimiento__date__lt=desde
    )
    cant = Decimal("0")
    valor = Decimal("0")
    for m in movs.order_by("fecha_movimiento", "id"):
        if m.sentido == "ENTRADA":
            cant += m.cantidad
            valor += m.valor_movimiento
        else:
            cant -= m.cantidad
            valor -= m.valor_movimiento
    return cant, valor


CONCEPTOS = {
    "COMPRA": "Compra",
    "VENTA": "Venta / Dispensacion",
    "BAJA": "Baja",
    "AJUSTE_POSITIVO": "Ajuste positivo",
    "AJUSTE_NEGATIVO": "Ajuste negativo",
    "ANULACION": "Anulacion (reverso)",
    "IMPORTACION": "Importacion",
}


def generar_kardex(producto_id, desde, hasta):
    """
    Devuelve un dict con cabecera y filas del Kardex valorado del producto en
    [desde, hasta]. No persiste; es la fuente para la consulta y los exports.
    """
    producto = Producto.objects.get(pk=producto_id)
    saldo_cant, saldo_valor = _saldo_inicial(producto_id, desde)

    movs = MovimientoInventario.objects.filter(
        producto_id=producto_id,
        fecha_movimiento__date__gte=desde,
        fecha_movimiento__date__lte=hasta,
    ).order_by("fecha_movimiento", "id")

    filas = []
    for m in movs:
        entrada_cant = entrada_valor = salida_cant = salida_valor = Decimal("0")
        if m.sentido == "ENTRADA":
            entrada_cant = m.cantidad
            entrada_valor = m.valor_movimiento
            saldo_cant += entrada_cant
            saldo_valor += entrada_valor
        else:
            salida_cant = m.cantidad
            salida_valor = m.valor_movimiento
            saldo_cant -= salida_cant
            saldo_valor -= salida_valor

        filas.append(
            {
                "fecha": m.fecha_movimiento.date().isoformat(),
                "tipo": m.tipo_movimiento,
                "concepto": CONCEPTOS.get(m.tipo_movimiento, m.tipo_movimiento),
                "documento": f"{m.referencia_tipo}-{m.referencia_id}"
                if m.referencia_id
                else "",
                "costo_unitario": m.costo_unitario_aplicado,
                "entrada_cantidad": entrada_cant,
                "entrada_valor": entrada_valor,
                "salida_cantidad": salida_cant,
                "salida_valor": salida_valor,
                "saldo_cantidad": saldo_cant,
                "saldo_valor": saldo_valor.quantize(Decimal("0.0001")),
            }
        )

    saldo_inicial_cant, saldo_inicial_valor = _saldo_inicial(producto_id, desde)
    return {
        "producto": {
            "id": producto.id,
            "codigo": producto.codigo_producto,
            "nombre": producto.nombre,
            "unidad": producto.unidad_medida.abreviatura,
        },
        "desde": desde.isoformat() if hasattr(desde, "isoformat") else str(desde),
        "hasta": hasta.isoformat() if hasattr(hasta, "isoformat") else str(hasta),
        "saldo_inicial_cantidad": saldo_inicial_cant,
        "saldo_inicial_valor": saldo_inicial_valor.quantize(Decimal("0.0001")),
        "saldo_final_cantidad": saldo_cant,
        "saldo_final_valor": saldo_valor.quantize(Decimal("0.0001")),
        "filas": filas,
    }


def verificar_saldo_vs_capas(producto_id):
    """Comprueba que el saldo del Kardex coincide con la suma de capas activas."""
    from apps.inventario.models import CapaCosto

    capas = CapaCosto.objects.filter(producto_id=producto_id, estado="ACTIVA")
    cant = capas.aggregate(s=Sum("cantidad_disponible"))["s"] or Decimal("0")
    valor = sum((c.cantidad_disponible * c.costo_unitario for c in capas), Decimal("0"))
    return cant, valor.quantize(Decimal("0.0001"))


# --------------------------------------------------------------------------
# Exportacion
# --------------------------------------------------------------------------
def exportar_excel(kardex):
    """Genera un .xlsx en memoria del Kardex y devuelve los bytes."""
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Kardex"
    p = kardex["producto"]
    ws.append([f"Kardex valorado - {p['codigo']} {p['nombre']}"])
    ws.append([f"Periodo: {kardex['desde']} a {kardex['hasta']}"])
    ws.append([])
    encabezados = [
        "Fecha", "Tipo", "Documento", "Concepto", "Costo Unit.",
        "Ent. Cant.", "Ent. Valor", "Sal. Cant.", "Sal. Valor",
        "Saldo Cant.", "Saldo Valor",
    ]
    ws.append(encabezados)
    ws.append([
        "", "", "", "SALDO INICIAL", "", "", "", "", "",
        float(kardex["saldo_inicial_cantidad"]),
        float(kardex["saldo_inicial_valor"]),
    ])
    for f in kardex["filas"]:
        ws.append([
            f["fecha"], f["tipo"], f["documento"], f["concepto"],
            float(f["costo_unitario"]),
            float(f["entrada_cantidad"]), float(f["entrada_valor"]),
            float(f["salida_cantidad"]), float(f["salida_valor"]),
            float(f["saldo_cantidad"]), float(f["saldo_valor"]),
        ])
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def exportar_pdf(kardex):
    """Genera un PDF del Kardex y devuelve los bytes (reportlab)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from reportlab.lib.styles import getSampleStyleSheet

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=1 * cm)
    styles = getSampleStyleSheet()
    p = kardex["producto"]
    elems = [
        Paragraph(f"Kardex valorado - {p['codigo']} {p['nombre']}", styles["Title"]),
        Paragraph(f"Periodo: {kardex['desde']} a {kardex['hasta']}", styles["Normal"]),
        Spacer(1, 0.4 * cm),
    ]
    data = [[
        "Fecha", "Concepto", "Doc", "C.Unit",
        "Ent.Cant", "Ent.Val", "Sal.Cant", "Sal.Val", "Saldo.Cant", "Saldo.Val",
    ]]
    data.append([
        "", "SALDO INICIAL", "", "", "", "", "", "",
        str(kardex["saldo_inicial_cantidad"]), str(kardex["saldo_inicial_valor"]),
    ])
    for f in kardex["filas"]:
        data.append([
            f["fecha"], f["concepto"], f["documento"], str(f["costo_unitario"]),
            str(f["entrada_cantidad"]), str(f["entrada_valor"]),
            str(f["salida_cantidad"]), str(f["salida_valor"]),
            str(f["saldo_cantidad"]), str(f["saldo_valor"]),
        ])
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    elems.append(tabla)
    doc.build(elems)
    return buf.getvalue()
