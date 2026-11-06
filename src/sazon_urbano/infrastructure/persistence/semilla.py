"""Datos iniciales (idempotentes): catálogo y datos de demostración. Los CSV originales solo se LEEN.

- Platillos del paquete del PIA (`data/paquete_pia/catalogo.csv`): la estación se deduce del nombre
  (Hamburguesa y Pasta -> parrilla, Ensalada -> fría, Bebida -> bebidas). Es un supuesto del equipo.
- Menú propio de Sazón Urbano (`fixtures/menu_sazon_urbano.csv`).
- Demo: promoción de martes (20 % en tacos y hamburguesas) y dos repartidores.
  (El BRD describe un 2x1; la demo usa un porcentaje con la misma vigencia. Ver docs/analisis D-09.)
"""
from __future__ import annotations

import csv
from datetime import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from sazon_urbano.domain.promocion import Promocion
from sazon_urbano.domain.repartidor import Repartidor
from sazon_urbano.domain.valores import Vigencia

from . import mapeo
from .modelos import PlatilloRow

RAIZ = Path(__file__).resolve().parents[4]
ESTACION_POR_TIPO = {"Hamburguesa": "parrilla", "Pasta": "parrilla", "Ensalada": "fria", "Bebida": "bebidas"}


def _leer(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def cargar_catalogo(session: Session, carpeta_paquete: Path = RAIZ / "data" / "paquete_pia",
                    menu: Path = RAIZ / "fixtures" / "menu_sazon_urbano.csv") -> int:
    n = 0
    for f in _leer(carpeta_paquete / "catalogo.csv"):
        tipo = f["descripcion"].split()[0]
        session.merge(PlatilloRow(id=f["recurso_id"], nombre=f["descripcion"], precio=Decimal(f["precio_mxn"]),
                                  estacion=ESTACION_POR_TIPO.get(tipo, "parrilla"),
                                  stock=int(f["capacidad_o_stock"]), habilitado=f["habilitado"] == "1"))
        n += 1
    for f in _leer(menu):
        session.merge(PlatilloRow(id=f["platillo_id"], nombre=f["nombre"], precio=Decimal(f["precio_mxn"]),
                                  estacion=f["estacion"], stock=int(f["stock"]), habilitado=f["habilitado"] == "1"))
        n += 1
    session.commit()
    return n


def cargar_demo(session: Session) -> None:
    from .modelos import PromocionRow, RepartidorRow

    if session.get(PromocionRow, "promo-martes") is None:
        promo = Promocion("promo-martes", "Martes de tacos y hamburguesas",
                          Vigencia(frozenset({1}), time(18), time(21)), {"taco-pastor", "hamburguesa-clasica"}, 20)
        session.add(mapeo.promocion_a_fila(promo))
    for id_, nombre in (("rep-1", "Pedro"), ("rep-2", "Lucía")):
        if session.get(RepartidorRow, id_) is None:
            session.add(mapeo.repartidor_a_fila(Repartidor(id_, nombre)))
    session.commit()
