from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DetalleImportacion, ImportacionArchivo
from .serializers import (
    DetalleImportacionSerializer,
    ImportacionArchivoSerializer,
    LogImportacionSerializer,
)
from .services import cargar_y_validar, confirmar_importacion


class _ImportarBase(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    tipo = None

    def post(self, request):
        archivo = request.FILES.get("archivo")
        if not archivo:
            return Response(
                {"detail": "Adjunte el archivo Excel en 'archivo'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importacion = cargar_y_validar(
            self.tipo, archivo, archivo.name, usuario=request.user
        )
        data = ImportacionArchivoSerializer(importacion).data
        data["detalles"] = DetalleImportacionSerializer(
            importacion.detalles.all(), many=True
        ).data
        return Response(data, status=status.HTTP_201_CREATED)


class ImportarInventarioInicialView(_ImportarBase):
    tipo = "INVENTARIO_INICIAL"


class ImportarComprasView(_ImportarBase):
    tipo = "COMPRAS"


class ImportarVentasView(_ImportarBase):
    tipo = "VENTAS"


class ImportacionErroresView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        imp = ImportacionArchivo.objects.get(pk=pk)
        return Response(LogImportacionSerializer(imp.logs.all(), many=True).data)


class ImportacionConfirmarView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            imp = confirmar_importacion(pk, usuario=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ImportacionArchivoSerializer(imp).data)
