from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.permissions import TienePermiso

from .models import AjusteInventario
from .serializers import AjusteInventarioSerializer
from .services import AjusteError, confirmar_ajuste


class AjusteInventarioViewSet(viewsets.ModelViewSet):
    queryset = AjusteInventario.objects.prefetch_related("detalles__producto")
    serializer_class = AjusteInventarioSerializer
    permission_classes = [TienePermiso]
    permisos_por_accion = {
        "create": "ajustes.crear",
        "update": "ajustes.editar",
        "partial_update": "ajustes.editar",
        "confirmar": "ajustes.confirmar",
    }

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        try:
            ajuste = confirmar_ajuste(pk, usuario=request.user)
        except AjusteError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(ajuste).data)
