"""
Servicios de inventario: el nucleo del sistema.

Implementa:
  - consumir_fifo  (RN-04 / PEPS-FIFO)
  - crear_capa     (RN-02, entrada)
  - registrar_movimiento (+ recalculo de InventarioProducto)
  - restaurar_capas (RN-06, anulacion)

Toda salida valora su costo a partir de las capas historicas, nunca con el
ultimo precio de compra. Las operaciones que afectan inventario deben llamarse
dentro de transaction.atomic() (RN-08), responsabilidad de quien invoca.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.auditoria.services import registrar_bitacora
from apps.catalogo.models import Producto

from .models import (
    AjusteInventario,
    Baja,
    CapaCosto,
    ConsumoCapaCosto,
    InventarioProducto,
    MovimientoInventario,
)


class StockInsuficienteError(Exception):
    """Se solicita mas cantidad de la disponible en capas activas."""


def stock_disponible(producto_id) -> Decimal:
    """RN-01: stock = suma de cantidad_disponible en capas activas."""
    total = CapaCosto.objects.filter(
        producto_id=producto_id, estado="ACTIVA"
    ).aggregate(s=Sum("cantidad_disponible"))["s"]
    return total or Decimal("0")


def crear_capa(producto, cantidad, costo_unitario, fecha_ingreso, origen):
    """RN-02: una entrada crea una nueva capa de costo independiente."""
    return CapaCosto.objects.create(
        producto=producto,
        cantidad_inicial=cantidad,
        cantidad_disponible=cantidad,
        costo_unitario=costo_unitario,
        fecha_ingreso=fecha_ingreso,
        origen=origen,
    )


def consumir_fifo(producto_id, cantidad_solicitada):
    """
    RN-04: consume las capas mas antiguas primero. Devuelve la lista de
    consumos [{capa, cantidad, costo_unitario, costo_total}] sin persistir el
    ConsumoCapaCosto (eso lo hace registrar_movimiento, que conoce el
    movimiento). Lanza StockInsuficienteError si no alcanza.
    """
    pendiente = Decimal(str(cantidad_solicitada))
    consumos = []
    capas = (
        CapaCosto.objects.select_for_update()
        .filter(producto_id=producto_id, estado="ACTIVA", cantidad_disponible__gt=0)
        .order_by("fecha_ingreso", "id")
    )

    for capa in capas:
        if pendiente <= 0:
            break
        cantidad = min(capa.cantidad_disponible, pendiente)
        consumos.append(
            {
                "capa": capa,
                "cantidad": cantidad,
                "costo_unitario": capa.costo_unitario,
                "costo_total": (cantidad * capa.costo_unitario).quantize(Decimal("0.0001")),
            }
        )
        capa.cantidad_disponible -= cantidad
        if capa.cantidad_disponible <= 0:
            capa.estado = "AGOTADA"
        capa.save(update_fields=["cantidad_disponible", "estado"])
        pendiente -= cantidad

    if pendiente > 0:
        raise StockInsuficienteError(
            f"Stock insuficiente para el producto {producto_id}: "
            f"faltan {pendiente} unidades."
        )
    return consumos


def _recalcular_inventario(producto):
    """Actualiza el cache InventarioProducto desde las capas activas."""
    capas = CapaCosto.objects.filter(producto=producto, estado="ACTIVA")
    cantidad = capas.aggregate(s=Sum("cantidad_disponible"))["s"] or Decimal("0")
    valor = sum(
        (c.cantidad_disponible * c.costo_unitario for c in capas), Decimal("0")
    )
    costo_ref = (valor / cantidad).quantize(Decimal("0.0001")) if cantidad else Decimal("0")
    inv, _ = InventarioProducto.objects.get_or_create(producto=producto)
    inv.cantidad_actual = cantidad
    inv.costo_referencial = costo_ref
    inv.save()
    return inv


def registrar_entrada(
    producto, cantidad, costo_unitario, *, tipo, referencia_tipo, referencia_id,
    usuario=None, fecha_ingreso, origen, observacion="", crear_capa_nueva=True,
):
    """
    Registra un movimiento de ENTRADA y, si corresponde, crea su capa de costo.
    Devuelve el MovimientoInventario.
    """
    if crear_capa_nueva:
        crear_capa(producto, cantidad, costo_unitario, fecha_ingreso, origen)

    valor = (Decimal(str(cantidad)) * Decimal(str(costo_unitario))).quantize(Decimal("0.0001"))
    mov = MovimientoInventario.objects.create(
        producto=producto,
        sentido="ENTRADA",
        tipo_movimiento=tipo,
        cantidad=cantidad,
        costo_unitario_aplicado=costo_unitario,
        valor_movimiento=valor,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario=usuario,
        observacion=observacion,
    )
    _recalcular_inventario(producto)
    return mov


def registrar_salida(
    producto, cantidad, *, tipo, referencia_tipo, referencia_id,
    usuario=None, motivo="", observacion="",
):
    """
    Registra un movimiento de SALIDA valorado por FIFO (consume las capas mas
    antiguas primero). Persiste los ConsumoCapaCosto. Devuelve (movimiento,
    costo_total_salida).
    """
    consumos = consumir_fifo(producto.id, cantidad)
    costo_total = sum((c["costo_total"] for c in consumos), Decimal("0"))
    costo_unitario_prom = (
        (costo_total / Decimal(str(cantidad))).quantize(Decimal("0.0001"))
        if Decimal(str(cantidad)) else Decimal("0")
    )

    mov = MovimientoInventario.objects.create(
        producto=producto,
        sentido="SALIDA",
        tipo_movimiento=tipo,
        cantidad=cantidad,
        costo_unitario_aplicado=costo_unitario_prom,
        valor_movimiento=costo_total,
        motivo=motivo,
        observacion=observacion,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario=usuario,
    )
    for c in consumos:
        ConsumoCapaCosto.objects.create(
            movimiento=mov,
            capa=c["capa"],
            cantidad_consumida=c["cantidad"],
            costo_unitario=c["costo_unitario"],
            valor_consumido=c["costo_total"],
        )
    _recalcular_inventario(producto)
    return mov, costo_total


def restaurar_capas(movimiento_salida, *, usuario=None, motivo="Anulacion"):
    """
    RN-06: revierte un movimiento de salida devolviendo a cada capa original la
    cantidad consumida y registrando un movimiento reverso de ENTRADA.
    """
    consumos = movimiento_salida.consumos.select_related("capa")
    cantidad_total = Decimal("0")
    valor_total = Decimal("0")
    for consumo in consumos:
        capa = consumo.capa
        capa.cantidad_disponible += consumo.cantidad_consumida
        if capa.estado == "AGOTADA" and capa.cantidad_disponible > 0:
            capa.estado = "ACTIVA"
        capa.save(update_fields=["cantidad_disponible", "estado"])
        cantidad_total += consumo.cantidad_consumida
        valor_total += consumo.valor_consumido

    producto = movimiento_salida.producto
    reverso = MovimientoInventario.objects.create(
        producto=producto,
        sentido="ENTRADA",
        tipo_movimiento="ANULACION",
        cantidad=cantidad_total,
        costo_unitario_aplicado=(
            (valor_total / cantidad_total).quantize(Decimal("0.0001"))
            if cantidad_total else Decimal("0")
        ),
        valor_movimiento=valor_total,
        motivo=motivo,
        referencia_tipo="MOVIMIENTO",
        referencia_id=movimiento_salida.id,
        usuario=usuario,
    )
    _recalcular_inventario(producto)
    return reverso


# ---------------------------------------------------------------------------
# Bajas (RN-03): confirmar consume capas por FIFO
# ---------------------------------------------------------------------------
class BajaError(Exception):
    pass


@transaction.atomic
def confirmar_baja(baja_id, usuario=None):
    baja = Baja.objects.select_for_update().get(pk=baja_id)
    if baja.estado != "BORRADOR":
        raise BajaError(f"La baja ya esta {baja.estado}.")

    detalles = baja.detalles.select_related("producto")
    if not detalles.exists():
        raise BajaError("La baja no tiene detalles.")

    # Validacion de stock por linea (FIFO global)
    for det in detalles:
        if stock_disponible(det.producto_id) < det.cantidad:
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


# ---------------------------------------------------------------------------
# Ajustes: POSITIVO crea capa (RN-02); NEGATIVO consume FIFO (RN-03/RN-04)
# ---------------------------------------------------------------------------
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
