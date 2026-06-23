from django.db import models


class EjecucionKMeans(models.Model):
    numero_clusters = models.IntegerField(db_column="numeroClusters")
    periodo_inicio = models.DateField(db_column="periodoInicio")
    periodo_fin = models.DateField(db_column="periodoFin")
    variables_usadas = models.JSONField(db_column="variablesUsadas")
    estado = models.CharField(max_length=20, default="EJECUTADO")
    fecha_ejecucion = models.DateTimeField(
        db_column="fechaEjecucion", auto_now_add=True
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
        db_table = "ejecucion_k_means"
        ordering = ["-fecha_ejecucion", "-id"]


class ClusterKMeans(models.Model):
    ejecucion = models.ForeignKey(
        EjecucionKMeans,
        on_delete=models.CASCADE,
        db_column="idEjecucionKMeans",
        related_name="clusters",
    )
    numero_cluster = models.IntegerField(db_column="numeroCluster")
    nombre_cluster = models.CharField(db_column="nombreCluster", max_length=80)
    descripcion = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cluster_k_means"


class ProductoCluster(models.Model):
    cluster = models.ForeignKey(
        ClusterKMeans,
        on_delete=models.CASCADE,
        db_column="idClusterKMeans",
        related_name="productos",
    )
    producto = models.ForeignKey(
        "catalogos.Producto", on_delete=models.CASCADE, db_column="idProducto"
    )
    rotacion = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    consumo_total = models.DecimalField(
        db_column="consumoTotal", max_digits=14, decimal_places=4, default=0
    )
    costo_total = models.DecimalField(
        db_column="costoTotal", max_digits=14, decimal_places=4, default=0
    )
    stock_actual = models.DecimalField(
        db_column="stockActual", max_digits=12, decimal_places=2, default=0
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "producto_cluster"
