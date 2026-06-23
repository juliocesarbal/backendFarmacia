from django.db import transaction
from rest_framework import serializers

from .models import AjusteInventario, DetalleAjuste


class DetalleAjusteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleAjuste
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "cantidad",
            "costo_unitario",
            "costo_total",
            "observacion",
        ]
        read_only_fields = ["costo_total"]


class AjusteInventarioSerializer(serializers.ModelSerializer):
    detalles = DetalleAjusteSerializer(many=True)

    class Meta:
        model = AjusteInventario
        fields = [
            "id",
            "numero_ajuste",
            "fecha_ajuste",
            "tipo_ajuste",
            "estado",
            "motivo",
            "observacion",
            "detalles",
        ]
        read_only_fields = ["estado", "fecha_ajuste"]

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        ajuste = AjusteInventario.objects.create(**validated_data)
        DetalleAjuste.objects.bulk_create(
            [DetalleAjuste(ajuste=ajuste, **det) for det in detalles]
        )
        return ajuste
