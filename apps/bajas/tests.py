"""
Pruebas de bajas: la confirmacion es una salida valorada por FIFO (RN-03/04).

    python manage.py test apps.bajas
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.bajas.models import Baja, DetalleBaja, MotivoBaja
from apps.bajas.services import BajaError, confirmar_baja
from apps.catalogos.models import CategoriaProducto, Producto, UnidadMedida
from apps.inventario.services import registrar_entrada, stock_disponible


class BajaServiceTests(TestCase):
    def setUp(self):
        cat = CategoriaProducto.objects.create(nombre="Test")
        uni = UnidadMedida.objects.create(nombre="Unidad", abreviatura="UND")
        self.producto = Producto.objects.create(
            codigo_producto="P001", nombre="Artrim", categoria=cat, unidad_medida=uni
        )
        self.motivo = MotivoBaja.objects.create(nombre="Vencimiento")
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 2)

    def _entrada(self, cantidad, costo, dia):
        registrar_entrada(
            producto=self.producto, cantidad=Decimal(cantidad),
            costo_unitario=Decimal(costo), tipo="COMPRA",
            referencia_tipo="COMPRA", referencia_id=1,
            fecha_ingreso=date(2026, 1, dia), origen="COMPRA",
        )

    def _baja_borrador(self, cantidad):
        baja = Baja.objects.create(estado="BORRADOR", motivo_baja=self.motivo)
        DetalleBaja.objects.create(baja=baja, producto=self.producto, cantidad=Decimal(cantidad))
        return baja

    def test_confirmar_consume_fifo_y_valora(self):
        baja = self._baja_borrador("15")
        confirmar_baja(baja.id)
        baja.refresh_from_db()
        det = baja.detalles.first()
        self.assertEqual(baja.estado, "CONFIRMADA")
        # FIFO: 10@2.00 + 5@3.00 = 35.00
        self.assertEqual(det.costo_total_baja, Decimal("35.0000"))
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

    def test_stock_insuficiente_no_confirma(self):
        baja = self._baja_borrador("100")
        with self.assertRaises(BajaError):
            confirmar_baja(baja.id)
        baja.refresh_from_db()
        self.assertEqual(baja.estado, "BORRADOR")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

    def test_no_se_confirma_dos_veces(self):
        baja = self._baja_borrador("5")
        confirmar_baja(baja.id)
        with self.assertRaises(BajaError):
            confirmar_baja(baja.id)
