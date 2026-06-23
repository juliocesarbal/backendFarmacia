from django.db import transaction
from rest_framework import serializers

from .models import Compra, DetalleCompra


class DetalleCompraSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = DetalleCompra
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "unidad_medida",
            "cantidad",
            "costo_unitario",
            "costo_total",
            "numero_lote",
            "fecha_vencimiento",
            "observacion",
        ]
        read_only_fields = ["costo_total"]


class CompraSerializer(serializers.ModelSerializer):
    detalles = DetalleCompraSerializer(many=True)
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "numero_orden",
            "numero_factura",
            "fecha_compra",
            "estado",
            "total_compra",
            "observacion",
            "proveedor",
            "proveedor_nombre",
            "detalles",
        ]
        read_only_fields = ["estado", "total_compra"]

    @transaction.atomic
    def create(self, validated_data):
        detalles = validated_data.pop("detalles", [])
        compra = Compra.objects.create(**validated_data)
        # bulk_create: una sola consulta para todos los detalles (no N round-trips)
        DetalleCompra.objects.bulk_create(
            [DetalleCompra(compra=compra, **det) for det in detalles]
        )
        return compra
