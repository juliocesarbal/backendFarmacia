from datetime import date, timedelta

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    exportar_excel,
    exportar_pdf,
    generar_kardex,
    verificar_saldo_vs_capas,
)


def _rango(request):
    hoy = date.today()
    desde = request.query_params.get("desde")
    hasta = request.query_params.get("hasta")
    desde = date.fromisoformat(desde) if desde else hoy - timedelta(days=30)
    hasta = date.fromisoformat(hasta) if hasta else hoy
    return desde, hasta


class KardexProductoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, producto_id):
        desde, hasta = _rango(request)
        kardex = generar_kardex(producto_id, desde, hasta)
        cap_cant, cap_valor = verificar_saldo_vs_capas(producto_id)
        kardex["verificacion_capas"] = {
            "cantidad": cap_cant,
            "valor": cap_valor,
            "coincide": cap_cant == kardex["saldo_final_cantidad"],
        }
        return Response(kardex)


class KardexExcelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, producto_id):
        desde, hasta = _rango(request)
        kardex = generar_kardex(producto_id, desde, hasta)
        contenido = exportar_excel(kardex)
        resp = HttpResponse(
            contenido,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        resp["Content-Disposition"] = (
            f'attachment; filename="kardex_{producto_id}.xlsx"'
        )
        return resp


class KardexPdfView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, producto_id):
        desde, hasta = _rango(request)
        kardex = generar_kardex(producto_id, desde, hasta)
        contenido = exportar_pdf(kardex)
        resp = HttpResponse(contenido, content_type="application/pdf")
        resp["Content-Disposition"] = (
            f'attachment; filename="kardex_{producto_id}.pdf"'
        )
        return resp
