"""
Servicio de ventas: confirmar (FIFO) y anular (restaura capas).
RN-03, RN-04, RN-06. Todo atomico (RN-08).
"""
from decimal import Decimal

from django.db import transaction

from apps.auditoria.services import registrar_bitacora
from apps.inventario.services import (
    StockInsuficienteError,
    registrar_salida,
    restaurar_capas,
    stock_disponible,
)
from apps.inventario.models import MovimientoInventario

from .models import AnulacionBoleta, Venta


class VentaError(Exception):
    pass


@transaction.atomic
def confirmar_venta(venta_id, usuario=None):
    """
    Valida stock por linea, descuenta inventario por FIFO, guarda el costo total
    de salida de cada detalle y marca la venta como CONFIRMADA.
    """
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado != "BORRADOR":
        raise VentaError(f"La venta ya esta {venta.estado}.")

    detalles = venta.detalles.select_related("producto")
    if not detalles.exists():
        raise VentaError("La venta no tiene detalles.")

    # 1. Validar stock de todas las lineas antes de descontar
    for det in detalles:
        if stock_disponible(det.producto_id) < det.cantidad:
            raise VentaError(
                f"Stock insuficiente para {det.producto.nombre}."
            )

    total = Decimal("0")
    for det in detalles:
        det.subtotal = (det.cantidad * det.precio_unitario).quantize(Decimal("0.0001"))
        try:
            _, costo_salida = registrar_salida(
                producto=det.producto,
                cantidad=det.cantidad,
                tipo="VENTA",
                referencia_tipo="VENTA",
                referencia_id=venta.id,
                usuario=usuario,
            )
        except StockInsuficienteError as e:
            raise VentaError(str(e))
        det.costo_total_salida = costo_salida
        det.save(update_fields=["subtotal", "costo_total_salida"])
        total += det.subtotal

    venta.total_venta = total
    venta.estado = "CONFIRMADA"
    venta.save(update_fields=["total_venta", "estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="ventas",
        accion="CONFIRMAR",
        entidad="Venta",
        id_entidad=venta.id,
        valores_nuevos={"estado": "CONFIRMADA", "total": str(total)},
    )
    return venta


@transaction.atomic
def anular_venta(venta_id, motivo="", usuario=None):
    """
    RN-06: marca la venta ANULADA, crea registro de anulacion, genera
    movimientos reversos y restaura las capas consumidas. No elimina la venta.
    """
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado != "CONFIRMADA":
        raise VentaError("Solo se pueden anular ventas confirmadas.")

    movimientos = MovimientoInventario.objects.filter(
        referencia_tipo="VENTA", referencia_id=venta.id, sentido="SALIDA"
    )
    for mov in movimientos:
        restaurar_capas(mov, usuario=usuario, motivo=f"Anulacion venta {venta.id}")

    AnulacionBoleta.objects.create(
        venta=venta, motivo=motivo, usuario=usuario, restaura_stock=True
    )
    venta.estado = "ANULADA"
    venta.save(update_fields=["estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="ventas",
        accion="ANULAR",
        entidad="Venta",
        id_entidad=venta.id,
        valores_anteriores={"estado": "CONFIRMADA"},
        valores_nuevos={"estado": "ANULADA", "motivo": motivo},
    )
    return venta
