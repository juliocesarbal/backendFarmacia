"""Registro de bitacora para trazabilidad de operaciones criticas."""
from .models import BitacoraOperacion


def registrar_bitacora(
    *, usuario=None, modulo, accion, entidad, id_entidad=None,
    valores_anteriores=None, valores_nuevos=None, ip_origen="",
):
    """Crea una entrada de bitacora. No debe romper la operacion principal."""
    try:
        return BitacoraOperacion.objects.create(
            usuario=usuario,
            modulo=modulo,
            accion=accion,
            entidad=entidad,
            id_entidad=id_entidad,
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            ip_origen=ip_origen,
        )
    except Exception:
        return None
