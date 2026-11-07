"""Datos iniciales (idempotentes): catálogo y datos de demostración. Los CSV originales solo se LEEN.

- Platillos del paquete del PIA (`data/paquete_pia/catalogo.csv`): la estación se deduce del nombre
  (Hamburguesa y Pasta -> parrilla, Ensalada -> fría, Bebida -> bebidas). Es un supuesto del equipo.
- Menú propio de Sazón Urbano (`fixtures/menu_sazon_urbano.csv`).
- Demo: promoción de martes (20 % en tacos y hamburguesas) y dos repartidores.
  (El BRD describe un 2x1; la demo usa un porcentaje con la misma vigencia. Ver docs/analisis D-09.)
"""
from __future__ import annotations

import csv
from datetime import date, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from sazon_urbano.domain.promocion import Promocion
from sazon_urbano.domain.repartidor import Repartidor
from sazon_urbano.domain.valores import Vigencia

from . import mapeo
from .modelos import ActorRow, DetalleOperacionPiaRow, OperacionPiaRow, PlatilloRow

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


def cargar_paquete_pia(session: Session, carpeta_paquete: Path = RAIZ / "data" / "paquete_pia") -> int:
    """Importa actores y los 60 pedidos del dataset (con su detalle) respetando claves foráneas.

    Idempotente: si ya existen pedidos importados no vuelve a insertarlos. Requiere el catálogo cargado
    (`cargar_catalogo`), porque `detalle_operaciones_pia.platillo_id` referencia `platillos.id`.
    Devuelve el número de pedidos importados en esta llamada.
    """
    if session.query(OperacionPiaRow).first() is not None:
        return 0
    for f in _leer(carpeta_paquete / "actores.csv"):
        session.merge(ActorRow(id=f["actor_id"], nombre=f["nombre"], es_preferente=f["es_preferente"] == "1",
                               activo=f["activo"] == "1", ciudad=f["ciudad"]))
    session.flush()
    detalle: dict[str, list[dict]] = {}
    for d in _leer(carpeta_paquete / "detalle_operaciones.csv"):
        detalle.setdefault(d["operacion_id"], []).append(d)
    n = 0
    for f in _leer(carpeta_paquete / "operaciones.csv"):
        session.add(OperacionPiaRow(
            id=f["operacion_id"], actor_id=f["actor_id"], estado_inicial=f["estado_inicial"],
            fecha_solicitud=date.fromisoformat(f["fecha_solicitud"]),
            promocion_activa=f["promocion_activa"] == "1", autorizado=f["autorizado"] == "1",
            referencia=f["referencia"],
            detalle=[DetalleOperacionPiaRow(platillo_id=d["recurso_id"], cantidad=int(d["cantidad"]))
                     for d in detalle.get(f["operacion_id"], [])]))
        n += 1
    session.commit()
    return n
