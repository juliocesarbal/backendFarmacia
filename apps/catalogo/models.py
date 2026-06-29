"""Catalogos base: categorias, unidades de medida y productos."""
from django.db import models


class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=20, default="ACTIVO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "categoria_producto"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=80)
    abreviatura = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, default="ACTIVO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "unidad_medida"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"


class Producto(models.Model):
    TIPOS = [
        ("MEDICAMENTO", "Medicamento"),
        ("MATERIAL", "Material"),
        ("INSUMO", "Insumo"),
        ("ESPECIAL", "Producto especial"),
    ]
    ESTADOS = [("ACTIVO", "Activo"), ("ANULADO", "Anulado")]

    codigo_producto = models.CharField(
        db_column="codigoProducto", max_length=60, unique=True
    )
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    tipo_producto = models.CharField(
        db_column="tipoProducto", max_length=40, choices=TIPOS, default="MEDICAMENTO"
    )
    precio_venta = models.DecimalField(
        db_column="precioVenta", max_digits=14, decimal_places=4, default=0
    )
    costo_referencial = models.DecimalField(
        db_column="costoReferencial", max_digits=14, decimal_places=4, default=0
    )
    stock_minimo = models.DecimalField(
        db_column="stockMinimo", max_digits=12, decimal_places=2, default=0
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="ACTIVO")
    fecha_creacion = models.DateTimeField(db_column="fechaCreacion", auto_now_add=True)
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.PROTECT,
        db_column="idCategoriaProducto",
        related_name="productos",
    )
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        db_column="idUnidadMedida",
        related_name="productos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"

    @property
    def stock_actual(self):
        """Stock = suma de cantidades disponibles en capas activas (RN-01)."""
        from django.db.models import Sum

        total = self.capas_costo.filter(estado="ACTIVA").aggregate(
            s=Sum("cantidad_disponible")
        )["s"]
        return total or 0
