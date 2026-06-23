from rest_framework import serializers

from .models import BitacoraOperacion


class BitacoraOperacionSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.username", read_only=True, default=""
    )

    class Meta:
        model = BitacoraOperacion
        fields = [
            "id",
            "usuario",
            "usuario_nombre",
            "modulo",
            "accion",
            "entidad",
            "id_entidad",
            "valores_anteriores",
            "valores_nuevos",
            "ip_origen",
            "fecha_operacion",
        ]
