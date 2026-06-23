"""
Carga catalogo real (Excel del sistema antiguo) + genera historial de inventario
2025-2026 con CAPAS DE COSTO reales para probar el Kardex valorado PEPS/FIFO.

Cada compra ingresa a un costo que varia 0-20% respecto al costo base del
producto (inflacion + ruido), creando capas a distinto costo. Las ventas
consumen por FIFO, dejando capas viejas (mas baratas) conviviendo con capas
nuevas (mas caras) -> exactamente el escenario que el sistema debe valorar bien.

Uso:
    python manage.py seed_historico                 # catalogo completo + historial de 50 productos
    python manage.py seed_historico --limit 80
    python manage.py seed_historico --todos          # historial para TODOS los productos
    python manage.py seed_historico --reset          # borra movimientos/compras/ventas/bajas antes
    python manage.py seed_historico --desde 2025-01 --hasta 2026-04

El catalogo siempre se importa completo. El historial se genera para un
subconjunto (por defecto 50, incluyendo los 8 productos con Kardex real de
referencia: 679, 258, 56, 292, 280, 636, 419, 144).
"""
import random
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.ajustes.models import AjusteInventario, DetalleAjuste
from apps.bajas.models import Baja, DetalleBaja, MotivoBaja
from apps.catalogos.models import CategoriaProducto, Producto, UnidadMedida
from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import (
    CapaCosto,
    ConsumoCapaCosto,
    InventarioProducto,
    MovimientoInventario,
)
from apps.proveedores.models import Proveedor
from apps.ventas.models import DetalleVenta, Venta

D = lambda x: Decimal(str(x))
Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")

# Productos con Kardex real de referencia (se incluyen siempre en el historial)
CODIGOS_REFERENCIA = ["679", "258", "56", "292", "280", "636", "419", "144"]

# Mapeo de abreviaturas de unidad del Excel -> nombre
UNIDADES = {
    "U": "Unidad", "FR": "Frasco", "APLIC": "Aplicacion", "DS": "Dosis",
    "ML": "Mililitro", "ml": "Mililitro", "CJA": "Caja", "AMP": "Ampolla",
    "COMP": "Comprimido", "TAB": "Tableta", "SOB": "Sobre", "TUBO": "Tubo",
}


def inferir_tipo(nombre):
    n = nombre.upper()
    materiales = ["JERINGA", "AGUJA", "BRANULA", "HILO", "CATETER", "GUANTE",
                  "SONDA", "GASA", "VENDA", "ESPARADRAPO", "BISTURI", "EQUIPO"]
    insumos = ["ALCOHOL", "AGUA", "SUERO", "SOLUCION", "YODO", "OXIGENADA"]
    if any(k in n for k in materiales):
        return "MATERIAL", "Materiales"
    if any(k in n for k in insumos):
        return "INSUMO", "Insumos"
    return "MEDICAMENTO", "Medicamentos"


class Command(BaseCommand):
    help = "Carga catalogo real e historial 2025-2026 con capas de costo FIFO."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--todos", action="store_true")
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--desde", type=str, default="2025-01")
        parser.add_argument("--hasta", type=str, default="2026-04")
        parser.add_argument(
            "--inventario", type=str,
            default=str(Path(settings.BASE_DIR) / "seed_data" / "inventario_dic_2025.xlsx"),
        )

    def handle(self, *args, **opt):
        random.seed(42)
        self.stdout.write(self.style.WARNING("== Seed historico de farmacia =="))

        if opt["reset"]:
            self._reset()

        productos_excel = self._leer_inventario(opt["inventario"])
        self.stdout.write(f"Productos en Excel: {len(productos_excel)}")

        catalogo = self._cargar_catalogo(productos_excel)
        self.stdout.write(self.style.SUCCESS(f"Catalogo cargado: {len(catalogo)} productos"))

        # Subconjunto para historial
        if opt["todos"]:
            objetivo = list(catalogo.values())
        else:
            ref = [catalogo[c] for c in CODIGOS_REFERENCIA if c in catalogo]
            resto = [p for c, p in catalogo.items() if c not in CODIGOS_REFERENCIA]
            random.shuffle(resto)
            objetivo = ref + resto[: max(0, opt["limit"] - len(ref))]

        desde = self._mes(opt["desde"])
        hasta = self._mes(opt["hasta"])
        proveedor = self._proveedor()
        motivo_baja = self._motivo_baja()

        self.stdout.write(f"Generando historial {opt['desde']} -> {opt['hasta']} "
                          f"para {len(objetivo)} productos...")
        total_mov = 0
        for idx, prod in enumerate(objetivo, 1):
            total_mov += self._historial_producto(prod, desde, hasta, proveedor, motivo_baja)
            if idx % 10 == 0:
                self.stdout.write(f"  {idx}/{len(objetivo)} productos procesados")

        self.stdout.write(self.style.SUCCESS(
            f"Listo. {len(objetivo)} productos con historial, ~{total_mov} movimientos."
        ))
        self.stdout.write("Prueba: GET /api/kardex/producto/<id>/?desde=2025-01-01&hasta=2026-12-31")

    # ---------------------------------------------------------------- helpers
    def _mes(self, s):
        y, m = s.split("-")
        return date(int(y), int(m), 1)

    def _reset(self):
        self.stdout.write("Reseteando movimientos/compras/ventas/bajas/ajustes...")
        ConsumoCapaCosto.objects.all().delete()
        MovimientoInventario.objects.all().delete()
        CapaCosto.objects.all().delete()
        InventarioProducto.objects.all().delete()
        DetalleVenta.objects.all().delete()
        Venta.objects.all().delete()
        DetalleCompra.objects.all().delete()
        Compra.objects.all().delete()
        DetalleBaja.objects.all().delete()
        Baja.objects.all().delete()
        DetalleAjuste.objects.all().delete()
        AjusteInventario.objects.all().delete()

    def _leer_inventario(self, ruta):
        wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
        ws = wb["INVENTARIO 2025"]
        filas = []
        encabezado_visto = False
        for row in ws.iter_rows(values_only=True):
            if not encabezado_visto:
                if row and str(row[0]).strip().upper() == "ITEM":
                    encabezado_visto = True
                continue
            cod = row[1]
            nombre = row[2]
            if cod is None or nombre is None or str(nombre).strip() == "":
                continue
            try:
                precio = D(row[4] or 0)
                costo = D(row[5] or 0)
            except Exception:
                continue
            filas.append({
                "codigo": str(cod).strip(),
                "nombre": str(nombre).strip(),
                "stock_dic2025": D(row[3] or 0),
                "precio": precio,
                "costo": costo,
                "unidad": str(row[6] or "U").strip(),
            })
        wb.close()
        return filas

    def _cargar_catalogo(self, productos_excel):
        # Categorias / unidades (pocas, get_or_create OK)
        cats = {}
        for nombre in ["Medicamentos", "Materiales", "Insumos"]:
            cats[nombre], _ = CategoriaProducto.objects.get_or_create(nombre=nombre)
        unidades = {}
        for abrev, nombre in UNIDADES.items():
            u, _ = UnidadMedida.objects.get_or_create(
                nombre=nombre, defaults={"abreviatura": abrev[:20]}
            )
            unidades[abrev] = u
        und_default = unidades["U"]

        # Productos ya existentes (por codigo) para no duplicar
        existentes = {p.codigo_producto: p for p in Producto.objects.all()}
        nuevos = []
        vistos = set(existentes)
        for p in productos_excel:
            cod = p["codigo"]
            if cod in vistos:
                continue
            vistos.add(cod)
            tipo, cat_nombre = inferir_tipo(p["nombre"])
            abrev = p["unidad"].split()[0] if p["unidad"] else "U"
            unidad = unidades.get(abrev, und_default)
            costo = p["costo"] if p["costo"] > 0 else D("1")
            nuevos.append(Producto(
                codigo_producto=cod, nombre=p["nombre"][:160], tipo_producto=tipo,
                precio_venta=p["precio"].quantize(Q4),
                costo_referencial=costo.quantize(Q4), stock_minimo=D("5"),
                estado="ACTIVO", categoria=cats[cat_nombre], unidad_medida=unidad,
            ))
        if nuevos:
            Producto.objects.bulk_create(nuevos, batch_size=200)
        # Recargar mapa completo con IDs
        return {p.codigo_producto: p for p in Producto.objects.all()}

    def _proveedor(self):
        prov, _ = Proveedor.objects.get_or_create(
            nombre="Distribuidora Veterinaria Santa Cruz",
            defaults={"nit": "1023456789", "estado": "ACTIVO",
                      "telefono": "33445566", "direccion": "Av. Busch #123"},
        )
        return prov

    def _motivo_baja(self):
        return MotivoBaja.objects.get_or_create(nombre="Vencimiento")[0]

    def _costo_variable(self, base, mes_idx, total_meses):
        """Costo de compra con drift inflacionario 0-15% + ruido, dentro de 0-20%."""
        drift = Decimal("0.15") * D(mes_idx) / D(max(1, total_meses))
        ruido = D(random.uniform(-0.04, 0.06))
        factor = Decimal("1") + drift + ruido
        factor = max(Decimal("1.0"), min(Decimal("1.20"), factor))
        return (base * factor).quantize(Q4, rounding=ROUND_HALF_UP)

    @transaction.atomic
    def _historial_producto(self, producto, desde, hasta, proveedor, motivo_baja):
        """
        Genera compras (capas), ventas (FIFO) y bajas para un producto usando
        bulk_create por fases para minimizar round-trips contra Railway.
        Preserva cronologia: una venta solo consume capas ya ingresadas.
        """
        base_costo = producto.costo_referencial or D("1")
        base_lote = random.choice([20, 40, 60, 100, 150])

        meses = []
        cur = desde
        while cur <= hasta:
            meses.append(cur)
            cur = (cur.replace(day=28) + timedelta(days=7)).replace(day=1)
        total_meses = len(meses)

        # ---- 1. PLAN de compras (capa inicial + reposiciones) ----
        # plan_compra: (mes_idx, fecha, cantidad, costo, obs)
        plan_compras = []
        costo_ini = (base_costo * D("0.90")).quantize(Q4)
        plan_compras.append((0, desde, D(random.randint(int(base_lote * 0.5), base_lote)),
                             costo_ini, "Saldo inicial 2025"))
        for i, mes in enumerate(meses):
            if i > 0 and (i % random.choice([2, 3]) == 0):
                costo = self._costo_variable(base_costo, i, total_meses)
                cant = D(random.randint(int(base_lote * 0.6), int(base_lote * 1.4)))
                fecha_compra = mes.replace(day=random.randint(3, 15))
                plan_compras.append((i, fecha_compra, cant, costo,
                                     f"Compra {mes.strftime('%b %Y')}"))

        # ---- 2. Crear Compra (bulk) -> IDs ----
        compras = [Compra(
            numero_factura=f"F-{random.randint(10000, 99999)}",
            numero_orden=str(random.randint(1000, 1999)), fecha_compra=f,
            estado="CONFIRMADA", total_compra=(c * co).quantize(Q4),
            proveedor=proveedor, observacion=o,
        ) for (_, f, c, co, o) in plan_compras]
        Compra.objects.bulk_create(compras)

        # ---- 3. DetalleCompra + CapaCosto + Movimiento ENTRADA (bulk) ----
        detalles_c, capas, movs_in = [], [], []
        for compra, (_, f, c, co, o) in zip(compras, plan_compras):
            total = (c * co).quantize(Q4)
            detalles_c.append(DetalleCompra(
                compra=compra, producto=producto, cantidad=c, costo_unitario=co,
                costo_total=total, unidad_medida=producto.unidad_medida))
            capas.append(CapaCosto(
                producto=producto, cantidad_inicial=c, cantidad_disponible=c,
                costo_unitario=co, fecha_ingreso=f, origen="COMPRA",
                origen_id=compra.id, estado="ACTIVA"))
            movs_in.append(MovimientoInventario(
                producto=producto, fecha_movimiento=self._dt(f), sentido="ENTRADA",
                tipo_movimiento="COMPRA", cantidad=c, costo_unitario_aplicado=co,
                valor_movimiento=total, referencia_tipo="COMPRA",
                referencia_id=compra.id, observacion=o))
        DetalleCompra.objects.bulk_create(detalles_c)
        CapaCosto.objects.bulk_create(capas)  # IDs asignados (postgres)
        MovimientoInventario.objects.bulk_create(movs_in)

        # capa_mem por mes de ingreso (para respetar cronologia)
        capas_por_mes = {}
        for (mes_idx, f, c, co, o), capa in zip(plan_compras, capas):
            capas_por_mes.setdefault(mes_idx, []).append(
                {"capa": capa, "costo": co, "disp": c})

        # ---- 4. Recorrer meses: ventas (FIFO) + bajas, acumulando objetos ----
        capas_mem = []
        ventas, det_ventas, movs_out, consumos_obj = [], [], [], []
        bajas, det_bajas = [], []
        # plan de salidas: cada item (mov_obj, [consumo dicts])
        salidas_pendientes = []  # (mov, consumos, es_baja, doc_obj, det_obj)

        for i, mes in enumerate(meses):
            # incorporar capas ingresadas este mes
            if i in capas_por_mes:
                capas_mem.extend(capas_por_mes[i])

            disponible = sum(c["disp"] for c in capas_mem)
            if disponible > 0:
                cant_venta = (disponible * D(random.uniform(0.10, 0.30))).quantize(Decimal("1"))
                if cant_venta > 0:
                    fv = mes.replace(day=random.randint(16, 27))
                    cons = self._consumir_mem(capas_mem, cant_venta)
                    if cons:
                        ct = sum(x["costo_total"] for x in cons)
                        precio = producto.precio_venta or (base_costo * D("1.4"))
                        sub = (cant_venta * precio).quantize(Q4)
                        venta = Venta(
                            numero_boleta=f"B-{random.randint(100000, 999999)}",
                            fecha_venta=self._dt(fv), tipo_venta="VENTA",
                            estado="CONFIRMADA", total_venta=sub)
                        ventas.append(venta)
                        det_ventas.append(DetalleVenta(
                            venta=venta, producto=producto, cantidad=cant_venta,
                            precio_unitario=precio, subtotal=sub, costo_total_salida=ct))
                        mov = MovimientoInventario(
                            producto=producto, fecha_movimiento=self._dt(fv),
                            sentido="SALIDA", tipo_movimiento="VENTA", cantidad=cant_venta,
                            costo_unitario_aplicado=(ct / cant_venta).quantize(Q4),
                            valor_movimiento=ct, referencia_tipo="VENTA")
                        movs_out.append(mov)
                        salidas_pendientes.append((mov, cons, "VENTA", venta))

            disponible = sum(c["disp"] for c in capas_mem)
            if i > 0 and i % 6 == 0 and disponible > 3:
                cant_baja = D(random.randint(1, 3))
                fb = mes.replace(day=random.randint(20, 28))
                cons = self._consumir_mem(capas_mem, cant_baja)
                if cons:
                    ct = sum(x["costo_total"] for x in cons)
                    baja = Baja(
                        numero_baja=f"BAJ-{random.randint(1000, 9999)}",
                        fecha_baja=self._dt(fb), estado="CONFIRMADA",
                        motivo_baja=motivo_baja, observacion="Vencimiento de lote")
                    bajas.append(baja)
                    det_bajas.append(DetalleBaja(
                        baja=baja, producto=producto, cantidad=cant_baja,
                        costo_total_baja=ct))
                    mov = MovimientoInventario(
                        producto=producto, fecha_movimiento=self._dt(fb),
                        sentido="SALIDA", tipo_movimiento="BAJA", cantidad=cant_baja,
                        costo_unitario_aplicado=(ct / cant_baja).quantize(Q4),
                        valor_movimiento=ct, motivo=motivo_baja.nombre,
                        referencia_tipo="BAJA")
                    movs_out.append(mov)
                    salidas_pendientes.append((mov, cons, "BAJA", baja))

        # ---- 5. Persistir cabeceras de salida (bulk) -> IDs ----
        if ventas:
            Venta.objects.bulk_create(ventas)
        if bajas:
            Baja.objects.bulk_create(bajas)
        # asignar referencia_id ahora que venta/baja tienen id
        for mov, cons, tipo, doc in salidas_pendientes:
            mov.referencia_id = doc.id
        if movs_out:
            MovimientoInventario.objects.bulk_create(movs_out)
        # detalles de venta/baja
        for d in det_ventas:
            d.venta_id = d.venta.id
        if det_ventas:
            DetalleVenta.objects.bulk_create(det_ventas)
        for d in det_bajas:
            d.baja_id = d.baja.id
        if det_bajas:
            DetalleBaja.objects.bulk_create(det_bajas)

        # ---- 6. Consumos FIFO (bulk) ----
        for mov, cons, tipo, doc in salidas_pendientes:
            for x in cons:
                consumos_obj.append(ConsumoCapaCosto(
                    movimiento=mov, capa=x["capa"], cantidad_consumida=x["cant"],
                    costo_unitario=x["costo"], valor_consumido=x["costo_total"]))
        if consumos_obj:
            ConsumoCapaCosto.objects.bulk_create(consumos_obj)

        # ---- 7. Actualizar capas (disponible/estado) en bulk ----
        capas_actualizar = [c["capa"] for grupo in capas_por_mes.values() for c in grupo]
        for grupo in capas_por_mes.values():
            for c in grupo:
                c["capa"].cantidad_disponible = c["disp"]
                c["capa"].estado = "AGOTADA" if c["disp"] <= 0 else "ACTIVA"
        if capas_actualizar:
            CapaCosto.objects.bulk_update(
                capas_actualizar, ["cantidad_disponible", "estado"], batch_size=200)

        # ---- 8. Inventario final (cache) ----
        cant_final = sum(c["disp"] for grupo in capas_por_mes.values() for c in grupo)
        valor_final = sum(c["disp"] * c["costo"] for grupo in capas_por_mes.values() for c in grupo)
        costo_ref = (valor_final / cant_final).quantize(Q4) if cant_final > 0 else D("0")
        InventarioProducto.objects.update_or_create(
            producto=producto,
            defaults={"cantidad_actual": cant_final, "costo_referencial": costo_ref})

        return len(movs_in) + len(movs_out)

    def _consumir_mem(self, capas_mem, cantidad):
        """FIFO solo en memoria (sin tocar BD). Devuelve lista de consumos."""
        pendiente = cantidad
        consumos = []
        for c in capas_mem:
            if pendiente <= 0:
                break
            if c["disp"] <= 0:
                continue
            usar = min(c["disp"], pendiente)
            consumos.append({"capa": c["capa"], "cant": usar, "costo": c["costo"],
                             "costo_total": (usar * c["costo"]).quantize(Q4)})
            c["disp"] -= usar
            pendiente -= usar
        return consumos

    def _dt(self, d):
        return timezone.make_aware(datetime(d.year, d.month, d.day, 10, 0))
