"""Persistencia relacional: mismo contrato que memoria, round-trip de aggregates, atomicidad y flujo completo.

Siempre corre contra SQLite en memoria. Si existe TEST_DATABASE_URL (p. ej. PostgreSQL), corre TAMBIÉN contra esa base:
    TEST_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/sazon_test python -m unittest discover
"""
import os
import unittest
from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import func, select

from sazon_urbano.application import comandos as c
from sazon_urbano.domain.errores import (
    EntregaNoEncontrada, PedidoNoEncontrado, PromocionNoEncontrada, RepartidorNoEncontrado,
)
from sazon_urbano.domain.pedido import EstadoPedido, EstadoPreparacion
from sazon_urbano.domain.promocion import Promocion
from sazon_urbano.domain.repartidor import Repartidor
from sazon_urbano.domain.errores import MontoMinimoDomicilioNoAlcanzado
from sazon_urbano.domain.valores import Canal, EstacionCocina, TipoCancelacion, Vigencia
from sazon_urbano.infrastructure.composicion import construir_aplicacion_sql
from sazon_urbano.infrastructure.persistence.base_datos import (
    borrar_tablas, crear_engine, crear_session_factory, crear_tablas, url_desde_entorno,
)
from sazon_urbano.infrastructure.persistence.modelos import (
    CancelacionRow, EntregaRow, MermaRow, PedidoRow, ProductoAgotadoRow,
)

from ..escenario import (
    AGUA, CAJA, CLIENTE_DOMICILIO, COCINA, ENCARGADO, MARTES_19H, MESERO, REPARTIDOR, TACOS, REFRESCO,
)


class _PersistenciaBase:
    URL = "sqlite://"

    @classmethod
    def setUpClass(cls):
        cls.engine = crear_engine(cls.URL)
        cls.sesiones = crear_session_factory(cls.engine)

    @classmethod
    def tearDownClass(cls):
        borrar_tablas(cls.engine)
        cls.engine.dispose()

    def setUp(self):
        borrar_tablas(self.engine)
        crear_tablas(self.engine)
        self.session = self.sesiones()
        self.app = construir_aplicacion_sql(self.session)
        self.app.promociones.guardar(Promocion("promo-martes", "Martes de tacos",
                                               Vigencia(frozenset({1}), time(18), time(21)), {"taco-pastor"}, 20))
        self.app.repartidores.guardar(Repartidor("rep-1", "Pedro"))
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def otra_sesion(self):
        """Simula reiniciar la aplicación: una sesión nueva solo ve lo que quedó confirmado."""
        sesion = self.sesiones()
        self.addCleanup(sesion.close)  # una sesión abierta bloquearía el DROP TABLE de la siguiente prueba en PostgreSQL
        return construir_aplicacion_sql(sesion)

    def registrar_mesa(self):
        return self.app.pedidos_svc.registrar_pedido(
            c.RegistrarPedido(Canal.MESA, [TACOS, REFRESCO], MESERO, mesa="5"))


class PruebasDePersistencia(_PersistenciaBase):
    # -- contrato común (principio L) -------------------------------------------
    def test_obtener_por_id_inexistente_lanza_error_de_negocio(self):
        with self.assertRaises(PedidoNoEncontrado):
            self.app.pedidos.obtener_por_id("no-existe")
        with self.assertRaises(PromocionNoEncontrada):
            self.app.promociones.obtener_por_id("no-existe")
        with self.assertRaises(EntregaNoEncontrada):
            self.app.entregas.obtener_por_id("no-existe")
        with self.assertRaises(RepartidorNoEncontrado):
            self.app.repartidores.obtener_por_id("no-existe")

    # -- round-trip -------------------------------------------------------------
    def test_el_pedido_sobrevive_a_una_sesion_nueva_con_todos_sus_datos(self):
        resultado = self.registrar_mesa()
        self.assertEqual(resultado.total.monto, Decimal("210"))
        otra = self.otra_sesion()
        pedido = otra.pedidos.obtener_por_id(resultado.pedido_id)
        self.assertIs(pedido.estado, EstadoPedido.ACEPTADO)
        self.assertEqual(pedido.total.monto, Decimal("210.00"))
        self.assertEqual([(l.producto.producto_id, l.cantidad) for l in pedido.lineas],
                         [("taco-pastor", 2), ("refresco", 1)])           # conserva el orden
        self.assertEqual(pedido.mesa, "5")
        self.assertEqual(pedido.responsable, MESERO)                      # RN-14
        self.assertEqual(set(pedido.preparaciones), {EstacionCocina.PARRILLA, EstacionCocina.BEBIDAS})
        self.assertEqual(pedido.recoger_eventos(), [])                    # reconstruir no emite eventos

    def test_promocion_aplicada_y_total_recalculado_persisten(self):
        pedido_id = self.registrar_mesa().pedido_id
        self.app.pedidos_svc.aplicar_promocion(c.AplicarPromocion(pedido_id, "promo-martes", MARTES_19H, CAJA))
        pedido = self.otra_sesion().pedidos.obtener_por_id(pedido_id)
        self.assertEqual(pedido.promocion.promocion_id, "promo-martes")
        self.assertEqual(pedido.total.monto, Decimal("174.00"))           # 210 - 20 % de 180

    def test_la_promocion_conserva_vigencia_y_productos(self):
        promo = self.otra_sesion().promociones.obtener_por_id("promo-martes")
        self.assertEqual(promo.vigencia, Vigencia(frozenset({1}), time(18), time(21)))
        self.assertEqual(promo.productos_ids, frozenset({"taco-pastor"}))
        self.assertEqual(promo.porcentaje_descuento, Decimal("20"))

    def test_quitar_linea_actualiza_las_lineas_y_registra_cancelacion_parcial(self):
        resultado = self.registrar_mesa()
        pedido = self.app.pedidos.obtener_por_id(resultado.pedido_id)
        linea = pedido.lineas[0]
        self.app.disponibilidad_svc.gestionar_producto_agotado(c.MarcarProductoAgotado("taco-pastor", COCINA))
        self.app.disponibilidad_svc.gestionar_producto_agotado(c.QuitarLineaAgotada(resultado.pedido_id, linea.id, MESERO))
        recargado = self.otra_sesion().pedidos.obtener_por_id(resultado.pedido_id)
        self.assertEqual(len(recargado.lineas), 1)
        self.assertEqual(recargado.total.monto, Decimal("30"))
        self.assertEqual([x.tipo for x in recargado.cancelaciones], [TipoCancelacion.PARCIAL])

    def test_producto_agotado_persiste(self):
        self.app.disponibilidad_svc.gestionar_producto_agotado(c.MarcarProductoAgotado("taco-pastor", COCINA))
        otra = self.otra_sesion()
        self.assertTrue(otra.disponibilidad.esta_agotado("taco-pastor"))
        self.assertFalse(otra.disponibilidad.esta_agotado("refresco"))

    # -- CU-03: atomicidad pedido + merma --------------------------------------
    def _en_preparacion(self):
        pedido_id = self.registrar_mesa().pedido_id
        pedido = self.app.pedidos.obtener_por_id(pedido_id)
        pedido.iniciar_preparacion(EstacionCocina.PARRILLA)
        self.app.pedidos.guardar(pedido)
        self.session.commit()
        return pedido_id

    def test_cancelacion_tardia_autorizada_guarda_pedido_y_merma_juntos(self):
        pedido_id = self._en_preparacion()
        r = self.app.pedidos_svc.cancelar_pedido(c.CancelarPedido(pedido_id, "Se fue el cliente", MESERO, ENCARGADO))
        self.assertTrue(r.genero_merma)
        with self.sesiones() as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(MermaRow)), 1)
            self.assertEqual(s.get(PedidoRow, pedido_id).estado, "cancelado")
            self.assertEqual(s.scalar(select(func.count()).select_from(CancelacionRow)), 1)

    def test_si_falla_guardar_la_merma_no_queda_un_pedido_cancelado_rn03(self):
        pedido_id = self._en_preparacion()
        self.app.mermas.guardar = lambda merma: (_ for _ in ()).throw(RuntimeError("falla técnica"))
        with self.assertRaises(RuntimeError):
            self.app.pedidos_svc.cancelar_pedido(c.CancelarPedido(pedido_id, "x", MESERO, ENCARGADO))
        with self.sesiones() as s:
            self.assertEqual(s.get(PedidoRow, pedido_id).estado, "en_preparacion")
            self.assertEqual(s.scalar(select(func.count()).select_from(MermaRow)), 0)
            self.assertEqual(s.scalar(select(func.count()).select_from(CancelacionRow)), 0)

    def test_registro_rechazado_no_deja_nada_guardado_rn01(self):
        with self.assertRaises(MontoMinimoDomicilioNoAlcanzado):
            self.app.pedidos_svc.registrar_pedido(c.RegistrarPedido(Canal.DOMICILIO, [AGUA], CAJA, cliente=CLIENTE_DOMICILIO))
        with self.sesiones() as s:
            self.assertEqual(s.scalar(select(func.count()).select_from(PedidoRow)), 0)

    # -- CU-05: entrega completa (Pedido + Entrega + Repartidor) ----------------
    def test_flujo_de_entrega_a_domicilio_completo(self):
        pedido_id = self.app.pedidos_svc.registrar_pedido(
            c.RegistrarPedido(Canal.DOMICILIO, [TACOS], CAJA, cliente=CLIENTE_DOMICILIO)).pedido_id
        pedido = self.app.pedidos.obtener_por_id(pedido_id)
        pedido.iniciar_preparacion(EstacionCocina.PARRILLA)
        pedido.marcar_listo()
        self.app.pedidos.guardar(pedido)
        self.session.commit()

        entrega = self.app.entregas_svc.gestionar_entrega(c.AsignarRepartidor(pedido_id, "rep-1", ENCARGADO))
        self.assertFalse(self.otra_sesion().repartidores.obtener_por_id("rep-1").disponible)
        self.app.entregas_svc.gestionar_entrega(c.RegistrarSalidaDeEntrega(entrega.entrega_id, REPARTIDOR, datetime(2026, 11, 2, 20, 0)))
        self.app.entregas_svc.gestionar_entrega(c.ConfirmarEntrega(entrega.entrega_id, REPARTIDOR, datetime(2026, 11, 2, 20, 20)))

        otra = self.otra_sesion()
        self.assertIs(otra.pedidos.obtener_por_id(pedido_id).estado, EstadoPedido.ENTREGADO)
        self.assertTrue(otra.repartidores.obtener_por_id("rep-1").disponible)
        with self.sesiones() as s:
            fila = s.get(EntregaRow, entrega.entrega_id)
            self.assertEqual((fila.estado, fila.hora_salida, fila.hora_entrega),
                             ("entregada", datetime(2026, 11, 2, 20, 0), datetime(2026, 11, 2, 20, 20)))  # RN-11


class TestPersistenciaSqlite(PruebasDePersistencia, unittest.TestCase):
    URL = "sqlite://"


@unittest.skipUnless(os.environ.get("TEST_DATABASE_URL"), "defina TEST_DATABASE_URL para probar contra PostgreSQL")
class TestPersistenciaPostgres(PruebasDePersistencia, unittest.TestCase):
    URL = os.environ.get("TEST_DATABASE_URL", "")


class TestConfiguracion(unittest.TestCase):
    def test_database_url_tiene_prioridad(self):
        self.assertEqual(url_desde_entorno({"DATABASE_URL": "sqlite:///x.db", "DB_HOST": "db"}), "sqlite:///x.db")

    def test_construye_url_de_postgres_con_variables_db(self):
        url = url_desde_entorno({"DB_HOST": "db", "DB_PORT": "5433", "DB_NAME": "n", "DB_USER": "u", "DB_PASSWORD": "p@ss"})
        self.assertEqual(url, "postgresql+psycopg://u:p%40ss@db:5433/n")

    def test_sin_configuracion_usa_sqlite_local(self):
        self.assertTrue(url_desde_entorno({}).startswith("sqlite:///"))


if __name__ == "__main__":
    unittest.main()
