"""Repositorios relacionales. Cumplen el mismo contrato que los de memoria (principio L, hallazgo H4):
obtener_por_id SIEMPRE lanza un error de negocio si el objeto no existe.

No confirman la transacción: eso lo decide la Unit of Work (una por solicitud, ADR-02).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from sazon_urbano.application.puertos import ConsultasDeDisponibilidad
from sazon_urbano.domain.errores import (
    EntregaNoEncontrada, PedidoNoEncontrado, PromocionNoEncontrada, RepartidorNoEncontrado,
)
from sazon_urbano.domain.repositorios import (
    DisponibilidadRepository, EntregaRepository, MermaRepository, PedidoRepository, PromocionRepository,
    RepartidorRepository,
)
from sazon_urbano.domain.valores import Responsable

from . import mapeo
from .modelos import (
    EntregaRow, MermaRow, PedidoRow, ProductoAgotadoRow, PromocionRow, RepartidorRow,
)


class _RepositorioSql:
    _Fila = None
    _error = None
    _a_dominio = None
    _a_fila = None

    def __init__(self, session: Session):
        self._session = session

    def obtener_por_id(self, id):
        fila = self._session.get(self._Fila, id)
        if fila is None:
            raise self._error(id)
        return type(self)._a_dominio(fila)

    def guardar(self, objeto) -> None:
        fila = self._session.get(self._Fila, objeto.id)
        self._session.add(type(self)._a_fila(objeto, fila))


class PedidoRepositorySql(_RepositorioSql, PedidoRepository):
    _Fila, _error = PedidoRow, PedidoNoEncontrado
    _a_dominio = staticmethod(mapeo.fila_a_pedido)
    _a_fila = staticmethod(mapeo.pedido_a_fila)


class PromocionRepositorySql(_RepositorioSql, PromocionRepository):
    _Fila, _error = PromocionRow, PromocionNoEncontrada
    _a_dominio = staticmethod(mapeo.fila_a_promocion)
    _a_fila = staticmethod(mapeo.promocion_a_fila)


class RepartidorRepositorySql(_RepositorioSql, RepartidorRepository):
    _Fila, _error = RepartidorRow, RepartidorNoEncontrado
    _a_dominio = staticmethod(mapeo.fila_a_repartidor)
    _a_fila = staticmethod(mapeo.repartidor_a_fila)


class EntregaRepositorySql(_RepositorioSql, EntregaRepository):
    _Fila, _error = EntregaRow, EntregaNoEncontrada
    _a_dominio = staticmethod(mapeo.fila_a_entrega)
    _a_fila = staticmethod(mapeo.entrega_a_fila)


class MermaRepositorySql(MermaRepository):
    def __init__(self, session: Session):
        self._session = session

    def guardar(self, merma) -> None:
        self._session.merge(mapeo.merma_a_fila(merma))  # una merma registrada no se edita; merge evita duplicar


class DisponibilidadSql(DisponibilidadRepository, ConsultasDeDisponibilidad):
    """Escritura y lectura separadas por interfaz (principio I): cada consumidor usa solo la suya."""

    def __init__(self, session: Session):
        self._session = session

    def marcar_agotado(self, producto_id: str, responsable: Responsable, fecha_hora: datetime) -> None:
        self._session.merge(ProductoAgotadoRow(producto_id=producto_id, marcado_por_id=responsable.usuario_id,
                                               marcado_por_rol=responsable.rol.value, fecha_hora=fecha_hora))

    def esta_agotado(self, producto_id: str) -> bool:
        return self._session.get(ProductoAgotadoRow, producto_id) is not None
