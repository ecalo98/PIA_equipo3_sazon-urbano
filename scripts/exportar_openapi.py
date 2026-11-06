"""Exporta el contrato OpenAPI a docs/api/openapi.json (se genera del código, no se escribe a mano).

Uso:  python scripts/exportar_openapi.py
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sazon_urbano.api.main import crear_app  # noqa: E402


def main() -> None:
    app = crear_app("sqlite://", sembrar=False)
    destino = RAIZ / "docs" / "api" / "openapi.json"
    destino.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Contrato exportado en", destino.relative_to(RAIZ), f"({len(app.openapi()['paths'])} rutas)")


if __name__ == "__main__":
    main()
