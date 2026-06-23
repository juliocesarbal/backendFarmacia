"""
Servicio de ajustes:
  - POSITIVO -> crea capa de costo + movimiento de entrada (RN-02)
  - NEGATIVO -> consume capas por FIFO + movimiento de salida (RN-03/RN-04)
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.auditoria.services import registrar_bitacora
from apps.inventario.services import (
    StockInsuficienteError,
    registrar_entrada,
    registrar_salida,
    stock_disponible,
)

from .models import AjusteInventario


class AjusteError(Exception):
    pass


@transaction.atomic
def confirmar_ajuste(ajuste_id, usuario=None):
    ajuste = AjusteInventario.objects.select_for_update().get(pk=ajuste_id)
    if ajuste.estado != "BORRADOR":
        raise AjusteError(f"El ajuste ya esta {ajuste.estado}.")

    detalles = ajuste.detalles.select_related("producto")
    if not detalles.exists():
        raise AjusteError("El ajuste no tiene detalles.")
    if not ajuste.motivo:
        raise AjusteError("Todo ajuste requiere motivo.")

    if ajuste.tipo_ajuste == "NEGATIVO":
        for det in detalles:
            if stock_disponible(det.producto_id) < det.cantidad:
                raise AjusteError(f"Stock insuficiente para {det.producto.nombre}.")

    for det in detalles:
        if ajuste.tipo_ajuste == "POSITIVO":
            costo = det.costo_unitario or det.producto.costo_referencial
            det.costo_total = (det.cantidad * costo).quantize(Decimal("0.0001"))
            registrar_entrada(
                producto=det.producto,
                cantidad=det.cantidad,
                costo_unitario=costo,
                tipo="AJUSTE_POSITIVO",
                referencia_tipo="AJUSTE",
                referencia_id=ajuste.id,
                usuario=usuario,
                fecha_ingreso=timezone.now().date(),
                origen="AJUSTE",
            )
        else:  # NEGATIVO
            try:
                _, costo_salida = registrar_salida(
                    producto=det.producto,
                    cantidad=det.cantidad,
                    tipo="AJUSTE_NEGATIVO",
                    referencia_tipo="AJUSTE",
                    referencia_id=ajuste.id,
                    usuario=usuario,
                    motivo=ajuste.motivo,
                )
            except StockInsuficienteError as e:
                raise AjusteError(str(e))
            det.costo_total = costo_salida
        det.save(update_fields=["costo_total"])

    ajuste.estado = "CONFIRMADO"
    ajuste.save(update_fields=["estado"])

    registrar_bitacora(
        usuario=usuario,
        modulo="ajustes",
        accion="CONFIRMAR",
        entidad="AjusteInventario",
        id_entidad=ajuste.id,
        valores_nuevos={"estado": "CONFIRMADO", "tipo": ajuste.tipo_ajuste},
    )
    return ajuste
