from django.db import transaction
from rest_framework import serializers

from .models import AnulacionBoleta, DetalleVenta, Venta


class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "costo_total_salida",
        ]
        read_only_fields = ["subtotal", "costo_total_salida"]


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "numero_boleta",
            "fecha_venta",
            "tipo_venta",
            "estado",
            "total_venta",
            "observacion",
            "detalles",
        ]
        read_only_fields = ["estado", "total_venta", "fecha_venta"]

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        venta = Venta.objects.create(**validated_data)
        DetalleVenta.objects.bulk_create(
            [DetalleVenta(venta=venta, **det) for det in detalles]
        )
        return venta


class AnulacionBoletaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnulacionBoleta
        fields = ["id", "venta", "fecha_anulacion", "motivo", "observacion"]
