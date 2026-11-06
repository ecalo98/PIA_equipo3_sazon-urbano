"""Raíz de composición: único lugar donde se conectan las interfaces con sus implementaciones."""
from __future__ import annotations

from dataclasses import dataclass

from sazon_urbano.application import handlers as h
from sazon_urbano.application.servicios import (
    DisponibilidadApplicationService,
    EntregaApplicationService,
    PedidoApplicationService,
    PreparacionApplicationService,
)
from sazon_urbano.domain.repositorios import (
    DisponibilidadRepository,
    EntregaRepository,
    MermaRepository,
    PedidoRepository,
    PromocionRepository,
    RepartidorRepository,
)
from sazon_urbano.domain.servicios import AplicadorDePromocion, AsignadorDeRepartidor

from .memoria import (
    ControlDeAccesoPorRol,
    DisponibilidadEnMemoria,
    EntregaRepositoryEnMemoria,
    MermaRepositoryEnMemoria,
    NotificadorInterno,
    PedidoRepositoryEnMemoria,
    PromocionRepositoryEnMemoria,
    PublicadorDeEventosEnMemoria,
    RepartidorRepositoryEnMemoria,
    UnitOfWorkEnMemoria,
)


@dataclass
class Aplicacion:
    pedidos_svc: PedidoApplicationService
    disponibilidad_svc: DisponibilidadApplicationService
    entregas_svc: EntregaApplicationService
    preparacion_svc: PreparacionApplicationService
    pedidos: PedidoRepository
    promociones: PromocionRepository
    entregas: EntregaRepository
    repartidores: RepartidorRepository
    mermas: MermaRepository
    disponibilidad: DisponibilidadRepository
    publicador: PublicadorDeEventosEnMemoria
    notificador: NotificadorInterno


def _ensamblar(pedidos, promociones, entregas, repartidores, mermas, disponibilidad, uow) -> Aplicacion:
    publicador, notificador, acceso = PublicadorDeEventosEnMemoria(), NotificadorInterno(), ControlDeAccesoPorRol()
    aplicador, asignador = AplicadorDePromocion(), AsignadorDeRepartidor()

    return Aplicacion(
        pedidos_svc=PedidoApplicationService(
            acceso,
            h.RegistrarPedidoHandler(pedidos, uow, publicador),
            h.AplicarPromocionHandler(pedidos, promociones, aplicador, uow, publicador),
            h.CancelarPedidoHandler(pedidos, mermas, uow, publicador),
        ),
        disponibilidad_svc=DisponibilidadApplicationService(
            acceso,
            h.MarcarProductoAgotadoHandler(disponibilidad, notificador, uow, publicador),
            h.QuitarLineaAgotadaHandler(pedidos, disponibilidad, uow, publicador),
        ),
        entregas_svc=EntregaApplicationService(
            acceso,
            h.AsignarRepartidorHandler(pedidos, repartidores, entregas, asignador, uow, publicador),
            h.RegistrarSalidaHandler(entregas, uow, publicador),
            h.ConfirmarEntregaHandler(entregas, pedidos, repartidores, uow, publicador),
            h.RegistrarEntregaFallidaHandler(entregas, pedidos, repartidores, uow, publicador),
        ),
        preparacion_svc=PreparacionApplicationService(
            acceso,
            h.IniciarPreparacionHandler(pedidos, uow, publicador),
            h.MarcarPedidoListoHandler(pedidos, uow, publicador),
        ),
        pedidos=pedidos, promociones=promociones, entregas=entregas, repartidores=repartidores,
        mermas=mermas, disponibilidad=disponibilidad, publicador=publicador, notificador=notificador,
    )


def construir_aplicacion() -> Aplicacion:
    """Versión en memoria (pruebas rápidas y demostraciones sin base de datos)."""
    pedidos, promociones = PedidoRepositoryEnMemoria(), PromocionRepositoryEnMemoria()
    entregas, repartidores = EntregaRepositoryEnMemoria(), RepartidorRepositoryEnMemoria()
    mermas, disponibilidad = MermaRepositoryEnMemoria(), DisponibilidadEnMemoria()
    uow = UnitOfWorkEnMemoria(pedidos, promociones, entregas, repartidores, mermas, disponibilidad)
    return _ensamblar(pedidos, promociones, entregas, repartidores, mermas, disponibilidad, uow)


def construir_aplicacion_sql(session) -> Aplicacion:
    """Versión relacional: una sesión SQLAlchemy por solicitud (la API crea una por request)."""
    from .persistence.repositorios_sql import (
        DisponibilidadSql, EntregaRepositorySql, MermaRepositorySql, PedidoRepositorySql,
        PromocionRepositorySql, RepartidorRepositorySql,
    )
    from .persistence.unit_of_work_sql import UnitOfWorkSql

    return _ensamblar(
        PedidoRepositorySql(session), PromocionRepositorySql(session), EntregaRepositorySql(session),
        RepartidorRepositorySql(session), MermaRepositorySql(session), DisponibilidadSql(session),
        UnitOfWorkSql(session),
    )
