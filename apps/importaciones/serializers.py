from rest_framework import serializers

from .models import DetalleImportacion, ImportacionArchivo, LogImportacion


class LogImportacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LogImportacion
        fields = ["id", "fila", "campo", "valor", "tipo_error", "descripcion"]


class DetalleImportacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleImportacion
        fields = [
            "id",
            "numero_fila",
            "datos_originales",
            "estado_fila",
            "mensaje_error",
        ]


class ImportacionArchivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportacionArchivo
        fields = [
            "id",
            "tipo_importacion",
            "nombre_archivo",
            "estado",
            "total_registros",
            "registros_validos",
            "registros_observados",
            "fecha_importacion",
        ]
