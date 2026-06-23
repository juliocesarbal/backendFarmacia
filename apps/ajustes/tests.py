"""
Pruebas de ajustes:
  - POSITIVO crea capa de costo (entrada, RN-02)
  - NEGATIVO consume capas por FIFO (salida, RN-03/04)

    python manage.py test apps.ajustes
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.ajustes.models import AjusteInventario, DetalleAjuste
from apps.ajustes.services import AjusteError, confirmar_ajuste
from apps.catalogos.models import CategoriaProducto, Producto, UnidadMedida
from apps.inventario.models import CapaCosto
from apps.inventario.services import registrar_entrada, stock_disponible


class AjusteServiceTests(TestCase):
    def setUp(self):
        cat = CategoriaProducto.objects.create(nombre="Test")
        uni = UnidadMedida.objects.create(nombre="Unidad", abreviatura="UND")
        self.producto = Producto.objects.create(
            codigo_producto="P001", nombre="Artrim", categoria=cat, unidad_medida=uni
        )

    def _entrada(self, cantidad, costo, dia):
        registrar_entrada(
            producto=self.producto, cantidad=Decimal(cantidad),
            costo_unitario=Decimal(costo), tipo="COMPRA",
            referencia_tipo="COMPRA", referencia_id=1,
            fecha_ingreso=date(2026, 1, dia), origen="COMPRA",
        )

    def _ajuste(self, tipo, cantidad, costo="0", motivo="Conteo fisico"):
        ajuste = AjusteInventario.objects.create(
            tipo_ajuste=tipo, estado="BORRADOR", motivo=motivo
        )
        DetalleAjuste.objects.create(
            ajuste=ajuste, producto=self.producto,
            cantidad=Decimal(cantidad), costo_unitario=Decimal(costo),
        )
        return ajuste

    def test_positivo_crea_capa_y_aumenta_stock(self):
        ajuste = self._ajuste("POSITIVO", "10", "5.00")
        confirmar_ajuste(ajuste.id)
        ajuste.refresh_from_db()
        self.assertEqual(ajuste.estado, "CONFIRMADO")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("10.00"))
        self.assertEqual(
            CapaCosto.objects.filter(producto=self.producto, origen="AJUSTE").count(), 1
        )
        det = ajuste.detalles.first()
        self.assertEqual(det.costo_total, Decimal("50.0000"))  # 10 * 5.00

    def test_negativo_consume_fifo(self):
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 2)
        ajuste = self._ajuste("NEGATIVO", "15")
        confirmar_ajuste(ajuste.id)
        ajuste.refresh_from_db()
        det = ajuste.detalles.first()
        # FIFO: 10@2.00 + 5@3.00 = 35.00
        self.assertEqual(det.costo_total, Decimal("35.0000"))
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

    def test_negativo_sin_stock_falla(self):
        ajuste = self._ajuste("NEGATIVO", "5")
        with self.assertRaises(AjusteError):
            confirmar_ajuste(ajuste.id)

    def test_requiere_motivo(self):
        ajuste = self._ajuste("POSITIVO", "10", "5.00", motivo="")
        with self.assertRaises(AjusteError):
            confirmar_ajuste(ajuste.id)
