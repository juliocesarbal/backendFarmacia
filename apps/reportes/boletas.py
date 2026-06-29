"""Generacion de boletas individuales (compra, venta, baja) en PDF.

Util compartido sin dependencias de modelos; cada ViewSet arma los datos y llama
`boleta_pdf(...)`. Se usa desde la accion `boleta` con `?formato=pdf`.
"""
from io import BytesIO

from django.http import HttpResponse

MARCA = "#731A1B"


def _v(x):
    return "" if x is None else str(x)


def boleta_pdf(titulo, cabecera, columnas, items, total_label="Total", total_val=None,
               nombre_archivo="boleta"):
    """
    titulo: str. cabecera: list[(label, valor)]. columnas: list[(encabezado, key)].
    items: list[dict]. Devuelve HttpResponse con el PDF.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
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
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.2 * cm)
    styles = getSampleStyleSheet()
    elems = [
        Paragraph("Farmacia HEV-UAGRM", styles["Title"]),
        Paragraph(titulo, styles["Heading2"]),
        Spacer(1, 0.3 * cm),
    ]

    # Cabecera (datos generales) como tabla de 2 columnas
    if cabecera:
        cab = Table([[f"{lbl}:", _v(val)] for lbl, val in cabecera], colWidths=[5 * cm, 11 * cm])
        cab.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(MARCA)),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        elems += [cab, Spacer(1, 0.4 * cm)]

    # Detalle
    data = [[h for h, _ in columnas]]
    for row in items:
        data.append([_v(row.get(k)) for _, k in columnas])
    tabla = Table(data, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(MARCA)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
    ]))
    elems.append(tabla)

    if total_val is not None:
        elems += [Spacer(1, 0.3 * cm),
                  Paragraph(f"<b>{total_label}: {_v(total_val)}</b>", styles["Normal"])]

    doc.build(elems)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="{nombre_archivo}.pdf"'
    return resp
