"""Infraestructura y API: semilla idempotente, catálogo, configuración y manejo de errores técnicos (500)."""
import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from sazon_urbano.api.errores import ErrorDeApi, codigo_para
from sazon_urbano.api.main import crear_app
from sazon_urbano.domain.errores import OperacionNoProcesable, PedidoNoEncontrado
from sazon_urbano.infrastructure.persistence import semilla
from sazon_urbano.infrastructure.persistence.base_datos import crear_engine, crear_session_factory, crear_tablas
from sazon_urbano.infrastructure.persistence.consultas_sql import CatalogoDePlatillosSql
from sazon_urbano.infrastructure.persistence.modelos import PlatilloRow, PromocionRow, RepartidorRow

MESERO = {"X-Usuario-Id": "ana", "X-Rol": "mesero"}


class TestSemillaYCatalogo(unittest.TestCase):
    def setUp(self):
        self.engine = crear_engine("sqlite://")
        crear_tablas(self.engine)
        self.session = crear_session_factory(self.engine)()

    def tearDown(self):
        self.session.close()

    def test_la_semilla_es_idempotente(self):
        semilla.cargar_catalogo(self.session)
        semilla.cargar_demo(self.session)
        semilla.cargar_catalogo(self.session)
        semilla.cargar_demo(self.session)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(PlatilloRow)), 26)  # 20 del paquete + 6 propios
        self.assertEqual(self.session.scalar(select(func.count()).select_from(PromocionRow)), 1)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(RepartidorRow)), 2)

    def test_el_catalogo_deduce_la_estacion_y_respeta_habilitado(self):
        semilla.cargar_catalogo(self.session)
        catalogo = CatalogoDePlatillosSql(self.session)
        self.assertEqual(len(catalogo.listar()), 26)
        self.assertEqual(catalogo.obtener("PED-P002").estacion.value, "fria")      # Ensalada
        self.assertEqual(catalogo.obtener("PED-P004").estacion.value, "bebidas")   # Bebida
        self.assertFalse(catalogo.obtener("PED-P011").habilitado)


class TestConfiguracion(unittest.TestCase):
    def test_crea_engine_de_postgresql_sin_conectarse(self):
        engine = crear_engine("postgresql+psycopg://u:p@localhost:5432/x")
        self.assertEqual(engine.dialect.name, "postgresql")

    def test_sembrar_por_defecto_y_desactivable_por_entorno(self):
        with mock.patch.dict(os.environ, {"SEMBRAR_DATOS": "0"}):
            self.assertEqual(TestClient(crear_app("sqlite://")).get("/menu").json(), [])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SEMBRAR_DATOS", None)
            self.assertEqual(len(TestClient(crear_app("sqlite://")).get("/menu").json()), 26)


class TestErroresHttp(unittest.TestCase):
    def setUp(self):
        self.app = crear_app("sqlite://", sembrar=False)

        @self.app.get("/_prueba/tecnico")
        def tecnico():
            raise RuntimeError("password=secreta conexion caida")

        @self.app.get("/_prueba/motivos")
        def motivos():
            raise OperacionNoProcesable(["No cumple: actor activo", "No cumple: autorización registrada"])

        @self.app.get("/_prueba/identidad")
        def identidad():
            raise ErrorDeApi(401, "NoIdentificado", "falta")

        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_un_error_tecnico_responde_500_sin_filtrar_detalles(self):
        r = self.client.get("/_prueba/tecnico")
        self.assertEqual((r.status_code, r.json()["error"]), (500, "ErrorTecnico"))
        self.assertNotIn("secreta", r.text)

    def test_un_error_de_negocio_con_motivos_los_incluye_en_la_respuesta(self):
        r = self.client.get("/_prueba/motivos")
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(r.json()["motivos"]), 2)

    def test_errores_de_la_capa_api(self):
        self.assertEqual(self.client.get("/_prueba/identidad").status_code, 401)

    def test_codigo_para_errores_desconocidos_es_500_y_los_de_negocio_422_o_404(self):
        self.assertEqual(codigo_para(RuntimeError()), 500)
        self.assertEqual(codigo_para(PedidoNoEncontrado("x")), 404)
        self.assertEqual(codigo_para(OperacionNoProcesable(["a"])), 422)


if __name__ == "__main__":
    unittest.main()
