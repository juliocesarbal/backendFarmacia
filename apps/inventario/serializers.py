from django.db import transaction
from rest_framework import serializers

from .models import (
    AjusteInventario,
    Baja,
    CapaCosto,
    DetalleAjuste,
    DetalleBaja,
    InventarioProducto,
    MotivoBaja,
    MovimientoInventario,
)


class CapaCostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapaCosto
        fields = [
            "id",
            "producto",
            "cantidad_inicial",
            "cantidad_disponible",
            "costo_unitario",
            "fecha_ingreso",
            "origen",
            "estado",
        ]


class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "fecha_movimiento",
            "sentido",
            "tipo_movimiento",
            "cantidad",
            "costo_unitario_aplicado",
            "valor_movimiento",
            "motivo",
            "referencia_tipo",
            "referencia_id",
        ]


class InventarioProductoSerializer(serializers.ModelSerializer):
    codigo_producto = serializers.CharField(
        source="producto.codigo_producto", read_only=True
    )
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    tipo_producto = serializers.CharField(
        source="producto.tipo_producto", read_only=True
    )
    stock_minimo = serializers.DecimalField(
        source="producto.stock_minimo", max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = InventarioProducto
        fields = [
            "id",
            "producto",
            "codigo_producto",
            "producto_nombre",
            "tipo_producto",
            "cantidad_actual",
            "costo_referencial",
            "stock_minimo",
            "fecha_actualizacion",
        ]


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
            "cantidad",
            "costo_total_baja",
            "observacion",
        ]
        read_only_fields = ["costo_total_baja"]


class BajaSerializer(serializers.ModelSerializer):
    detalles = DetalleBajaSerializer(many=True)
    motivo_nombre = serializers.CharField(source="motivo_baja.nombre", read_only=True)

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
