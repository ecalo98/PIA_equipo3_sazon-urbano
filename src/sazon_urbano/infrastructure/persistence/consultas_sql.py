"""Implementaciones SQL de las interfaces de lectura (Queries) y del catálogo."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from sazon_urbano.application.consultas import (
    ConsultasDeMenu, ConsultasDePedidos, ConsultasDePromociones, ConsultasDeRepartidores, LineaDto,
    ProductoDisponibleDto, PromocionVigenteDto, RepartidorDisponibleDto, ResumenDePedidoDto,
)
from sazon_urbano.application.puertos import CatalogoDePlatillos, PlatilloDto
from sazon_urbano.domain.errores import PedidoNoEncontrado, PlatilloNoEncontrado
from sazon_urbano.domain.valores import EstacionCocina

from . import mapeo
from .modelos import PedidoRow, PlatilloRow, ProductoAgotadoRow, PromocionRow, RepartidorRow

_DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def _a_platillo_dto(f: PlatilloRow) -> PlatilloDto:
    return PlatilloDto(f.id, f.nombre, f.precio, EstacionCocina(f.estacion), f.stock, f.habilitado)


class CatalogoDePlatillosSql(CatalogoDePlatillos):
    def __init__(self, session: Session):
        self._session = session

    def obtener(self, platillo_id: str) -> PlatilloDto:
        fila = self._session.get(PlatilloRow, platillo_id)
        if fila is None:
            raise PlatilloNoEncontrado(platillo_id)
        return _a_platillo_dto(fila)

    def listar(self) -> list[PlatilloDto]:
        return [_a_platillo_dto(f) for f in self._session.scalars(select(PlatilloRow).order_by(PlatilloRow.id))]


class ConsultasDePedidosSql(ConsultasDePedidos):
    def __init__(self, session: Session):
        self._session = session

    def resumen(self, pedido_id: str) -> ResumenDePedidoDto:
        fila = self._session.get(PedidoRow, pedido_id)
        if fila is None:
            raise PedidoNoEncontrado(pedido_id)
        pedido = mapeo.fila_a_pedido(fila)  # el total y las acciones se calculan con las reglas del dominio
        descuento = pedido.promocion.descuento.monto if pedido.promocion else 0
        cliente = pedido.cliente.nombre if pedido.cliente else ""
        return ResumenDePedidoDto(
            id=pedido.id, canal=pedido.canal.value,
            mesa_o_cliente=f"Mesa {pedido.mesa}" if pedido.mesa else cliente,
            lineas=[LineaDto(l.id, l.producto.producto_id, l.producto.nombre, l.cantidad,
                             l.producto.precio_unitario.monto, l.subtotal.monto, tuple(l.modificaciones))
                    for l in pedido.lineas],
            promocion=pedido.promocion.descripcion if pedido.promocion else None,
            descuento=descuento, total=pedido.total.monto, estado=pedido.estado.value,
            responsable=f"{pedido.responsable.usuario_id} ({pedido.responsable.rol.value})",
            acciones_permitidas=[a.value for a in pedido.acciones_permitidas],
        )


class ConsultasDeMenuSql(ConsultasDeMenu):
    def __init__(self, session: Session):
        self._session = session

    def menu_disponible(self) -> list[ProductoDisponibleDto]:
        agotados = set(self._session.scalars(select(ProductoAgotadoRow.producto_id)))
        filas = self._session.scalars(select(PlatilloRow).order_by(PlatilloRow.id))
        return [ProductoDisponibleDto(f.id, f.nombre, f.precio,
                                      f.habilitado and f.stock > 0 and f.id not in agotados) for f in filas]


class ConsultasDePromocionesSql(ConsultasDePromociones):
    def __init__(self, session: Session):
        self._session = session

    def vigentes_en(self, fecha_hora: datetime) -> list[PromocionVigenteDto]:
        resultado = []
        for fila in self._session.scalars(select(PromocionRow).order_by(PromocionRow.id)):
            promo = mapeo.fila_a_promocion(fila)
            if promo.esta_vigente_en(fecha_hora):
                dias = ", ".join(_DIAS[d] for d in sorted(promo.vigencia.dias))
                resultado.append(PromocionVigenteDto(
                    promo.id, promo.nombre, sorted(promo.productos_ids),
                    f"{dias} {promo.vigencia.hora_inicio:%H:%M}-{promo.vigencia.hora_fin:%H:%M}"))
        return resultado


class ConsultasDeRepartidoresSql(ConsultasDeRepartidores):
    def __init__(self, session: Session):
        self._session = session

    def disponibles(self) -> list[RepartidorDisponibleDto]:
        filas = self._session.scalars(select(RepartidorRow).where(RepartidorRow.disponible.is_(True)).order_by(RepartidorRow.id))
        return [RepartidorDisponibleDto(f.id, f.nombre) for f in filas]
