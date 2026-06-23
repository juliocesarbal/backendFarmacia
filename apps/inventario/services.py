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

from django.db.models import Sum

from apps.catalogos.models import Producto

from .models import (
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


def crear_capa(
    producto, cantidad, costo_unitario, fecha_ingreso, origen, origen_id=None,
    numero_lote="", fecha_vencimiento=None,
):
    """RN-02: una entrada crea una nueva capa de costo independiente."""
    return CapaCosto.objects.create(
        producto=producto,
        cantidad_inicial=cantidad,
        cantidad_disponible=cantidad,
        costo_unitario=costo_unitario,
        fecha_ingreso=fecha_ingreso,
        origen=origen,
        origen_id=origen_id,
        numero_lote=numero_lote or "",
        fecha_vencimiento=fecha_vencimiento,
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


def consumir_de_capa(capa_id, cantidad_solicitada):
    """
    Consume una cantidad de UNA capa concreta (baja/ajuste de un lote especifico,
    p.ej. baja por vencimiento). No usa FIFO. Lanza StockInsuficienteError si la
    capa no tiene suficiente disponible.
    """
    pendiente = Decimal(str(cantidad_solicitada))
    capa = CapaCosto.objects.select_for_update().get(pk=capa_id)
    if capa.estado != "ACTIVA" or capa.cantidad_disponible < pendiente:
        raise StockInsuficienteError(
            f"El lote {capa_id} no tiene {pendiente} unidades disponibles."
        )
    consumo = [
        {
            "capa": capa,
            "cantidad": pendiente,
            "costo_unitario": capa.costo_unitario,
            "costo_total": (pendiente * capa.costo_unitario).quantize(Decimal("0.0001")),
        }
    ]
    capa.cantidad_disponible -= pendiente
    if capa.cantidad_disponible <= 0:
        capa.estado = "AGOTADA"
    capa.save(update_fields=["cantidad_disponible", "estado"])
    return consumo


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
    numero_lote="", fecha_vencimiento=None,
):
    """
    Registra un movimiento de ENTRADA y, si corresponde, crea su capa de costo.
    Devuelve el MovimientoInventario.
    """
    if crear_capa_nueva:
        crear_capa(
            producto, cantidad, costo_unitario, fecha_ingreso, origen, referencia_id,
            numero_lote=numero_lote, fecha_vencimiento=fecha_vencimiento,
        )

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
    usuario=None, motivo="", observacion="", capa=None,
):
    """
    Registra un movimiento de SALIDA. Por defecto valora por FIFO; si se pasa
    `capa` (id o instancia) consume solo de ese lote (baja por vencimiento, etc.).
    Persiste los ConsumoCapaCosto. Devuelve (movimiento, costo_total_salida).
    """
    if capa is not None:
        capa_id = capa.id if hasattr(capa, "id") else capa
        consumos = consumir_de_capa(capa_id, cantidad)
    else:
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
