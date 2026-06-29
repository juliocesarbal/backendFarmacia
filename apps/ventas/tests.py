"""
Pruebas de ventas: flujo CAJA FACULTATIVA (registrar comprobante -> verificar
pago -> entregar descuenta FIFO) y anulacion (restaura capas).

    python manage.py test apps.ventas
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.catalogo.models import CategoriaProducto, Producto, UnidadMedida
from apps.inventario.services import registrar_entrada, stock_disponible
from apps.ventas.models import AnulacionBoleta, DetalleVenta, Venta
from apps.ventas.services import (
    VentaError,
    anular_venta,
    entregar_venta,
    registrar_comprobante,
    verificar_pago,
)


class VentaCajaFacultativaTests(TestCase):
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

    def _venta(self, cantidad, precio):
        venta = Venta.objects.create()
        sub = Decimal(cantidad) * Decimal(precio)
        DetalleVenta.objects.create(
            venta=venta, producto=self.producto,
            cantidad=Decimal(cantidad), precio_unitario=Decimal(precio), subtotal=sub,
        )
        venta.total_venta = sub
        venta.save(update_fields=["total_venta"])
        return venta

    def test_pendiente_no_descuenta_stock(self):
        self._venta("15", "5.00")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

    def test_flujo_completo_descuenta_al_entregar(self):
        venta = self._venta("15", "5.00")
        # No se puede entregar sin pago verificado
        with self.assertRaises(VentaError):
            entregar_venta(venta.id)

        registrar_comprobante(venta.id, {"monto_pagado": Decimal("75.00")})
        verificar_pago(venta.id)
        venta.refresh_from_db()
        self.assertEqual(venta.estado_pago, "PAGADA")
        # Aun pagada, sin entregar no se descuenta
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))

        entregar_venta(venta.id)
        venta.refresh_from_db()
        det = venta.detalles.first()
        self.assertEqual(venta.estado_entrega, "ENTREGADA")
        # FIFO: 10@2.00 + 5@3.00 = 35.00
        self.assertEqual(det.costo_total_salida, Decimal("35.0000"))
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

    def test_no_verifica_si_monto_insuficiente(self):
        venta = self._venta("15", "5.00")  # total 75
        registrar_comprobante(venta.id, {"monto_pagado": Decimal("50.00")})
        with self.assertRaises(VentaError):
            verificar_pago(venta.id)

    def test_anular_entregada_restaura_capas(self):
        venta = self._venta("15", "5.00")
        registrar_comprobante(venta.id, {"monto_pagado": Decimal("75.00")})
        verificar_pago(venta.id)
        entregar_venta(venta.id)
        self.assertEqual(stock_disponible(self.producto.id), Decimal("15.00"))

        anular_venta(venta.id, motivo="Error de registro")
        venta.refresh_from_db()
        self.assertEqual(venta.estado, "ANULADA")
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))
        self.assertTrue(AnulacionBoleta.objects.filter(venta=venta).exists())
        self.assertTrue(Venta.objects.filter(pk=venta.id).exists())  # no se borra

    def test_entregar_sin_stock_falla(self):
        venta = self._venta("100", "5.00")
        registrar_comprobante(venta.id, {"monto_pagado": Decimal("500.00")})
        verificar_pago(venta.id)
        with self.assertRaises(VentaError):
            entregar_venta(venta.id)
        self.assertEqual(stock_disponible(self.producto.id), Decimal("30.00"))
