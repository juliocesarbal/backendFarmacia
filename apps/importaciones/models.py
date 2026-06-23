from django.db import models


class ImportacionArchivo(models.Model):
    TIPOS = [
        ("INVENTARIO_INICIAL", "Inventario inicial"),
        ("COMPRAS", "Compras"),
        ("VENTAS", "Ventas"),
        ("BAJAS", "Bajas"),
    ]
    ESTADOS = [
        ("PENDIENTE", "Pendiente"),
        ("VALIDADO", "Validado"),
        ("CONFIRMADO", "Confirmado"),
        ("ERROR", "Error"),
    ]

    tipo_importacion = models.CharField(
        db_column="tipoImportacion", max_length=40, choices=TIPOS
    )
    nombre_archivo = models.CharField(db_column="nombreArchivo", max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="PENDIENTE")
    total_registros = models.IntegerField(db_column="totalRegistros", default=0)
    registros_validos = models.IntegerField(db_column="registrosValidos", default=0)
    registros_observados = models.IntegerField(
        db_column="registrosObservados", default=0
    )
    fecha_importacion = models.DateTimeField(
        db_column="fechaImportacion", auto_now_add=True
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
        db_table = "importacion_archivo"
        ordering = ["-fecha_importacion", "-id"]


class DetalleImportacion(models.Model):
    importacion = models.ForeignKey(
        ImportacionArchivo,
        on_delete=models.CASCADE,
        db_column="idImportacionArchivo",
        related_name="detalles",
    )
    numero_fila = models.IntegerField(db_column="numeroFila")
    datos_originales = models.JSONField(db_column="datosOriginales")
    estado_fila = models.CharField(db_column="estadoFila", max_length=20)
    mensaje_error = models.TextField(db_column="mensajeError", blank=True)
    referencia_creada_tipo = models.CharField(
        db_column="referenciaCreadaTipo", max_length=40, blank=True
    )
    referencia_creada_id = models.IntegerField(
        db_column="referenciaCreadaId", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_importacion"


class LogImportacion(models.Model):
    importacion = models.ForeignKey(
        ImportacionArchivo,
        on_delete=models.CASCADE,
        db_column="idImportacionArchivo",
        related_name="logs",
    )
    fila = models.IntegerField()
    campo = models.CharField(max_length=80, blank=True)
    valor = models.CharField(max_length=255, blank=True)
    tipo_error = models.CharField(db_column="tipoError", max_length=60)
    descripcion = models.TextField(blank=True)
    procesado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "log_importacion"
