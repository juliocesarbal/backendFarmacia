from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import BitacoraOperacion
from .serializers import BitacoraOperacionSerializer


class BitacoraOperacionViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Trazabilidad de operaciones (solo lectura)."""

    queryset = BitacoraOperacion.objects.select_related("usuario")
    serializer_class = BitacoraOperacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        modulo = self.request.query_params.get("modulo")
        entidad = self.request.query_params.get("entidad")
        if modulo:
            qs = qs.filter(modulo=modulo)
        if entidad:
            qs = qs.filter(entidad=entidad)
        return qs
