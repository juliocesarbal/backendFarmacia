from django.db import transaction
from rest_framework import serializers

from .models import Baja, DetalleBaja, MotivoBaja


class MotivoBajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MotivoBaja
        fields = ["id", "nombre", "descripcion", "estado"]


class DetalleBajaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleBaja
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "capa",
            "cantidad",
            "costo_total_baja",
            "observacion",
        ]
        read_only_fields = ["costo_total_baja"]


class BajaSerializer(serializers.ModelSerializer):
    detalles = DetalleBajaSerializer(many=True)
    motivo_nombre = serializers.CharField(
        source="motivo_baja.nombre", read_only=True
    )

    class Meta:
        model = Baja
        fields = [
            "id",
            "numero_baja",
            "fecha_baja",
            "estado",
            "observacion",
            "motivo_baja",
            "motivo_nombre",
            "detalles",
        ]
        read_only_fields = ["estado", "fecha_baja"]

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        baja = Baja.objects.create(**validated_data)
        DetalleBaja.objects.bulk_create(
            [DetalleBaja(baja=baja, **det) for det in detalles]
        )
        return baja
