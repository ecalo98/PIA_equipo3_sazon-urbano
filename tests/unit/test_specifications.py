"""Pruebas unitarias del patrón Specification (AND / OR / NOT y motivos de rechazo)."""
import unittest
from decimal import Decimal

from sazon_urbano.domain.evaluacion import OperacionEvaluable
from sazon_urbano.domain.specifications import (
    ActorActivo, ActorPreferente, Autorizado, MontoMinimoDomicilio, PromocionActiva,
    TieneLineas, TotalMinimo, beneficio_referencia, puede_procesarse,
)
from sazon_urbano.domain.valores import Canal, Dinero


def operacion(**cambios) -> OperacionEvaluable:
    base = dict(operacion_id="X", actor_activo=True, actor_preferente=False, num_lineas=1,
                total=Dinero.mxn(500), autorizado=True, promocion_activa=False, canal=None)
    base.update(cambios)
    return OperacionEvaluable(**base)


class TestSpecificationsSimples(unittest.TestCase):
    def test_cada_specification_responde_su_pregunta(self):
        self.assertTrue(ActorActivo().es_satisfecha_por(operacion()))
        self.assertFalse(ActorActivo().es_satisfecha_por(operacion(actor_activo=False)))
        self.assertFalse(TieneLineas().es_satisfecha_por(operacion(num_lineas=0)))
        self.assertFalse(Autorizado().es_satisfecha_por(operacion(autorizado=False)))
        self.assertTrue(PromocionActiva().es_satisfecha_por(operacion(promocion_activa=True)))
        self.assertTrue(ActorPreferente().es_satisfecha_por(operacion(actor_preferente=True)))

    def test_total_minimo_incluye_el_limite(self):
        spec = TotalMinimo(Dinero.mxn(1500))
        self.assertTrue(spec.es_satisfecha_por(operacion(total=Dinero.mxn("1500.00"))))
        self.assertFalse(spec.es_satisfecha_por(operacion(total=Dinero.mxn("1499.99"))))

    def test_monto_minimo_domicilio_solo_aplica_a_domicilio_rn01(self):
        spec = MontoMinimoDomicilio(Dinero.mxn(150))
        self.assertFalse(spec.es_satisfecha_por(operacion(canal=Canal.DOMICILIO, total=Dinero.mxn(149))))
        self.assertTrue(spec.es_satisfecha_por(operacion(canal=Canal.DOMICILIO, total=Dinero.mxn(150))))
        self.assertTrue(spec.es_satisfecha_por(operacion(canal=Canal.MESA, total=Dinero.mxn(10))))


class TestCombinadores(unittest.TestCase):
    def test_y_requiere_ambas(self):
        spec = ActorActivo() & Autorizado()
        self.assertTrue(spec.es_satisfecha_por(operacion()))
        self.assertFalse(spec.es_satisfecha_por(operacion(autorizado=False)))

    def test_o_requiere_al_menos_una(self):
        spec = ActorPreferente() | PromocionActiva()
        self.assertFalse(spec.es_satisfecha_por(operacion()))
        self.assertTrue(spec.es_satisfecha_por(operacion(promocion_activa=True)))
        self.assertTrue(spec.es_satisfecha_por(operacion(actor_preferente=True)))

    def test_no_invierte(self):
        self.assertTrue((~PromocionActiva()).es_satisfecha_por(operacion()))
        self.assertFalse((~PromocionActiva()).es_satisfecha_por(operacion(promocion_activa=True)))

    def test_metodos_y_operadores_son_equivalentes(self):
        a, b = ActorActivo(), Autorizado()
        for op in (operacion(), operacion(actor_activo=False), operacion(autorizado=False)):
            self.assertEqual((a & b).es_satisfecha_por(op), a.y(b).es_satisfecha_por(op))
            self.assertEqual((a | b).es_satisfecha_por(op), a.o(b).es_satisfecha_por(op))
            self.assertEqual((~a).es_satisfecha_por(op), a.no().es_satisfecha_por(op))

    def test_leyes_de_de_morgan(self):
        a, b = ActorActivo(), Autorizado()
        for activo in (True, False):
            for autorizado in (True, False):
                op = operacion(actor_activo=activo, autorizado=autorizado)
                self.assertEqual((~(a & b)).es_satisfecha_por(op), ((~a) | (~b)).es_satisfecha_por(op))


class TestReglasDelPaquete(unittest.TestCase):
    def test_puede_procesarse(self):
        regla = puede_procesarse()
        self.assertTrue(regla.es_satisfecha_por(operacion()))
        self.assertFalse(regla.es_satisfecha_por(operacion(actor_activo=False)))
        self.assertFalse(regla.es_satisfecha_por(operacion(num_lineas=0)))
        self.assertFalse(regla.es_satisfecha_por(operacion(autorizado=False)))

    def test_beneficio_referencia_es_solo_elegibilidad_y_no_modifica_el_total(self):
        op = operacion(actor_preferente=True, total=Dinero.mxn(1500))
        self.assertTrue(beneficio_referencia().es_satisfecha_por(op))
        self.assertEqual(op.total.monto, Decimal("1500"))  # decisión A: nunca aplica descuento
        self.assertFalse(beneficio_referencia().es_satisfecha_por(operacion(actor_preferente=True, total=Dinero.mxn(1500), promocion_activa=True)))
        self.assertFalse(beneficio_referencia().es_satisfecha_por(operacion(actor_preferente=False, total=Dinero.mxn(1500))))
        self.assertFalse(beneficio_referencia().es_satisfecha_por(operacion(actor_preferente=True, total=Dinero.mxn(1499))))

    def test_motivos_de_rechazo_indican_que_condicion_fallo(self):
        motivos = puede_procesarse().motivos_de_rechazo(operacion(actor_activo=False, autorizado=False))
        self.assertEqual(len(motivos), 2)
        self.assertIn("No cumple: actor activo", motivos)
        self.assertIn("No cumple: autorización registrada", motivos)
        self.assertEqual(puede_procesarse().motivos_de_rechazo(operacion()), [])


if __name__ == "__main__":
    unittest.main()
