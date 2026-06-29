from django.db import models


class Compra(models.Model):
    ESTADOS = [
        ("BORRADOR", "Borrador"),
        ("CONFIRMADA", "Confirmada"),
        ("ANULADA", "Anulada"),
    ]

    numero_orden = models.CharField(db_column="numeroOrden", max_length=60, blank=True)
    numero_factura = models.CharField(
        db_column="numeroFactura", max_length=60, blank=True
    )
    fecha_compra = models.DateField(db_column="fechaCompra")
    fecha_registro = models.DateTimeField(db_column="fechaRegistro", auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="BORRADOR")
    total_compra = models.DecimalField(
        db_column="totalCompra", max_digits=14, decimal_places=4, default=0
    )
    observacion = models.TextField(blank=True)
    proveedor = models.ForeignKey(
        "compras.Proveedor",
        on_delete=models.PROTECT,
        db_column="idProveedor",
        related_name="compras",
    )
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="compras",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compra"
        ordering = ["-fecha_compra", "-id"]

    def __str__(self):
        return f"Compra {self.id} - {self.proveedor}"


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra, on_delete=models.CASCADE, db_column="idCompra", related_name="detalles"
    )
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.PROTECT, db_column="idProducto"
    )
    unidad_medida = models.ForeignKey(
        "catalogo.UnidadMedida",
        on_delete=models.PROTECT,
        db_column="idUnidadMedida",
        null=True,
        blank=True,
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario = models.DecimalField(
        db_column="costoUnitario", max_digits=14, decimal_places=4
    )
    costo_total = models.DecimalField(
        db_column="costoTotal", max_digits=14, decimal_places=4, default=0
    )
    fecha_vencimiento = models.DateField(
        db_column="fechaVencimiento", null=True, blank=True
    )
    observacion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_compra"
        ordering = ["id"]


class Proveedor(models.Model):
    nombre = models.CharField(max_length=160)
    nit = models.CharField(max_length=40, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(max_length=254, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proveedor"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
