"""
Pruebas obligatorias del Kardex valorado (guia seccion 16).

Ejecutar:
    python manage.py test apps.inventario
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.catalogos.models import CategoriaProducto, Producto, UnidadMedida
from apps.inventario.services import (
    crear_capa,
    registrar_entrada,
    registrar_salida,
    restaurar_capas,
    stock_disponible,
)
from apps.inventario.models import MovimientoInventario


class KardexFifoTests(TestCase):
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

    def test_caso1_dos_compras_costos_distintos(self):
        # Compra 10@2.00 + Compra 20@3.00, Venta 15
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 2)
        _, costo = registrar_salida(
            producto=self.producto, cantidad=Decimal("15"), tipo="VENTA",
            referencia_tipo="VENTA", referencia_id=1,
        )
        # Consume 10@2.00 + 5@3.00 = 20 + 15 = 35.00
        self.assertEqual(costo, Decimal("35.0000"))
        # Saldo: 15 unidades a 3.00 = 45.00
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

    def test_caso2_saldo_anterior_y_compra_nueva(self):
        # Saldo inicial 18@3.40 + compra 300@4.67, venta 38
        crear_capa(self.producto, Decimal("18"), Decimal("3.40"), date(2026, 1, 1), "IMPORTACION")
        MovimientoInventario.objects.create(
            producto=self.producto, sentido="ENTRADA", tipo_movimiento="IMPORTACION",
            cantidad=Decimal("18"), costo_unitario_aplicado=Decimal("3.40"),
            valor_movimiento=Decimal("61.20"),
        )
        self._entrada(300, "4.67", 2)
        _, costo = registrar_salida(
            producto=self.producto, cantidad=Decimal("38"), tipo="VENTA",
            referencia_tipo="VENTA", referencia_id=1,
        )
        # Consume 18@3.40 (61.20) + 20@4.67 (93.40) = 154.60
        self.assertEqual(costo, Decimal("154.6000"))
        # Saldo: 280 a 4.67
        self.assertEqual(stock_disponible(self.producto.id), Decimal("280.00"))

    def test_caso3_anulacion_restaura_capas(self):
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 2)
        mov, _ = registrar_salida(
            producto=self.producto, cantidad=Decimal("15"), tipo="VENTA",
            referencia_tipo="VENTA", referencia_id=1,
        )
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))
        # Anular -> restaura capas
        restaurar_capas(mov, motivo="Anulacion test")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

    def test_fifo_mismo_dia_respeta_orden_de_capa(self):
        # Dos capas creadas el MISMO dia: el FIFO debe desempatar por id
        # (orden de ingreso), no por costo. Regresion del bug E2E.
        self._entrada(10, "2.00", 1)
        self._entrada(20, "3.00", 1)  # mismo dia 1
        _, costo = registrar_salida(
            producto=self.producto, cantidad=Decimal("15"), tipo="VENTA",
            referencia_tipo="VENTA", referencia_id=1,
        )
        # Debe consumir 10@2.00 + 5@3.00 = 35.00, no 15@3.00 = 45.00
        self.assertEqual(costo, Decimal("35.0000"))

    def test_stock_insuficiente(self):
        from apps.inventario.services import StockInsuficienteError

        self._entrada(5, "2.00", 1)
        with self.assertRaises(StockInsuficienteError):
            registrar_salida(
                producto=self.producto, cantidad=Decimal("10"), tipo="VENTA",
                referencia_tipo="VENTA", referencia_id=1,
            )
