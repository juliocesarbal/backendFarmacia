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
