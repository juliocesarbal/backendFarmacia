from rest_framework import serializers

from .models import CategoriaProducto, Producto, UnidadMedida


class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ["id", "nombre", "descripcion", "estado"]


class UnidadMedidaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnidadMedida
        fields = ["id", "nombre", "abreviatura", "estado"]


class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    unidad_nombre = serializers.CharField(
        source="unidad_medida.abreviatura", read_only=True
    )
    stock_actual = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id",
            "codigo_producto",
            "nombre",
            "descripcion",
            "tipo_producto",
            "precio_venta",
            "costo_referencial",
            "stock_minimo",
            "estado",
            "categoria",
            "categoria_nombre",
            "unidad_medida",
            "unidad_nombre",
            "stock_actual",
        ]

    def get_stock_actual(self, obj):
        # Usa la anotacion del queryset si existe (1 sola consulta); si no, el property.
        valor = getattr(obj, "stock_annotado", None)
        return valor if valor is not None else obj.stock_actual
