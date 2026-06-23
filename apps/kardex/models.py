from django.db import models


class Periodo(models.Model):
    nombre = models.CharField(max_length=60)
    fecha_inicio = models.DateField(db_column="fechaInicio")
    fecha_fin = models.DateField(db_column="fechaFin")
    estado = models.CharField(max_length=20, default="ABIERTO")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "periodo"

    def __str__(self):
        return self.nombre


class SaldoPeriodo(models.Model):
    periodo = models.ForeignKey(
        Periodo, on_delete=models.CASCADE, db_column="idPeriodo"
    )
    producto = models.ForeignKey(
        "catalogos.Producto", on_delete=models.CASCADE, db_column="idProducto"
    )
    saldo_inicial_cantidad = models.DecimalField(
        db_column="saldoInicialCantidad", max_digits=12, decimal_places=2, default=0
    )
    saldo_inicial_valor = models.DecimalField(
        db_column="saldoInicialValor", max_digits=14, decimal_places=4, default=0
    )
    saldo_final_cantidad = models.DecimalField(
        db_column="saldoFinalCantidad", max_digits=12, decimal_places=2, default=0
    )
    saldo_final_valor = models.DecimalField(
        db_column="saldoFinalValor", max_digits=14, decimal_places=4, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saldo_periodo"
        unique_together = ("periodo", "producto")


class KardexGenerado(models.Model):
    producto = models.ForeignKey(
        "catalogos.Producto", on_delete=models.CASCADE, db_column="idProducto"
    )
    periodo = models.ForeignKey(
        Periodo, on_delete=models.SET_NULL, db_column="idPeriodo", null=True, blank=True
    )
    fecha_inicio = models.DateField(db_column="fechaInicio")
    fecha_fin = models.DateField(db_column="fechaFin")
    fecha_generacion = models.DateTimeField(
        db_column="fechaGeneracion", auto_now_add=True
    )
    saldo_inicial_cantidad = models.DecimalField(
        db_column="saldoInicialCantidad", max_digits=12, decimal_places=2, default=0
    )
    saldo_inicial_valor = models.DecimalField(
        db_column="saldoInicialValor", max_digits=14, decimal_places=4, default=0
    )
    saldo_final_cantidad = models.DecimalField(
        db_column="saldoFinalCantidad", max_digits=12, decimal_places=2, default=0
    )
    saldo_final_valor = models.DecimalField(
        db_column="saldoFinalValor", max_digits=14, decimal_places=4, default=0
    )
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
        db_table = "kardex_generado"


class DetalleKardex(models.Model):
    kardex = models.ForeignKey(
        KardexGenerado,
        on_delete=models.CASCADE,
        db_column="idKardexGenerado",
        related_name="detalles",
    )
    movimiento = models.ForeignKey(
        "inventario.MovimientoInventario",
        on_delete=models.SET_NULL,
        db_column="idMovimientoInventario",
        null=True,
        blank=True,
    )
    fecha = models.DateField()
    concepto = models.CharField(max_length=120)
    tipo_movimiento = models.CharField(db_column="tipoMovimiento", max_length=40)
    costo_unitario_referencial = models.DecimalField(
        db_column="costoUnitarioReferencial", max_digits=14, decimal_places=4, default=0
    )
    entrada_cantidad = models.DecimalField(
        db_column="entradaCantidad", max_digits=12, decimal_places=2, default=0
    )
    entrada_valor = models.DecimalField(
        db_column="entradaValor", max_digits=14, decimal_places=4, default=0
    )
    salida_cantidad = models.DecimalField(
        db_column="salidaCantidad", max_digits=12, decimal_places=2, default=0
    )
    salida_valor = models.DecimalField(
        db_column="salidaValor", max_digits=14, decimal_places=4, default=0
    )
    saldo_cantidad = models.DecimalField(
        db_column="saldoCantidad", max_digits=12, decimal_places=2, default=0
    )
    saldo_valor = models.DecimalField(
        db_column="saldoValor", max_digits=14, decimal_places=4, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_kardex"
        ordering = ["fecha", "id"]
