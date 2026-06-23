from django.db import models


class AjusteInventario(models.Model):
    TIPOS = [("POSITIVO", "Positivo"), ("NEGATIVO", "Negativo")]
    ESTADOS = [("BORRADOR", "Borrador"), ("CONFIRMADO", "Confirmado")]

    numero_ajuste = models.CharField(
        db_column="numeroAjuste", max_length=60, blank=True
    )
    fecha_ajuste = models.DateTimeField(db_column="fechaAjuste", auto_now_add=True)
    tipo_ajuste = models.CharField(db_column="tipoAjuste", max_length=20, choices=TIPOS)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    motivo = models.CharField(max_length=120, blank=True)
    observacion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        "users.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="ajustes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ajuste_inventario"
        ordering = ["-fecha_ajuste", "-id"]


class DetalleAjuste(models.Model):
    ajuste = models.ForeignKey(
        AjusteInventario,
        on_delete=models.CASCADE,
        db_column="idAjusteInventario",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "catalogos.Producto", on_delete=models.PROTECT, db_column="idProducto"
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(
        db_column="costoUnitario", max_digits=14, decimal_places=4, default=0
    )
    costo_total = models.DecimalField(
        db_column="costoTotal", max_digits=14, decimal_places=4, default=0
    )
    observacion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_ajuste"
