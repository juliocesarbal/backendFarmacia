from django.db import models


class TipoOperacion(models.Model):
    codigo = models.CharField(max_length=60, unique=True)
    modulo = models.CharField(max_length=60)
    descripcion = models.CharField(max_length=255, blank=True)
    requiere_motivo = models.BooleanField(db_column="requiereMotivo", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tipo_operacion"

    def __str__(self):
        return self.codigo


class ParametroSistema(models.Model):
    clave = models.CharField(max_length=80, unique=True)
    valor = models.CharField(max_length=255)
    descripcion = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "parametro_sistema"

    def __str__(self):
        return self.clave


class BitacoraOperacion(models.Model):
    """Trazabilidad de operaciones criticas (RNF13/RF17)."""

    usuario = models.ForeignKey(
        "users.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
        related_name="operaciones",
    )
    tipo_operacion = models.ForeignKey(
        TipoOperacion,
        on_delete=models.SET_NULL,
        db_column="idTipoOperacion",
        null=True,
        blank=True,
    )
    modulo = models.CharField(max_length=60)
    accion = models.CharField(max_length=60)
    entidad = models.CharField(max_length=60)
    id_entidad = models.IntegerField(db_column="idEntidad", null=True, blank=True)
    valores_anteriores = models.JSONField(
        db_column="valoresAnteriores", null=True, blank=True
    )
    valores_nuevos = models.JSONField(
        db_column="valoresNuevos", null=True, blank=True
    )
    ip_origen = models.CharField(db_column="ipOrigen", max_length=60, blank=True)
    fecha_operacion = models.DateTimeField(
        db_column="fechaOperacion", auto_now_add=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "bitacora_operacion"
        ordering = ["-fecha_operacion", "-id"]
