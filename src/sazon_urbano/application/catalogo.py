"""Arma las líneas de un pedido desde el catálogo: el precio y la estación los pone el sistema, no el cliente.

Valida disponibilidad y cantidades (RN-06, US-04). No descuenta inventario: RN-13 queda fuera de los 5 casos de uso.
"""
from __future__ import annotations

from dataclasses import dataclass

from sazon_urbano.domain.errores import CantidadExcedeStock, PlatilloNoDisponible

from . import comandos as c
from .puertos import CatalogoDePlatillos, ConsultasDeDisponibilidad


@dataclass(frozen=True)
class ItemSolicitado:
    platillo_id: str
    cantidad: int
    modificaciones: tuple = ()


def lineas_desde_catalogo(catalogo: CatalogoDePlatillos, disponibilidad: ConsultasDeDisponibilidad, items) -> list:
    lineas = []
    for item in items:
        platillo = catalogo.obtener(item.platillo_id)  # PlatilloNoEncontrado si no existe
        if not platillo.habilitado or disponibilidad.esta_agotado(platillo.id):
            raise PlatilloNoDisponible(platillo.nombre)
        if item.cantidad > platillo.stock:
            raise CantidadExcedeStock(f"{platillo.nombre}: pidió {item.cantidad}, hay {platillo.stock}")
        lineas.append(c.LineaSolicitada(platillo.id, platillo.nombre, platillo.precio, item.cantidad,
                                        platillo.estacion, tuple(item.modificaciones)))
    return lineas
