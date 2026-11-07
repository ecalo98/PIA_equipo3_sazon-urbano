"""Importación de los 60 pedidos del dataset a la base de datos, con claves foráneas."""
import unittest

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from sazon_urbano.infrastructure.persistence import semilla
from sazon_urbano.infrastructure.persistence.base_datos import (
    _normalizar_url, crear_engine, crear_session_factory, crear_tablas,
)
from sazon_urbano.infrastructure.persistence.modelos import (
    ActorRow, DetalleOperacionPiaRow, OperacionPiaRow,
)


class ImportacionPaquetePiaTest(unittest.TestCase):
    def setUp(self):
        self.engine = crear_engine("sqlite://")
        crear_tablas(self.engine)
        self.factory = crear_session_factory(self.engine)
        with self.factory() as s:
            semilla.cargar_catalogo(s)

    def test_importa_los_60_pedidos_con_su_detalle(self):
        with self.factory() as s:
            self.assertEqual(semilla.cargar_paquete_pia(s), 60)
            self.assertEqual(s.scalar(select(func.count()).select_from(OperacionPiaRow)), 60)
            self.assertEqual(s.scalar(select(func.count()).select_from(ActorRow)), 40)
            self.assertEqual(s.scalar(select(func.count()).select_from(DetalleOperacionPiaRow)), 117)

    def test_es_idempotente(self):
        with self.factory() as s:
            semilla.cargar_paquete_pia(s)
            self.assertEqual(semilla.cargar_paquete_pia(s), 0)
            self.assertEqual(s.scalar(select(func.count()).select_from(OperacionPiaRow)), 60)

    def test_clave_foranea_rechaza_actor_inexistente(self):
        with self.factory() as s:
            semilla.cargar_paquete_pia(s)
            s.add(OperacionPiaRow(id="X", actor_id="NO-EXISTE", estado_inicial="CREADO",
                                  fecha_solicitud=__import__("datetime").date(2026, 10, 1), referencia="x"))
            with self.assertRaises(IntegrityError):
                s.commit()

    def test_normaliza_url_de_plataformas(self):
        self.assertEqual(_normalizar_url("postgres://u:p@h:5432/d"), "postgresql+psycopg://u:p@h:5432/d")
        self.assertEqual(_normalizar_url("postgresql://u:p@h/d"), "postgresql+psycopg://u:p@h/d")
        self.assertEqual(_normalizar_url("sqlite://"), "sqlite://")


if __name__ == "__main__":
    unittest.main()
