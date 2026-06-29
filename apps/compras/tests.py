"""
Pruebas de compras: confirmar genera una capa de costo y un movimiento de
entrada por cada detalle (RN-02), conservando el costo historico.

    python manage.py test apps.compras
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.catalogo.models import CategoriaProducto, Producto, UnidadMedida
from apps.compras.models import Compra, DetalleCompra
from apps.compras.services import CompraError, confirmar_compra
from apps.inventario.models import CapaCosto, MovimientoInventario
from apps.inventario.services import stock_disponible
from apps.compras.models import Proveedor


class CompraServiceTests(TestCase):
    def setUp(self):
        cat = CategoriaProducto.objects.create(nombre="Test")
        uni = UnidadMedida.objects.create(nombre="Unidad", abreviatura="UND")
        self.producto = Producto.objects.create(
            codigo_producto="P001", nombre="Artrim", categoria=cat, unidad_medida=uni
        )
        self.proveedor = Proveedor.objects.create(nombre="Proveedor SA")

    def _compra(self, cantidad, costo):
        compra = Compra.objects.create(
            estado="BORRADOR", proveedor=self.proveedor, fecha_compra=date(2026, 1, 1)
        )
        DetalleCompra.objects.create(
            compra=compra, producto=self.producto,
            cantidad=Decimal(cantidad), costo_unitario=Decimal(costo),
        )
        return compra

    def test_confirmar_crea_capa_y_entrada(self):
        compra = self._compra("100", "4.67")
        confirmar_compra(compra.id)
        compra.refresh_from_db()
        det = compra.detalles.first()
        self.assertEqual(compra.estado, "CONFIRMADA")
        self.assertEqual(compra.total_compra, Decimal("467.0000"))  # 100 * 4.67
        self.assertEqual(det.costo_total, Decimal("467.0000"))
        self.assertEqual(stock_disponible(self.producto.id), Decimal("100.00"))

        capa = CapaCosto.objects.get(producto=self.producto, origen="COMPRA")
        self.assertEqual(capa.costo_unitario, Decimal("4.6700"))
        self.assertEqual(capa.cantidad_disponible, Decimal("100.00"))
        self.assertTrue(
            MovimientoInventario.objects.filter(
                producto=self.producto, tipo_movimiento="COMPRA", sentido="ENTRADA"
            ).exists()
        )

    def test_dos_compras_generan_dos_capas(self):
        confirmar_compra(self._compra("10", "2.00").id)
        confirmar_compra(self._compra("20", "3.00").id)
        self.assertEqual(CapaCosto.objects.filter(producto=self.producto).count(), 2)
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

    def test_no_confirma_sin_detalles(self):
        compra = Compra.objects.create(
            estado="BORRADOR", proveedor=self.proveedor, fecha_compra=date(2026, 1, 1)
        )
        with self.assertRaises(CompraError):
            confirmar_compra(compra.id)

    def test_no_se_confirma_dos_veces(self):
        compra = self._compra("10", "2.00")
        confirmar_compra(compra.id)
        with self.assertRaises(CompraError):
            confirmar_compra(compra.id)
