from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from .models import AnulacionBoleta, ComprobantePago, DetalleVenta, Venta


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


class ComprobantePagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComprobantePago
        fields = [
            "id",
            "venta",
            "numero_comprobante",
            "monto_pagado",
            "fecha_pago",
            "estado_verificacion",
            "observacion",
        ]
        read_only_fields = ["estado_verificacion", "fecha_pago"]


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)
    comprobantes = ComprobantePagoSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "numero_boleta",
            "fecha_venta",
            "tipo_venta",
            "estado",
            "estado_pago",
            "estado_entrega",
            "total_venta",
            "observacion",
            "detalles",
            "comprobantes",
        ]
        read_only_fields = [
            "estado", "estado_pago", "estado_entrega", "total_venta", "fecha_venta",
        ]

    @transaction.atomic
    def create(self, validated_data):
        """Crea la venta PENDIENTE de pago. Calcula subtotales y total. NO toca stock."""
        detalles = validated_data.pop("detalles", [])
        venta = Venta.objects.create(**validated_data)
        total = Decimal("0")
        objs = []
        for det in detalles:
            subtotal = (det["cantidad"] * det["precio_unitario"]).quantize(
                Decimal("0.0001")
            )
            total += subtotal
            objs.append(DetalleVenta(venta=venta, subtotal=subtotal, **det))
        DetalleVenta.objects.bulk_create(objs)
        venta.total_venta = total
        venta.save(update_fields=["total_venta"])
        return venta


class AnulacionBoletaSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnulacionBoleta
        fields = ["id", "venta", "fecha_anulacion", "motivo", "observacion"]
