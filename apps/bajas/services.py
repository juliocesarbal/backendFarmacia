"""Servicio de bajas: confirmar consume capas por FIFO (RN-03)."""
from decimal import Decimal

from django.db import transaction

from apps.auditoria.services import registrar_bitacora
from apps.inventario.services import (
    StockInsuficienteError,
    registrar_salida,
    stock_disponible,
)

from .models import Baja


class BajaError(Exception):
    pass


@transaction.atomic
def confirmar_baja(baja_id, usuario=None):
    baja = Baja.objects.select_for_update().get(pk=baja_id)
    if baja.estado != "BORRADOR":
        raise BajaError(f"La baja ya esta {baja.estado}.")

    detalles = baja.detalles.select_related("producto", "capa")
    if not detalles.exists():
        raise BajaError("La baja no tiene detalles.")

    # Validacion: si se eligio un lote, validar contra ese lote; si no, FIFO global
    for det in detalles:
        if det.capa_id:
            if det.capa.producto_id != det.producto_id:
                raise BajaError(
                    f"El lote seleccionado no corresponde a {det.producto.nombre}."
                )
            if det.capa.cantidad_disponible < det.cantidad:
                raise BajaError(
                    f"El lote seleccionado de {det.producto.nombre} no tiene stock suficiente."
                )
        elif stock_disponible(det.producto_id) < det.cantidad:
            raise BajaError(f"Stock insuficiente para {det.producto.nombre}.")

    for det in detalles:
        try:
            _, costo_salida = registrar_salida(
                producto=det.producto,
                cantidad=det.cantidad,
                tipo="BAJA",
                referencia_tipo="BAJA",
                referencia_id=baja.id,
                usuario=usuario,
                motivo=baja.motivo_baja.nombre,
                capa=det.capa,  # None = FIFO
            )
        except StockInsuficienteError as e:
            raise BajaError(str(e))
        det.costo_total_baja = costo_salida
        det.save(update_fields=["costo_total_baja"])

    baja.estado = "CONFIRMADA"
    baja.save(update_fields=["estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="bajas",
        accion="CONFIRMAR",
        entidad="Baja",
        id_entidad=baja.id,
        valores_nuevos={"estado": "CONFIRMADA"},
    )
    return baja
