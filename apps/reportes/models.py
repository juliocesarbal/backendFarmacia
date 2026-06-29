from django.db import models


class Reporte(models.Model):
    nombre = models.CharField(max_length=120)
    tipo_reporte = models.CharField(db_column="tipoReporte", max_length=60)
    formato = models.CharField(max_length=20)  # EXCEL / PDF
    parametros = models.JSONField(null=True, blank=True)
    ruta_archivo = models.CharField(db_column="rutaArchivo", max_length=255, blank=True)
    fecha_generacion = models.DateTimeField(
        db_column="fechaGeneracion", auto_now_add=True
    )
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reporte"


class DocumentoExportado(models.Model):
    tipo_documento = models.CharField(db_column="tipoDocumento", max_length=60)
    nombre_archivo = models.CharField(db_column="nombreArchivo", max_length=255)
    ruta_archivo = models.CharField(db_column="rutaArchivo", max_length=255, blank=True)
    referencia_tipo = models.CharField(
        db_column="referenciaTipo", max_length=40, blank=True
    )
    referencia_id = models.IntegerField(
        db_column="referenciaId", null=True, blank=True
    )
    fecha_generacion = models.DateTimeField(
        db_column="fechaGeneracion", auto_now_add=True
    )
    usuario = models.ForeignKey(
        "seguridad.Usuario",
        on_delete=models.SET_NULL,
        db_column="idUsuario",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documento_exportado"
