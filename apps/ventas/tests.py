"""
Pruebas de ventas: confirmacion (FIFO), anulacion (restaura capas) y validacion
de stock. Complementan las pruebas del Kardex en apps.inventario.

    python manage.py test apps.ventas
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.catalogos.models import CategoriaProducto, Producto, UnidadMedida
from apps.inventario.services import registrar_entrada, stock_disponible
from apps.ventas.models import AnulacionBoleta, DetalleVenta, Venta
from apps.ventas.services import VentaError, anular_venta, confirmar_venta


class VentaServiceTests(TestCase):
    def setUp(self):
        cat = CategoriaProducto.objects.create(nombre="Test")
        uni = UnidadMedida.objects.create(nombre="Unidad", abreviatura="UND")
        self.producto = Producto.objects.create(
            codigo_producto="P001", nombre="Artrim", categoria=cat, unidad_medida=uni
        )
        # Stock inicial: 10@2.00 + 20@3.00 = 30 unidades
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 2)

    def _entrada(self, cantidad, costo, dia):
        registrar_entrada(
            producto=self.producto, cantidad=Decimal(cantidad),
            costo_unitario=Decimal(costo), tipo="COMPRA",
            referencia_tipo="COMPRA", referencia_id=1,
            fecha_ingreso=date(2026, 1, dia), origen="COMPRA",
        )

    def _venta_borrador(self, cantidad, precio):
        venta = Venta.objects.create(estado="BORRADOR")
        DetalleVenta.objects.create(
            venta=venta, producto=self.producto,
            cantidad=Decimal(cantidad), precio_unitario=Decimal(precio),
        )
        return venta

    def test_confirmar_descuenta_fifo_y_guarda_costo(self):
        venta = self._venta_borrador("15", "5.00")
        confirmar_venta(venta.id)
        venta.refresh_from_db()
        det = venta.detalles.first()
        self.assertEqual(venta.estado, "CONFIRMADA")
        self.assertEqual(venta.total_venta, Decimal("75.0000"))  # 15 * 5.00
        # FIFO: 10@2.00 + 5@3.00 = 35.00 de costo de salida
        self.assertEqual(det.costo_total_salida, Decimal("35.0000"))
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

    def test_anular_restaura_capas_y_no_elimina(self):
        venta = self._venta_borrador("15", "5.00")
        confirmar_venta(venta.id)
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

        anular_venta(venta.id, motivo="Error de registro")
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "ANULADA")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))
        self.assertTrue(AnulacionBoleta.objects.filter(venta=venta).exists())
        self.assertTrue(Venta.objects.filter(pk=venta.id).exists())  # no se borra

    def test_stock_insuficiente_no_confirma(self):
        venta = self._venta_borrador("100", "5.00")
        with self.assertRaises(VentaError):
            confirmar_venta(venta.id)
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "BORRADOR")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

    def test_no_se_confirma_dos_veces(self):
        venta = self._venta_borrador("5", "5.00")
        confirmar_venta(venta.id)
        with self.assertRaises(VentaError):
            confirmar_venta(venta.id)

    def test_solo_se_anulan_ventas_confirmadas(self):
        venta = self._venta_borrador("5", "5.00")
        with self.assertRaises(VentaError):
            anular_venta(venta.id)
