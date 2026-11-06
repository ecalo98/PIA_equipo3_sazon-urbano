"""Lectura de los CSV del paquete del PIA (solo lectura: los archivos originales nunca se modifican).

Convierte las filas en `OperacionEvaluable` usando claves foráneas y Decimal para el total:
total = suma(precio_mxn x cantidad).
"""
from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from sazon_urbano.domain.evaluacion import OperacionEvaluable
from sazon_urbano.domain.valores import Dinero

RAIZ_DATOS = Path(__file__).resolve().parents[3] / "data" / "paquete_pia"


def _leer(nombre: str, carpeta: Path) -> list[dict]:
    with open(carpeta / nombre, encoding="utf-8-sig", newline="") as f:  # los CSV traen BOM
        return list(csv.DictReader(f))


class PaquetePia:
    def __init__(self, carpeta: Path = RAIZ_DATOS):
        actores = {a["actor_id"]: a for a in _leer("actores.csv", carpeta)}
        catalogo = {c["recurso_id"]: c for c in _leer("catalogo.csv", carpeta)}
        lineas = defaultdict(list)
        for d in _leer("detalle_operaciones.csv", carpeta):
            lineas[d["operacion_id"]].append(d)

        self.catalogo = catalogo
        self.detalle = lineas
        self.operaciones: dict[str, OperacionEvaluable] = {}
        for fila in _leer("operaciones.csv", carpeta):
            actor = actores[fila["actor_id"]]
            detalle = lineas[fila["operacion_id"]]
            total = sum((Decimal(catalogo[d["recurso_id"]]["precio_mxn"]) * int(d["cantidad"]) for d in detalle), Decimal("0"))
            self.operaciones[fila["operacion_id"]] = OperacionEvaluable(
                operacion_id=fila["operacion_id"],
                actor_activo=actor["activo"] == "1",
                actor_preferente=actor["es_preferente"] == "1",
                num_lineas=len(detalle),
                total=Dinero(total),
                autorizado=fila["autorizado"] == "1",
                promocion_activa=fila["promocion_activa"] == "1",
            )
        self.casos_prueba = _leer("casos_prueba.csv", carpeta)
        self.transiciones = _leer("transiciones_prueba.csv", carpeta)
