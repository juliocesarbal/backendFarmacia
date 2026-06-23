from django.db import models


class MotivoBaja(models.Model):
    nombre = models.CharField(max_length=80)
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "motivo_baja"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Baja(models.Model):
    ESTADOS = [
        ("BORRADOR", "Borrador"),
        ("CONFIRMADA", "Confirmada"),
    ]

    numero_baja = models.CharField(db_column="numeroBaja", max_length=60, blank=True)
    fecha_baja = models.DateTimeField(db_column="fechaBaja", auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    observacion = models.TextField(blank=True)
    motivo_baja = models.ForeignKey(
        MotivoBaja, on_delete=models.PROTECT, db_column="idMotivoBaja"
    )
    usuario = models.ForeignKey(
        "users.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="bajas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "baja"
        ordering = ["-fecha_baja", "-id"]


class DetalleBaja(models.Model):
    baja = models.ForeignKey(
        Baja, on_delete=models.CASCADE, db_column="idBaja", related_name="detalles"
    )
    producto = models.ForeignKey(
        "catalogos.Producto", on_delete=models.PROTECT, db_column="idProducto"
    )
    capa = models.ForeignKey(
        "inventario.CapaCosto",
        on_delete=models.PROTECT,
        db_column="idCapaCosto",
        null=True,
        blank=True,
        help_text="Lote especifico a dar de baja; vacio = FIFO automatico",
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    costo_total_baja = models.DecimalField(
        db_column="costoTotalBaja", max_digits=14, decimal_places=4, default=0
    )
    observacion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_baja"
