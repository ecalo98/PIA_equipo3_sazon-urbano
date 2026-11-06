"""Queries (CQRS básico, ADR-03): solo leen y devuelven DTO planos, nunca el aggregate.

Dependen de interfaces de lectura (`ConsultasDe...`), no de los repositorios de escritura (principio I).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class LineaDto:
    linea_id: str
    producto_id: str
    producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    modificaciones: tuple = ()


@dataclass(frozen=True)
class ResumenDePedidoDto:
    id: str
    canal: str
    mesa_o_cliente: str
    lineas: list[LineaDto]
    promocion: str | None
    descuento: Decimal
    total: Decimal
    estado: str
    responsable: str
    acciones_permitidas: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProductoDisponibleDto:
    id: str
    nombre: str
    precio: Decimal
    disponible: bool


@dataclass(frozen=True)
class PromocionVigenteDto:
    id: str
    nombre: str
    productos: list[str]
    horario: str


@dataclass(frozen=True)
class RepartidorDisponibleDto:
    id: str
    nombre: str


class ConsultasDePedidos(ABC):
    @abstractmethod
    def resumen(self, pedido_id: str) -> ResumenDePedidoDto:
        """Lanza PedidoNoEncontrado si no existe."""


class ConsultasDeMenu(ABC):
    @abstractmethod
    def menu_disponible(self) -> list[ProductoDisponibleDto]: ...


class ConsultasDePromociones(ABC):
    @abstractmethod
    def vigentes_en(self, fecha_hora: datetime) -> list[PromocionVigenteDto]: ...


class ConsultasDeRepartidores(ABC):
    @abstractmethod
    def disponibles(self) -> list[RepartidorDisponibleDto]: ...


class ConsultarResumenDelPedidoHandler:
    def __init__(self, consultas: ConsultasDePedidos):
        self._consultas = consultas

    def manejar(self, pedido_id: str) -> ResumenDePedidoDto:
        return self._consultas.resumen(pedido_id)


class ConsultarMenuDisponibleHandler:
    def __init__(self, consultas: ConsultasDeMenu):
        self._consultas = consultas

    def manejar(self) -> list[ProductoDisponibleDto]:
        return self._consultas.menu_disponible()


class ConsultarPromocionesVigentesHandler:
    def __init__(self, consultas: ConsultasDePromociones):
        self._consultas = consultas

    def manejar(self, fecha_hora: datetime) -> list[PromocionVigenteDto]:
        return self._consultas.vigentes_en(fecha_hora)


class ConsultarRepartidoresDisponiblesHandler:
    def __init__(self, consultas: ConsultasDeRepartidores):
        self._consultas = consultas

    def manejar(self) -> list[RepartidorDisponibleDto]:
        return self._consultas.disponibles()
