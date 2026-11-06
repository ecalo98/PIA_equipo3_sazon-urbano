"""Pruebas de arquitectura: verifican por código la regla de dependencias (principio D de SOLID,
validación de Persistencia de la Etapa 9)."""
import ast
import pathlib
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2] / "src" / "sazon_urbano"


def importaciones(carpeta: str) -> set:
    encontradas = set()
    for archivo in (RAIZ / carpeta).glob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                encontradas.add(nodo.module)
            elif isinstance(nodo, ast.Import):
                encontradas.update(a.name for a in nodo.names)
    return encontradas


class TestReglaDeDependencias(unittest.TestCase):
    def test_el_dominio_no_depende_de_aplicacion_ni_infraestructura(self):
        for modulo in importaciones("domain"):
            self.assertNotIn("application", modulo)
            self.assertNotIn("infrastructure", modulo)

    def test_la_aplicacion_no_depende_de_la_infraestructura(self):
        for modulo in importaciones("application"):
            self.assertNotIn("infrastructure", modulo)

    def test_el_dominio_no_usa_sql_ni_librerias_de_persistencia(self):
        prohibidas = {"sqlite3", "sqlalchemy", "psycopg2", "psycopg", "pyodbc"}
        self.assertFalse(prohibidas & importaciones("domain"))
        self.assertFalse(prohibidas & importaciones("application"))

    def test_dominio_y_aplicacion_no_conocen_la_capa_api_ni_el_framework_web(self):
        prohibidas = {"fastapi", "starlette", "pydantic", "uvicorn"}
        for capa in ("domain", "application"):
            modulos = importaciones(capa)
            self.assertFalse(prohibidas & modulos, capa)
            self.assertFalse([m for m in modulos if ".api" in m or m.endswith("api")], capa)

    def test_la_infraestructura_no_depende_de_la_api(self):
        for modulo in importaciones("infrastructure"):
            self.assertNotIn(".api", modulo)


if __name__ == "__main__":
    unittest.main()
