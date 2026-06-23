from django.db import models


class Venta(models.Model):
    ESTADOS = [
        ("BORRADOR", "Borrador"),
        ("CONFIRMADA", "Confirmada"),
        ("ANULADA", "Anulada"),
    ]
    TIPOS = [("VENTA", "Venta"), ("DISPENSACION", "Dispensacion")]

    numero_boleta = models.CharField(db_column="numeroBoleta", max_length=60, blank=True)
    fecha_venta = models.DateTimeField(db_column="fechaVenta", auto_now_add=True)
    tipo_venta = models.CharField(
        db_column="tipoVenta", max_length=40, choices=TIPOS, default="VENTA"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    total_venta = models.DecimalField(
        db_column="totalVenta", max_digits=14, decimal_places=4, default=0
    )
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        "users.Usuario",
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
        "catalogos.Producto", on_delete=models.PROTECT, db_column="idProducto"
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
        "users.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "anulacion_boleta"
