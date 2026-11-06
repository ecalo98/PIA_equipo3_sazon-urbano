"""Casos de borde del dominio: estados finales, estados incorrectos y valores inválidos."""
import unittest
from datetime import datetime
from decimal import Decimal

from sazon_urbano.domain.entrega import Entrega
from sazon_urbano.domain.errores import (
    EntregaSinSalidaRegistrada, OperacionNoPermitidaEnEstado, TransicionDeEstadoInvalida,
)
from sazon_urbano.domain.evaluacion import OperacionEvaluable
from sazon_urbano.domain.pedido import EstadoPedido, LineaPedido, Pedido
from sazon_urbano.domain.specifications import ActorActivo, Autorizado, PromocionActiva, puede_procesarse
from sazon_urbano.domain.valores import (
    Canal, Dinero, EstacionCocina, ProductoPedido, PromocionAplicada, Responsable, Rol,
)

CAJA = Responsable("caja", Rol.CAJA)


def op(**cambios) -> OperacionEvaluable:
    base = dict(operacion_id="X", actor_activo=True, actor_preferente=False, num_lineas=1,
                total=Dinero.mxn(500), autorizado=True, promocion_activa=False)
    base.update(cambios)
    return OperacionEvaluable(**base)


def pedido_con_dos_estaciones() -> Pedido:
    lineas = [
        LineaPedido("L1", ProductoPedido("taco", "Tacos", Dinero.mxn(90)), 2, EstacionCocina.PARRILLA),
        LineaPedido("L2", ProductoPedido("refresco", "Refresco", Dinero.mxn(30)), 1, EstacionCocina.BEBIDAS),
    ]
    pedido = Pedido.crear("P1", Canal.MESA, CAJA, lineas, mesa="1")
    pedido.confirmar()
    return pedido


class TestSpecificationsExplicacion(unittest.TestCase):
    def test_o_explica_cuando_ninguna_alternativa_se_cumple(self):
        spec = ActorActivo() | PromocionActiva()
        self.assertEqual(spec.motivos_de_rechazo(op()), [])  # se cumple la primera
        motivos = spec.motivos_de_rechazo(op(actor_activo=False))
        self.assertEqual(len(motivos), 1)
        self.assertIn("ninguna alternativa", motivos[0])

    def test_no_explica_que_se_cumplio_lo_que_no_debia(self):
        spec = ~PromocionActiva()
        self.assertEqual(spec.motivos_de_rechazo(op()), [])
        self.assertIn("promoción activa", spec.motivos_de_rechazo(op(promocion_activa=True))[0])

    def test_descripcion_y_representacion_legibles(self):
        regla = puede_procesarse()
        self.assertEqual(regla.descripcion, "((actor activo Y al menos una línea de detalle) Y autorización registrada)")
        self.assertEqual(repr(Autorizado()), "<autorización registrada>")
        self.assertEqual(Autorizado().descripcion, "autorización registrada")


class TestValoresInvalidos(unittest.TestCase):
    def test_el_dinero_no_puede_ser_negativo(self):
        with self.assertRaises(ValueError):
            Dinero(Decimal("-0.01"))


class TestEstadosFinalesDelPedido(unittest.TestCase):
    def setUp(self):
        self.pedido = pedido_con_dos_estaciones()
        self.pedido.cancelar(CAJA, "Error de captura")

    def test_un_pedido_cancelado_no_acepta_promocion(self):
        with self.assertRaises(OperacionNoPermitidaEnEstado):
            self.pedido.aplicar_promocion(PromocionAplicada("p", "Promo", Dinero.mxn(10)))

    def test_un_pedido_cancelado_no_acepta_quitar_lineas(self):
        with self.assertRaises(OperacionNoPermitidaEnEstado):
            self.pedido.quitar_linea("L1", True, CAJA)

    def test_un_pedido_cancelado_no_inicia_preparacion(self):
        with self.assertRaises(TransicionDeEstadoInvalida):
            self.pedido.iniciar_preparacion(EstacionCocina.PARRILLA)


class TestPreparacionPorEstacion(unittest.TestCase):
    def test_la_segunda_estacion_no_cambia_el_estado_pero_si_emite_evento(self):
        pedido = pedido_con_dos_estaciones()
        pedido.recoger_eventos()
        pedido.iniciar_preparacion(EstacionCocina.PARRILLA)
        pedido.iniciar_preparacion(EstacionCocina.BEBIDAS)
        self.assertIs(pedido.estado, EstadoPedido.EN_PREPARACION)
        self.assertEqual([e.estacion for e in pedido.recoger_eventos()], ["parrilla", "bebidas"])


class TestEstadosDeLaEntrega(unittest.TestCase):
    def test_la_salida_solo_se_registra_una_vez(self):
        entrega = Entrega.asignar("E1", "P1", "R1")
        entrega.registrar_salida(datetime(2026, 11, 2, 20, 0))
        with self.assertRaises(OperacionNoPermitidaEnEstado):
            entrega.registrar_salida(datetime(2026, 11, 2, 20, 1))

    def test_no_puede_fallar_sin_haber_salido_rn11(self):
        with self.assertRaises(EntregaSinSalidaRegistrada):
            Entrega.asignar("E1", "P1", "R1").fallar("Cliente ausente", datetime(2026, 11, 2, 20, 0))


if __name__ == "__main__":
    unittest.main()
