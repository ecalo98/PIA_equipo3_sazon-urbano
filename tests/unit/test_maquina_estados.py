"""Máquina de estados del Pedido y Domain Events que emite cada transición."""
import pathlib
import unittest

from sazon_urbano.application.aprobacion import aprobar_operacion
from sazon_urbano.domain import eventos as ev
from sazon_urbano.domain.errores import (
    CancelacionRequiereAutorizacion, OperacionNoProcesable, TransicionDeEstadoInvalida,
)
from sazon_urbano.domain.evaluacion import OperacionEvaluable
from sazon_urbano.domain.pedido import AccionPedido, EstadoPedido, LineaPedido, MAQUINA_PEDIDO, Pedido
from sazon_urbano.domain.valores import Canal, Dinero, EstacionCocina, ProductoPedido, Responsable, Rol

CAJA = Responsable("caja", Rol.CAJA)
ENCARGADO = Responsable("eva", Rol.ENCARGADO)
E_, A_ = EstadoPedido, AccionPedido


def pedido_nuevo(canal=Canal.MESA) -> Pedido:
    linea = LineaPedido("L1", ProductoPedido("p1", "Tacos", Dinero.mxn(200)), 1, EstacionCocina.PARRILLA)
    cliente = None
    if canal is Canal.DOMICILIO:
        from sazon_urbano.domain.valores import DatosCliente
        cliente = DatosCliente("Ana", "8112345678", "Calle 1")
    return Pedido.crear("P1", canal, CAJA, [linea], cliente=cliente, mesa="1" if canal is Canal.MESA else None)


def tipos(pedido):
    return [type(e) for e in pedido.recoger_eventos()]


class TestTablaDeTransiciones(unittest.TestCase):
    def test_flujo_feliz_completo(self):
        p = pedido_nuevo()
        self.assertIs(p.estado, E_.CREADO)
        p.confirmar()
        self.assertIs(p.estado, E_.ACEPTADO)
        p.iniciar_preparacion(EstacionCocina.PARRILLA)
        self.assertIs(p.estado, E_.EN_PREPARACION)
        p.marcar_listo()
        self.assertIs(p.estado, E_.LISTO)
        p.marcar_entregado()
        self.assertIs(p.estado, E_.ENTREGADO)

    def test_cada_estado_final_no_permite_ninguna_accion(self):
        for estado in (E_.ENTREGADO, E_.CANCELADO, E_.ENTREGA_NO_COMPLETADA):
            self.assertTrue(MAQUINA_PEDIDO.es_final(estado))
            for accion in AccionPedido:
                with self.assertRaises(TransicionDeEstadoInvalida):
                    MAQUINA_PEDIDO.transicionar(estado, accion)

    def test_toda_combinacion_fuera_de_la_tabla_se_rechaza(self):
        validas = {(o, a) for o, a, _ in MAQUINA_PEDIDO.transiciones()}
        for estado in EstadoPedido:
            for accion in AccionPedido:
                if (estado, accion) not in validas:
                    self.assertFalse(MAQUINA_PEDIDO.puede(estado, accion))
                    with self.assertRaises(TransicionDeEstadoInvalida):
                        MAQUINA_PEDIDO.transicionar(estado, accion)

    def test_no_se_puede_saltar_un_estado(self):
        p = pedido_nuevo()
        with self.assertRaises(TransicionDeEstadoInvalida) as ctx:
            p.iniciar_preparacion(EstacionCocina.PARRILLA)  # CREADO -> EN_PREPARACION
        self.assertIs(p.estado, E_.CREADO)
        self.assertIn(A_.ACEPTAR, ctx.exception.permitidas)
        p.confirmar()
        with self.assertRaises(TransicionDeEstadoInvalida):
            p.marcar_listo()  # ACEPTADO -> LISTO sin pasar por EN_PREPARACION
        with self.assertRaises(TransicionDeEstadoInvalida):
            p.marcar_entregado()

    def test_no_se_repite_una_aprobacion(self):
        p = pedido_nuevo()
        p.confirmar()
        with self.assertRaises(TransicionDeEstadoInvalida):
            p.confirmar()
        self.assertIs(p.estado, E_.ACEPTADO)

    def test_acciones_permitidas_por_estado(self):
        p = pedido_nuevo()
        self.assertEqual(set(p.acciones_permitidas), {A_.ACEPTAR, A_.CANCELAR})
        p.confirmar()
        self.assertEqual(set(p.acciones_permitidas), {A_.INICIAR_PREPARACION, A_.CANCELAR})

    def test_el_error_es_un_error_de_negocio_con_el_estado_y_la_accion(self):
        with self.assertRaises(TransicionDeEstadoInvalida) as ctx:
            MAQUINA_PEDIDO.transicionar(E_.CREADO, A_.ENTREGAR)
        self.assertIs(ctx.exception.estado, E_.CREADO)
        self.assertIs(ctx.exception.accion, A_.ENTREGAR)


class TestCancelacionYEstados(unittest.TestCase):
    def test_creado_se_cancela_sin_autorizacion_rn02(self):
        p = pedido_nuevo()
        p.cancelar(CAJA, "error de captura")
        self.assertIs(p.estado, E_.CANCELADO)

    def test_en_preparacion_exige_encargado_rn03_y_no_cambia_el_estado_si_falla(self):
        p = pedido_nuevo()
        p.confirmar()
        p.iniciar_preparacion(EstacionCocina.PARRILLA)
        with self.assertRaises(CancelacionRequiereAutorizacion):
            p.cancelar(CAJA, "cliente se fue")
        self.assertIs(p.estado, E_.EN_PREPARACION)
        p.cancelar(CAJA, "cliente se fue", ENCARGADO)
        self.assertIs(p.estado, E_.CANCELADO)

    def test_un_pedido_cancelado_no_se_vuelve_a_cancelar(self):
        p = pedido_nuevo()
        p.cancelar(CAJA, "x")
        with self.assertRaises(TransicionDeEstadoInvalida):
            p.cancelar(CAJA, "otra vez")


class TestDomainEvents(unittest.TestCase):
    def test_cada_transicion_emite_su_evento(self):
        p = pedido_nuevo(Canal.DOMICILIO)
        p.confirmar()
        p.iniciar_preparacion(EstacionCocina.PARRILLA)
        p.marcar_listo()
        p.marcar_entregado()
        self.assertEqual(tipos(p), [ev.PedidoConfirmado, ev.PreparacionIniciada, ev.PedidoListo, ev.PedidoEntregado])

    def test_entrega_fallida_emite_evento(self):
        p = pedido_nuevo(Canal.DOMICILIO)
        p.confirmar(); p.iniciar_preparacion(EstacionCocina.PARRILLA); p.marcar_listo(); p.recoger_eventos()
        p.marcar_entrega_no_completada()
        self.assertIs(p.estado, E_.ENTREGA_NO_COMPLETADA)
        self.assertEqual(tipos(p), [ev.PedidoEntregaNoCompletada])

    def test_una_transicion_rechazada_no_emite_eventos(self):
        p = pedido_nuevo()
        with self.assertRaises(TransicionDeEstadoInvalida):
            p.marcar_entregado()
        self.assertEqual(p.recoger_eventos(), [])

    def test_recoger_eventos_los_vacia(self):
        p = pedido_nuevo(); p.confirmar()
        self.assertEqual(len(p.recoger_eventos()), 1)
        self.assertEqual(p.recoger_eventos(), [])


class TestAprobacionConSpecification(unittest.TestCase):
    def operacion(self, **cambios):
        base = dict(operacion_id="X", actor_activo=True, actor_preferente=False, num_lineas=1,
                    total=Dinero.mxn(200), autorizado=True, promocion_activa=False)
        base.update(cambios)
        return OperacionEvaluable(**base)

    def test_aprueba_cuando_puede_procesarse(self):
        p = pedido_nuevo()
        aprobar_operacion(p, self.operacion())
        self.assertIs(p.estado, E_.ACEPTADO)

    def test_rechaza_con_motivos_y_el_pedido_sigue_en_creado(self):
        p = pedido_nuevo()
        with self.assertRaises(OperacionNoProcesable) as ctx:
            aprobar_operacion(p, self.operacion(actor_activo=False, autorizado=False))
        self.assertEqual(len(ctx.exception.motivos), 2)
        self.assertIs(p.estado, E_.CREADO)
        self.assertEqual(p.recoger_eventos(), [])


class TestDiagramaCoherenteConElCodigo(unittest.TestCase):
    def test_el_puml_versionado_coincide_con_la_tabla(self):
        ruta = pathlib.Path(__file__).resolve().parents[2] / "docs" / "architecture" / "diagramas" / "estados-pedido.puml"
        self.assertEqual(ruta.read_text(encoding="utf-8"), MAQUINA_PEDIDO.a_plantuml(E_.CREADO))


if __name__ == "__main__":
    unittest.main()
