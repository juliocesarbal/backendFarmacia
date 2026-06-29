from datetime import date, timedelta

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EjecucionKMeans
from .serializers import EjecucionKMeansSerializer
from .services import ejecutar_kmeans


class KMeansEjecutarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        k = int(request.data.get("k", 4))
        hoy = date.today()
        inicio = request.data.get("periodo_inicio")
        fin = request.data.get("periodo_fin")
        inicio = date.fromisoformat(inicio) if inicio else hoy - timedelta(days=90)
        fin = date.fromisoformat(fin) if fin else hoy
        try:
            ejecucion = ejecutar_kmeans(k, inicio, fin, usuario=request.user)
        except Exception as e:  # K-means es complementario, no debe romper el sistema
            return Response(
                {"detail": f"Error al ejecutar K-means: {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Recarga con prefetch para evitar N+1 al serializar clusters/productos
        ejecucion = EjecucionKMeans.objects.prefetch_related(
            "clusters__productos__producto"
        ).get(pk=ejecucion.pk)
        return Response(
            EjecucionKMeansSerializer(ejecucion).data, status=status.HTTP_201_CREATED
        )


class KMeansResultadosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        ejecucion = EjecucionKMeans.objects.prefetch_related(
            "clusters__productos__producto"
        ).get(pk=pk)
        return Response(EjecucionKMeansSerializer(ejecucion).data)


class KMeansExcelView(APIView):
    """Exporta los resultados de una ejecucion K-means a .xlsx (v3 §23)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from io import BytesIO

        from django.http import HttpResponse
        from openpyxl import Workbook

        ejecucion = EjecucionKMeans.objects.prefetch_related(
            "clusters__productos__producto"
        ).get(pk=pk)
        wb = Workbook()
        ws = wb.active
        ws.title = "Segmentacion"
        ws.append([f"Segmentacion K-means #{ejecucion.id}"])
        ws.append([
            f"Periodo: {ejecucion.periodo_inicio} a {ejecucion.periodo_fin}",
            f"Clusters: {ejecucion.numero_clusters}",
        ])
        ws.append([])
        ws.append([
            "Cluster", "Descripcion", "Codigo", "Producto",
            "Rotacion", "Consumo", "Costo", "Stock",
        ])
        for c in ejecucion.clusters.all():
            for pc in c.productos.all():
                ws.append([
                    c.nombre_cluster, c.descripcion,
                    pc.producto.codigo_producto, pc.producto.nombre,
                    float(pc.rotacion), float(pc.consumo_total),
                    float(pc.costo_total), float(pc.stock_actual),
                ])
        buf = BytesIO()
        wb.save(buf)
        resp = HttpResponse(
            buf.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="segmentacion_kmeans_{pk}.xlsx"'
        )
        return resp
