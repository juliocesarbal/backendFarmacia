"""
Servicio de importacion historica desde Excel.

Flujo: cargar -> validar por fila (vista previa) -> confirmar.
Solo se confirman las filas validas. El inventario inicial crea capas de costo
iniciales (RN-02).
"""
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Producto
from apps.inventario.services import (
    StockInsuficienteError,
    registrar_entrada,
    registrar_salida,
)

from .models import DetalleImportacion, ImportacionArchivo, LogImportacion

# Columnas esperadas por tipo (guia 5.9)
COLUMNAS = {
    "INVENTARIO_INICIAL": [
        "codigo_producto", "cantidad_inicial", "costo_unitario", "fecha_saldo",
    ],
    "COMPRAS": [
        "fecha", "codigo_producto", "cantidad", "costo_unitario",
    ],
    "VENTAS": ["fecha", "codigo_producto", "cantidad"],
    "BAJAS": ["fecha", "codigo_producto", "cantidad"],
}

# Tipos que generan ENTRADA (capa de costo) vs SALIDA (consumo FIFO)
ENTRADAS = {"INVENTARIO_INICIAL", "COMPRAS"}
SALIDAS = {"VENTAS": "VENTA", "BAJAS": "BAJA"}


def _aware(fecha):
    """date -> datetime aware a medianoche (para fechar movimientos historicos)."""
    return timezone.make_aware(datetime.combine(fecha, time()))


def _leer_excel(archivo):
    import openpyxl

    wb = openpyxl.load_workbook(archivo, data_only=True)
    ws = wb.active
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return [], []
    encabezados = [str(c).strip() if c is not None else "" for c in filas[0]]
    registros = []
    for fila in filas[1:]:
        if all(c is None for c in fila):
            continue
        registros.append(dict(zip(encabezados, fila)))
    return encabezados, registros


def _to_decimal(valor):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError):
        return None


@transaction.atomic
def cargar_y_validar(tipo, archivo, nombre_archivo, usuario=None):
    """Crea la importacion en estado VALIDADO con sus detalles y errores."""
    importacion = ImportacionArchivo.objects.create(
        tipo_importacion=tipo,
        nombre_archivo=nombre_archivo,
        estado="VALIDADO",
        usuario=usuario,
    )
    _, registros = _leer_excel(archivo)
    requeridas = COLUMNAS.get(tipo, [])

    validos = observados = 0
    for i, reg in enumerate(registros, start=2):
        errores = []
        # columnas requeridas
        for col in requeridas:
            if reg.get(col) in (None, ""):
                errores.append(f"Falta '{col}'")
        # producto existe
        codigo = reg.get("codigo_producto")
        producto = Producto.objects.filter(codigo_producto=codigo).first()
        if codigo and not producto:
            errores.append(f"Producto '{codigo}' no existe")
        # numeros
        if _to_decimal(reg.get("cantidad_inicial") or reg.get("cantidad")) is None:
            errores.append("Cantidad invalida")
        if tipo in ENTRADAS and _to_decimal(reg.get("costo_unitario")) is None:
            errores.append("Costo invalido")

        estado_fila = "ERROR" if errores else "VALIDO"
        if errores:
            observados += 1
            for e in errores:
                LogImportacion.objects.create(
                    importacion=importacion, fila=i, tipo_error="VALIDACION", descripcion=e
                )
        else:
            validos += 1

        DetalleImportacion.objects.create(
            importacion=importacion,
            numero_fila=i,
            datos_originales={k: (str(v) if v is not None else None) for k, v in reg.items()},
            estado_fila=estado_fila,
            mensaje_error="; ".join(errores),
        )

    importacion.total_registros = len(registros)
    importacion.registros_validos = validos
    importacion.registros_observados = observados
    importacion.save(update_fields=[
        "total_registros", "registros_validos", "registros_observados",
    ])
    return importacion


@transaction.atomic
def confirmar_importacion(importacion_id, usuario=None):
    """Procesa las filas validas creando capas/movimientos segun el tipo."""
    importacion = ImportacionArchivo.objects.select_for_update().get(pk=importacion_id)
    if importacion.estado == "CONFIRMADO":
        raise ValueError("La importacion ya fue confirmada.")

    tipo = importacion.tipo_importacion
    filas = importacion.detalles.filter(estado_fila="VALIDO")
    for det in filas:
        datos = det.datos_originales
        producto = Producto.objects.filter(
            codigo_producto=datos.get("codigo_producto")
        ).first()
        if not producto:
            continue
        cantidad = Decimal(str(datos.get("cantidad_inicial") or datos.get("cantidad")))
        fecha_txt = datos.get("fecha_saldo") or datos.get("fecha")
        try:
            fecha = date.fromisoformat(str(fecha_txt)[:10])
        except (ValueError, TypeError):
            fecha = timezone.now().date()

        if tipo in ENTRADAS:
            costo = Decimal(str(datos.get("costo_unitario")))
            mov = registrar_entrada(
                producto=producto, cantidad=cantidad, costo_unitario=costo,
                tipo="IMPORTACION", referencia_tipo="IMPORTACION",
                referencia_id=importacion.id, usuario=usuario,
                fecha_ingreso=fecha, origen="IMPORTACION",
            )
            mov.fecha_movimiento = _aware(fecha)
            mov.save(update_fields=["fecha_movimiento"])
            det.referencia_creada_tipo = "CAPA_COSTO"
            det.save(update_fields=["referencia_creada_tipo"])
        elif tipo in SALIDAS:
            try:
                mov, _ = registrar_salida(
                    producto=producto, cantidad=cantidad,
                    tipo=SALIDAS[tipo], referencia_tipo="IMPORTACION",
                    referencia_id=importacion.id, usuario=usuario,
                    motivo="Importacion historica",
                )
            except StockInsuficienteError as e:
                det.estado_fila = "ERROR"
                det.mensaje_error = str(e)
                det.save(update_fields=["estado_fila", "mensaje_error"])
                continue
            mov.fecha_movimiento = _aware(fecha)
            mov.save(update_fields=["fecha_movimiento"])
            det.referencia_creada_tipo = "MOVIMIENTO"
            det.save(update_fields=["referencia_creada_tipo"])

    importacion.estado = "CONFIRMADO"
    importacion.save(update_fields=["estado"])
    return importacion
