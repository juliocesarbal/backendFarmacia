"""
Servicio de ventas — flujo de CAJA FACULTATIVA (v3 §4, §16.6).

Flujo: venta ACTIVA/PENDIENTE_PAGO -> registrar_comprobante -> verificar_pago
(PAGADA) -> entregar (descuenta inventario por FIFO, ENTREGADA) -> anular.

Regla crítica: NO se descuenta stock al crear la venta ni al registrar el
comprobante; el descuento ocurre SOLO al entregar, con el pago ya verificado.
Todo atomico (RN-08); salidas valoradas por FIFO (RN-04).
"""
from decimal import Decimal

from django.db import transaction

from apps.auditoria.services import registrar_bitacora
from apps.inventario.models import MovimientoInventario
from apps.inventario.services import (
    StockInsuficienteError,
    registrar_salida,
    restaurar_capas,
    stock_disponible,
)

from .models import AnulacionBoleta, ComprobantePago, Venta


class VentaError(Exception):
    pass


@transaction.atomic
def registrar_comprobante(venta_id, datos, usuario=None):
    """Registra el comprobante de la caja facultativa (estado PENDIENTE)."""
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado != "ACTIVA":
        raise VentaError("La venta no esta activa.")
    if venta.estado_pago == "PAGADA":
        raise VentaError("La venta ya esta pagada.")

    comprobante = ComprobantePago.objects.create(
        venta=venta,
        numero_comprobante=datos.get("numero_comprobante", ""),
        monto_pagado=datos.get("monto_pagado") or venta.total_venta,
        observacion=datos.get("observacion", ""),
        usuario=usuario,
        estado_verificacion="PENDIENTE",
    )
    registrar_bitacora(
        usuario=usuario, modulo="ventas", accion="REGISTRAR_COMPROBANTE",
        entidad="Venta", id_entidad=venta.id,
        valores_nuevos={"comprobante": comprobante.id,
                        "monto": str(comprobante.monto_pagado)},
    )
    return venta


@transaction.atomic
def verificar_pago(venta_id, usuario=None):
    """Verifica el comprobante pendiente y marca la venta como PAGADA."""
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado != "ACTIVA":
        raise VentaError("La venta no esta activa.")
    if venta.estado_pago == "PAGADA":
        raise VentaError("La venta ya esta pagada.")

    comprobante = (
        venta.comprobantes.filter(estado_verificacion="PENDIENTE")
        .order_by("-id")
        .first()
    )
    if not comprobante:
        raise VentaError("No hay comprobante de pago registrado para verificar.")
    if comprobante.monto_pagado < venta.total_venta:
        raise VentaError("El monto del comprobante no cubre el total de la venta.")

    comprobante.estado_verificacion = "VERIFICADO"
    comprobante.save(update_fields=["estado_verificacion"])
    venta.estado_pago = "PAGADA"
    venta.save(update_fields=["estado_pago"])

    registrar_bitacora(
        usuario=usuario, modulo="ventas", accion="VERIFICAR_PAGO",
        entidad="Venta", id_entidad=venta.id,
        valores_nuevos={"estado_pago": "PAGADA"},
    )
    return venta


@transaction.atomic
def entregar_venta(venta_id, usuario=None):
    """
    Confirma la entrega SOLO si la venta esta PAGADA. Recien aqui se descuenta el
    inventario por FIFO y se guarda el costo de salida de cada detalle (RN-04).
    """
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado != "ACTIVA":
        raise VentaError("La venta no esta activa.")
    if venta.estado_pago != "PAGADA":
        raise VentaError("No se puede entregar: el pago no esta verificado.")
    if venta.estado_entrega == "ENTREGADA":
        raise VentaError("La venta ya fue entregada.")

    detalles = venta.detalles.select_related("producto")
    if not detalles.exists():
        raise VentaError("La venta no tiene detalles.")

    for det in detalles:
        if stock_disponible(det.producto_id) < det.cantidad:
            raise VentaError(f"Stock insuficiente para {det.producto.nombre}.")

    for det in detalles:
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
        det.save(update_fields=["costo_total_salida"])

    venta.estado_entrega = "ENTREGADA"
    venta.save(update_fields=["estado_entrega"])

    registrar_bitacora(
        usuario=usuario, modulo="ventas", accion="ENTREGAR",
        entidad="Venta", id_entidad=venta.id,
        valores_nuevos={"estado_entrega": "ENTREGADA"},
    )
    return venta


@transaction.atomic
def anular_venta(venta_id, motivo="", usuario=None):
    """
    Anula la venta. Si ya fue entregada (stock descontado), restaura las capas
    consumidas (RN-06). No elimina la venta.
    """
    venta = Venta.objects.select_for_update().get(pk=venta_id)
    if venta.estado == "ANULADA":
        raise VentaError("La venta ya esta anulada.")

    restauro = False
    if venta.estado_entrega == "ENTREGADA":
        movimientos = MovimientoInventario.objects.filter(
            referencia_tipo="VENTA", referencia_id=venta.id, sentido="SALIDA"
        )
        for mov in movimientos:
            restaurar_capas(mov, usuario=usuario, motivo=f"Anulacion venta {venta.id}")
        venta.estado_entrega = "NO_ENTREGADA"
        restauro = True

    AnulacionBoleta.objects.create(
        venta=venta, motivo=motivo, usuario=usuario, restaura_stock=restauro
    )
    venta.estado = "ANULADA"
    venta.save(update_fields=["estado", "estado_entrega"])

    registrar_bitacora(
        usuario=usuario, modulo="ventas", accion="ANULAR",
        entidad="Venta", id_entidad=venta.id,
        valores_anteriores={"estado": "ACTIVA"},
        valores_nuevos={"estado": "ANULADA", "motivo": motivo,
                        "restauro_stock": restauro},
    )
    return venta
