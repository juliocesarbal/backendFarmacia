from decimal import Decimal

from django.db.models import DecimalField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.seguridad.permissions import TienePermiso

from .models import CategoriaProducto, Producto, UnidadMedida
from .serializers import (
    CategoriaProductoSerializer,
    ProductoSerializer,
    UnidadMedidaSerializer,
)


class CategoriaProductoViewSet(viewsets.ModelViewSet):
    queryset = CategoriaProducto.objects.all()
    serializer_class = CategoriaProductoSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "catalogo.gestionar",
        "update": "catalogo.gestionar",
        "partial_update": "catalogo.gestionar",
        "destroy": "catalogo.gestionar",
    }


class UnidadMedidaViewSet(viewsets.ModelViewSet):
    queryset = UnidadMedida.objects.all()
    serializer_class = UnidadMedidaSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "catalogo.gestionar",
        "update": "catalogo.gestionar",
        "partial_update": "catalogo.gestionar",
        "destroy": "catalogo.gestionar",
    }


class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.select_related("categoria", "unidad_medida")
    serializer_class = ProductoSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "productos.crear",
        "update": "productos.editar",
        "partial_update": "productos.editar",
        "anular": "productos.anular",
        "restaurar": "productos.anular",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        buscar = self.request.query_params.get("buscar")
        tipo = self.request.query_params.get("tipo")
        estado = self.request.query_params.get("estado")
        if buscar:
            qs = qs.filter(
                Q(codigo_producto__icontains=buscar) | Q(nombre__icontains=buscar)
            )
        if tipo:
            qs = qs.filter(tipo_producto=tipo)
        if estado:
            qs = qs.filter(estado=estado)
        # Stock via subconsulta correlada: evita el N+1 del property y mantiene
        # barato el COUNT de la paginacion (no fuerza GROUP BY sobre capa_costo).
        from apps.inventario.models import CapaCosto

        stock_sub = (
            CapaCosto.objects.filter(producto=OuterRef("pk"), estado="ACTIVA")
            .values("producto")
            .annotate(total=Sum("cantidad_disponible"))
            .values("total")
        )
        return qs.annotate(
            stock_annotado=Coalesce(
                Subquery(stock_sub, output_field=DecimalField(max_digits=14, decimal_places=2)),
                Value(Decimal("0")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        producto = self.get_object()
        producto.estado = "ANULADO"
        producto.save(update_fields=["estado"])
        return Response(self.get_serializer(producto).data)

    @action(detail=True, methods=["post"])
    def restaurar(self, request, pk=None):
        producto = self.get_object()
        producto.estado = "ACTIVO"
        producto.save(update_fields=["estado"])
        return Response(self.get_serializer(producto).data)

    @action(detail=False, methods=["get"])
    def select(self, request):
        """Lista ligera de productos activos para combos (sin stock ni paginacion)."""
        datos = (
            Producto.objects.filter(estado="ACTIVO")
            .order_by("nombre")
            .values("id", "codigo_producto", "nombre")
        )
        return Response(list(datos))

    @action(detail=True, methods=["get"])
    def stock(self, request, pk=None):
        producto = self.get_object()
        return Response({"producto": producto.id, "stock_actual": producto.stock_actual})

    @action(detail=True, methods=["get"])
    def capas(self, request, pk=None):
        """Capas de costo activas del producto (CU19: costos historicos y capas)."""
        producto = self.get_object()
        capas = producto.capas_costo.filter(estado="ACTIVA").order_by(
            "fecha_ingreso", "id"
        )
        data = [
            {
                "id": c.id,
                "cantidad_inicial": c.cantidad_inicial,
                "cantidad_disponible": c.cantidad_disponible,
                "costo_unitario": c.costo_unitario,
                "fecha_ingreso": c.fecha_ingreso,
                "origen": c.origen,
                "estado": c.estado,
            }
            for c in capas
        ]
        return Response(data)
