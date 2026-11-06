"""Integración: las Specifications contra los 120 casos del paquete del PIA.

El oráculo se calcula con Python plano (sin usar Specifications) para que la comparación sea independiente.
"""
import unittest
from decimal import Decimal

from sazon_urbano.domain.specifications import beneficio_referencia, puede_procesarse
from sazon_urbano.infrastructure.paquete_pia import PaquetePia


class TestPaquetePia(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paquete = PaquetePia()

    def test_carga_los_volumenes_esperados(self):
        self.assertEqual(len(self.paquete.operaciones), 60)
        self.assertEqual(len(self.paquete.casos_prueba), 120)
        self.assertEqual(len(self.paquete.transiciones), 20)

    def test_el_total_usa_decimal_y_coincide_con_la_suma_de_lineas(self):
        for op in self.paquete.operaciones.values():
            self.assertIsInstance(op.total.monto, Decimal)
        self.assertEqual(self.paquete.operaciones["PED-O013"].total.monto, Decimal("0"))  # sin líneas

    def test_los_120_casos_coinciden_con_el_oraculo_independiente(self):
        for caso in self.paquete.casos_prueba:
            op = self.paquete.operaciones[caso["operacion_id"]]
            if caso["tipo_prueba"] == "validar_operacion":
                esperado = op.actor_activo and op.num_lineas > 0 and op.autorizado
                obtenido = puede_procesarse().es_satisfecha_por(op)
            else:
                esperado = op.actor_preferente and op.total.monto >= Decimal("1500") and not op.promocion_activa
                obtenido = beneficio_referencia().es_satisfecha_por(op)
            self.assertEqual(obtenido, esperado, caso["caso_id"])

    def test_totales_de_los_casos(self):
        validos = sum(puede_procesarse().es_satisfecha_por(self.paquete.operaciones[c["operacion_id"]])
                      for c in self.paquete.casos_prueba if c["tipo_prueba"] == "validar_operacion")
        con_beneficio = sum(beneficio_referencia().es_satisfecha_por(self.paquete.operaciones[c["operacion_id"]])
                            for c in self.paquete.casos_prueba if c["tipo_prueba"] == "evaluar_beneficio")
        self.assertEqual((validos, con_beneficio), (47, 9))

    def test_casos_limite_conocidos(self):
        ops = self.paquete.operaciones
        self.assertFalse(puede_procesarse().es_satisfecha_por(ops["PED-O013"]))  # sin líneas
        self.assertFalse(puede_procesarse().es_satisfecha_por(ops["PED-O029"]))  # actor inactivo
        self.assertFalse(puede_procesarse().es_satisfecha_por(ops["PED-O008"]))  # sin autorización


if __name__ == "__main__":
    unittest.main()
