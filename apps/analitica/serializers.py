from rest_framework import serializers

from .models import ClusterKMeans, EjecucionKMeans, ProductoCluster


class ProductoClusterSerializer(serializers.ModelSerializer):
    codigo = serializers.CharField(source="producto.codigo_producto", read_only=True)
    nombre = serializers.CharField(source="producto.nombre", read_only=True)

    class Meta:
        model = ProductoCluster
        fields = [
            "id", "producto", "codigo", "nombre",
            "rotacion", "consumo_total", "costo_total", "stock_actual",
        ]


class ClusterKMeansSerializer(serializers.ModelSerializer):
    productos = ProductoClusterSerializer(many=True, read_only=True)

    class Meta:
        model = ClusterKMeans
        fields = ["id", "numero_cluster", "nombre_cluster", "descripcion", "productos"]


class EjecucionKMeansSerializer(serializers.ModelSerializer):
    clusters = ClusterKMeansSerializer(many=True, read_only=True)

    class Meta:
        model = EjecucionKMeans
        fields = [
            "id", "numero_clusters", "periodo_inicio", "periodo_fin",
            "variables_usadas", "estado", "fecha_ejecucion", "clusters",
        ]
