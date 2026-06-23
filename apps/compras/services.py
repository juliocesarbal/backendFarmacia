"""Servicio de compras: confirmar genera entradas y capas de costo (RN-02)."""
from decimal import Decimal

from django.db import transaction

from apps.auditoria.services import registrar_bitacora
from apps.inventario.services import registrar_entrada

from .models import Compra


class CompraError(Exception):
    pass


@transaction.atomic
def confirmar_compra(compra_id, usuario=None):
    """
    Confirma una compra: por cada detalle genera un movimiento de entrada y una
    capa de costo independiente, y actualiza el total. Atomica (RN-08).
    """
    compra = Compra.objects.select_for_update().get(pk=compra_id)
    if compra.estado != "BORRADOR":
        raise CompraError(f"La compra ya esta {compra.estado}.")

    detalles = compra.detalles.select_related("producto").order_by("id")
    if not detalles.exists():
        raise CompraError("La compra no tiene detalles.")

    total = Decimal("0")
    for det in detalles:
        det.costo_total = (det.cantidad * det.costo_unitario).quantize(Decimal("0.0001"))
        det.save(update_fields=["costo_total"])
        total += det.costo_total

        registrar_entrada(
            producto=det.producto,
            cantidad=det.cantidad,
            costo_unitario=det.costo_unitario,
            tipo="COMPRA",
            referencia_tipo="COMPRA",
            referencia_id=compra.id,
            usuario=usuario,
            fecha_ingreso=compra.fecha_compra,
            origen="COMPRA",
            numero_lote=det.numero_lote,
            fecha_vencimiento=det.fecha_vencimiento,
        )

    compra.total_compra = total
    compra.estado = "CONFIRMADA"
    compra.save(update_fields=["total_compra", "estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="compras",
        accion="CONFIRMAR",
        entidad="Compra",
        id_entidad=compra.id,
        valores_nuevos={"estado": "CONFIRMADA", "total": str(total)},
    )
    return compra
