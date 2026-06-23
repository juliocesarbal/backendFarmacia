"""Exportacion de reportes a Excel, PDF y HTML desde filas (list[dict])."""
import re
from io import BytesIO

from django.http import HttpResponse
from django.utils.html import escape

MARCA = "#731A1B"


def _slug(titulo):
    return re.sub(r"[^a-z0-9]+", "_", titulo.lower()).strip("_") or "reporte"


def _val(row, key):
    v = row.get(key)
    return "" if v is None else v


def exportar_reporte(formato, titulo, columnas, filas, resumen=None):
    """
    Devuelve un HttpResponse de descarga segun `formato` (excel|pdf|html),
    o None si el formato no es de exportacion (entonces el view responde JSON).
    columnas: lista de (encabezado, clave). filas: list[dict].
    """
    if formato == "excel":
        return _excel(titulo, columnas, filas)
    if formato == "pdf":
        return _pdf(titulo, columnas, filas)
    if formato == "html":
        return _html(titulo, columnas, filas, resumen)
    return None


def _excel(titulo, columnas, filas):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append([titulo])
    ws.append([h for h, _ in columnas])
    for row in filas:
        ws.append([str(_val(row, k)) for _, k in columnas])
    buf = BytesIO()
    wb.save(buf)
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{_slug(titulo)}.xlsx"'
    return resp


def _pdf(titulo, columnas, filas):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(letter), topMargin=1 * cm)
    styles = getSampleStyleSheet()
    data = [[h for h, _ in columnas]]
    for row in filas:
        data.append([str(_val(row, k)) for _, k in columnas])
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MARCA)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
            ]
        )
    )
    elems = [Paragraph(titulo, styles["Title"]), Spacer(1, 0.4 * cm), tabla]
    doc.build(elems)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{_slug(titulo)}.pdf"'
    return resp


def _html(titulo, columnas, filas, resumen=None):
    th = "".join(f"<th>{escape(h)}</th>" for h, _ in columnas)
    rows = ""
    for row in filas:
        tds = "".join(f"<td>{escape(str(_val(row, k)))}</td>" for _, k in columnas)
        rows += f"<tr>{tds}</tr>"
    resumen_html = ""
    if resumen:
        partes = " · ".join(f"{escape(str(k))}: {escape(str(v))}" for k, v in resumen.items())
        resumen_html = f"<p class='resumen'>{partes}</p>"
    html = (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>{escape(titulo)}</title><style>"
        "body{font-family:Arial,Helvetica,sans-serif;margin:24px;color:#1f2937}"
        f"h1{{color:{MARCA};font-size:20px;margin-bottom:4px}}"
        ".resumen{color:#555;margin:0 0 16px}"
        "table{border-collapse:collapse;width:100%;font-size:12px}"
        "th,td{border:1px solid #ccc;padding:6px 8px;text-align:left}"
        f"th{{background:{MARCA};color:#fff}}tr:nth-child(even){{background:#f6f6f6}}"
        "</style></head><body>"
        f"<h1>{escape(titulo)}</h1>{resumen_html}"
        f"<table><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table>"
        "</body></html>"
    )
    resp = HttpResponse(html, content_type="text/html")
    resp["Content-Disposition"] = f'attachment; filename="{_slug(titulo)}.html"'
    return resp
