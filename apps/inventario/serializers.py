from rest_framework import serializers

from .models import CapaCosto, InventarioProducto, MovimientoInventario


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
