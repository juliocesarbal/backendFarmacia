"""Inventario, capas de costo y movimientos (nucleo del Kardex valorado)."""
from django.db import models
from django.utils import timezone


class CapaCosto(models.Model):
    """
    Ingreso diferenciado: cada compra/ajuste positivo/importacion crea una capa
    con su costo unitario propio. El FIFO consume primero las mas antiguas.
    """

    ORIGENES = [
        ("COMPRA", "Compra"),
        ("AJUSTE", "Ajuste positivo"),
        ("IMPORTACION", "Importacion"),
    ]
    ESTADOS = [("ACTIVA", "Activa"), ("AGOTADA", "Agotada")]

    producto = models.ForeignKey(
        "catalogos.Producto",
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="capas_costo",
    )
    cantidad_inicial = models.DecimalField(
        db_column="cantidadInicial", max_digits=12, decimal_places=2
    )
    cantidad_disponible = models.DecimalField(
        db_column="cantidadDisponible", max_digits=12, decimal_places=2
    )
    costo_unitario = models.DecimalField(
        db_column="costoUnitario", max_digits=14, decimal_places=4
    )
    fecha_ingreso = models.DateField(db_column="fechaIngreso")
    numero_lote = models.CharField(
        db_column="numeroLote", max_length=60, blank=True, default=""
    )
    fecha_vencimiento = models.DateField(
        db_column="fechaVencimiento", null=True, blank=True
    )
    origen = models.CharField(max_length=40, choices=ORIGENES)
    origen_id = models.IntegerField(db_column="origenId", null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="ACTIVA")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "capa_costo"
        ordering = ["fecha_ingreso", "id"]  # orden FIFO

    def __str__(self):
        return f"Capa {self.id} {self.producto_id} disp={self.cantidad_disponible}@{self.costo_unitario}"


class MovimientoInventario(models.Model):
    """Toda entrada o salida de inventario; alimenta el Kardex."""

    SENTIDOS = [("ENTRADA", "Entrada"), ("SALIDA", "Salida")]
    TIPOS = [
        ("COMPRA", "Compra"),
        ("VENTA", "Venta"),
        ("BAJA", "Baja"),
        ("AJUSTE_POSITIVO", "Ajuste positivo"),
        ("AJUSTE_NEGATIVO", "Ajuste negativo"),
        ("ANULACION", "Anulacion"),
        ("IMPORTACION", "Importacion"),
    ]

    producto = models.ForeignKey(
        "catalogos.Producto",
        on_delete=models.PROTECT,
        db_column="idProducto",
        related_name="movimientos",
    )
    fecha_movimiento = models.DateTimeField(
        db_column="fechaMovimiento", default=timezone.now
    )
    sentido = models.CharField(max_length=20, choices=SENTIDOS)
    tipo_movimiento = models.CharField(
        db_column="tipoMovimiento", max_length=40, choices=TIPOS
    )
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario_aplicado = models.DecimalField(
        db_column="costoUnitarioAplicado", max_digits=14, decimal_places=4, default=0
    )
    valor_movimiento = models.DecimalField(
        db_column="valorMovimiento", max_digits=14, decimal_places=4, default=0
    )
    motivo = models.CharField(max_length=120, blank=True)
    observacion = models.TextField(blank=True)
    referencia_tipo = models.CharField(
        db_column="referenciaTipo", max_length=40, blank=True
    )
    referencia_id = models.IntegerField(
        db_column="referenciaId", null=True, blank=True
    )
    usuario = models.ForeignKey(
        "users.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="movimientos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "movimiento_inventario"
        ordering = ["fecha_movimiento", "id"]
        indexes = [
            models.Index(fields=["fecha_movimiento"]),
            models.Index(fields=["producto", "fecha_movimiento"]),
        ]


class ConsumoCapaCosto(models.Model):
    """Detalle de que capas consumio un movimiento de salida (FIFO)."""

    movimiento = models.ForeignKey(
        MovimientoInventario,
        on_delete=models.CASCADE,
        db_column="idMovimientoInventario",
        related_name="consumos",
    )
    capa = models.ForeignKey(
        CapaCosto,
        on_delete=models.PROTECT,
        db_column="idCapaCosto",
        related_name="consumos",
    )
    cantidad_consumida = models.DecimalField(
        db_column="cantidadConsumida", max_digits=12, decimal_places=2
    )
    costo_unitario = models.DecimalField(
        db_column="costoUnitario", max_digits=14, decimal_places=4
    )
    valor_consumido = models.DecimalField(
        db_column="valorConsumido", max_digits=14, decimal_places=4
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "consumo_capa_costo"


class InventarioProducto(models.Model):
    """Cache de stock actual por producto (se recalcula desde capas)."""

    producto = models.OneToOneField(
        "catalogos.Producto",
        on_delete=models.CASCADE,
        db_column="idProducto",
        related_name="inventario",
    )
    cantidad_actual = models.DecimalField(
        db_column="cantidadActual", max_digits=12, decimal_places=2, default=0
    )
    costo_referencial = models.DecimalField(
        db_column="costoReferencial", max_digits=14, decimal_places=4, default=0
    )
    fecha_actualizacion = models.DateTimeField(
        db_column="fechaActualizacion", auto_now=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "inventario_producto"
        ordering = ["producto__nombre"]
