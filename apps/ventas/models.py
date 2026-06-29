from django.db import models


class Venta(models.Model):
    TIPOS = [("VENTA", "Venta"), ("DISPENSACION", "Dispensacion")]
    ESTADOS = [("ACTIVA", "Activa"), ("ANULADA", "Anulada")]
    ESTADOS_PAGO = [
        ("PENDIENTE_PAGO", "Pendiente de pago"),
        ("PAGADA", "Pagada"),
        ("RECHAZADA", "Rechazada"),
    ]
    ESTADOS_ENTREGA = [
        ("PENDIENTE_ENTREGA", "Pendiente de entrega"),
        ("ENTREGADA", "Entregada"),
        ("NO_ENTREGADA", "No entregada"),
    ]

    numero_boleta = models.CharField(db_column="numeroBoleta", max_length=60, blank=True)
    fecha_venta = models.DateTimeField(db_column="fechaVenta", auto_now_add=True)
    tipo_venta = models.CharField(
        db_column="tipoVenta", max_length=40, choices=TIPOS, default="VENTA"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="ACTIVA")
    estado_pago = models.CharField(
        db_column="estadoPago", max_length=20, choices=ESTADOS_PAGO,
        default="PENDIENTE_PAGO",
    )
    estado_entrega = models.CharField(
        db_column="estadoEntrega", max_length=20, choices=ESTADOS_ENTREGA,
        default="PENDIENTE_ENTREGA",
    )
    total_venta = models.DecimalField(
        db_column="totalVenta", max_digits=14, decimal_places=4, default=0
    )
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="ventas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "venta"
        ordering = ["-fecha_venta", "-id"]

    def __str__(self):
        return f"Venta {self.numero_boleta or self.id}"


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, db_column="idVenta", related_name="detalles"
    )
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.PROTECT, db_column="idProducto"
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    precio_unitario = models.DecimalField(
        db_column="precioUnitario", max_digits=14, decimal_places=4
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    costo_total_salida = models.DecimalField(
        db_column="costoTotalSalida", max_digits=14, decimal_places=4, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_venta"


class AnulacionBoleta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column="idVenta",
        related_name="anulaciones",
    )
    fecha_anulacion = models.DateTimeField(
        db_column="fechaAnulacion", auto_now_add=True
    )
    motivo = models.CharField(max_length=120, blank=True)
    observacion = models.TextField(blank=True)
    restaura_stock = models.BooleanField(db_column="restauraStock", default=True)
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "anulacion_boleta"


class ComprobantePago(models.Model):
    """Pago realizado en caja facultativa (flujo de venta v3 §4)."""

    ESTADOS_VERIFICACION = [
        ("PENDIENTE", "Pendiente"),
        ("VERIFICADO", "Verificado"),
        ("RECHAZADO", "Rechazado"),
    ]

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        db_column="idVenta",
        related_name="comprobantes",
    )
    numero_comprobante = models.CharField(
        db_column="numeroComprobante", max_length=60, blank=True
    )
    monto_pagado = models.DecimalField(
        db_column="montoPagado", max_digits=14, decimal_places=4, default=0
    )
    fecha_pago = models.DateTimeField(db_column="fechaPago", auto_now_add=True)
    estado_verificacion = models.CharField(
        db_column="estadoVerificacion", max_length=20,
        choices=ESTADOS_VERIFICACION, default="PENDIENTE",
    )
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "comprobante_pago"
        ordering = ["-fecha_pago", "-id"]
