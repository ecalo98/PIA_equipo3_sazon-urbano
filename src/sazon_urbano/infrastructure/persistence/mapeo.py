"""Traduce entre objetos del dominio y filas. Reconstruye los aggregates sin disparar reglas ni eventos."""
from __future__ import annotations

from decimal import Decimal

from sazon_urbano.domain.entrega import Entrega, EstadoEntrega
from sazon_urbano.domain.merma import Merma
from sazon_urbano.domain.pedido import EstadoPedido, EstadoPreparacion, LineaPedido, Pedido, PreparacionEstacion
from sazon_urbano.domain.promocion import Promocion
from sazon_urbano.domain.repartidor import Repartidor
from sazon_urbano.domain.valores import (
    Canal, Cancelacion, DatosCliente, Dinero, EstacionCocina, ProductoPedido, PromocionAplicada,
    Responsable, Rol, TipoCancelacion, Vigencia,
)

from .modelos import (
    CancelacionRow, EntregaRow, LineaPedidoRow, MermaRow, PedidoRow, PreparacionRow, PromocionRow, RepartidorRow,
)


def _responsable(id_, rol) -> Responsable | None:
    return Responsable(id_, Rol(rol)) if id_ else None


# -- Pedido -------------------------------------------------------------------
def pedido_a_fila(pedido: Pedido, fila: PedidoRow | None = None) -> PedidoRow:
    fila = fila or PedidoRow(id=pedido.id)
    fila.canal, fila.estado = pedido.canal.value, pedido.estado.value
    fila.responsable_id, fila.responsable_rol = pedido.responsable.usuario_id, pedido.responsable.rol.value
    cliente = pedido.cliente
    fila.cliente_nombre = cliente.nombre if cliente else None
    fila.cliente_telefono = cliente.telefono if cliente else None
    fila.cliente_direccion = cliente.direccion if cliente else None
    fila.mesa = pedido.mesa
    promo = pedido.promocion
    fila.promocion_id = promo.promocion_id if promo else None
    fila.promocion_descripcion = promo.descripcion if promo else None
    fila.promocion_descuento = promo.descuento.monto if promo else None
    # Los hijos se reemplazan completos: el aggregate es la unidad de consistencia.
    fila.lineas = [
        LineaPedidoRow(id=l.id, posicion=i, producto_id=l.producto.producto_id, nombre=l.producto.nombre,
                       precio_unitario=l.producto.precio_unitario.monto, cantidad=l.cantidad,
                       estacion=l.estacion.value, modificaciones=list(l.modificaciones))
        for i, l in enumerate(pedido.lineas)
    ]
    fila.preparaciones = [PreparacionRow(estacion=e.value, estado=p.estado.value) for e, p in pedido.preparaciones.items()]
    fila.cancelaciones = [
        CancelacionRow(tipo=c.tipo.value, motivo=c.motivo, responsable_id=c.responsable.usuario_id,
                       responsable_rol=c.responsable.rol.value,
                       autorizado_por_id=c.autorizado_por.usuario_id if c.autorizado_por else None,
                       autorizado_por_rol=c.autorizado_por.rol.value if c.autorizado_por else None, fecha=c.fecha)
        for c in pedido.cancelaciones
    ]
    return fila


def fila_a_pedido(fila: PedidoRow) -> Pedido:
    cliente = None
    if fila.cliente_nombre is not None or fila.cliente_telefono is not None or fila.cliente_direccion is not None:
        cliente = DatosCliente(fila.cliente_nombre or "", fila.cliente_telefono or "", fila.cliente_direccion or "")
    lineas = [
        LineaPedido(l.id, ProductoPedido(l.producto_id, l.nombre, Dinero(Decimal(l.precio_unitario))), l.cantidad,
                    EstacionCocina(l.estacion), tuple(l.modificaciones or ()))
        for l in fila.lineas
    ]
    pedido = Pedido(fila.id, Canal(fila.canal), Responsable(fila.responsable_id, Rol(fila.responsable_rol)),
                    lineas, cliente, fila.mesa)
    pedido.estado = EstadoPedido(fila.estado)
    pedido.preparaciones = {EstacionCocina(p.estacion): PreparacionEstacion(EstacionCocina(p.estacion), EstadoPreparacion(p.estado))
                            for p in fila.preparaciones}
    if fila.promocion_id:
        pedido.promocion = PromocionAplicada(fila.promocion_id, fila.promocion_descripcion,
                                             Dinero(Decimal(fila.promocion_descuento)))
    pedido.cancelaciones = [
        Cancelacion(TipoCancelacion(c.tipo), c.motivo, Responsable(c.responsable_id, Rol(c.responsable_rol)),
                    _responsable(c.autorizado_por_id, c.autorizado_por_rol), c.fecha)
        for c in fila.cancelaciones
    ]
    return pedido


# -- Promoción ----------------------------------------------------------------
def promocion_a_fila(p: Promocion, fila: PromocionRow | None = None) -> PromocionRow:
    fila = fila or PromocionRow(id=p.id)
    fila.nombre = p.nombre
    fila.dias = sorted(p.vigencia.dias)
    fila.hora_inicio, fila.hora_fin = p.vigencia.hora_inicio, p.vigencia.hora_fin
    fila.productos_ids = sorted(p.productos_ids)
    fila.porcentaje_descuento = p.porcentaje_descuento
    return fila


def fila_a_promocion(f: PromocionRow) -> Promocion:
    return Promocion(f.id, f.nombre, Vigencia(frozenset(f.dias), f.hora_inicio, f.hora_fin),
                     set(f.productos_ids), Decimal(f.porcentaje_descuento))


# -- Repartidor ---------------------------------------------------------------
def repartidor_a_fila(r: Repartidor, fila: RepartidorRow | None = None) -> RepartidorRow:
    fila = fila or RepartidorRow(id=r.id)
    fila.nombre, fila.disponible = r.nombre, r.disponible
    return fila


def fila_a_repartidor(f: RepartidorRow) -> Repartidor:
    return Repartidor(f.id, f.nombre, f.disponible)


# -- Entrega ------------------------------------------------------------------
def entrega_a_fila(e: Entrega, fila: EntregaRow | None = None) -> EntregaRow:
    fila = fila or EntregaRow(id=e.id)
    fila.pedido_id, fila.repartidor_id, fila.estado = e.pedido_id, e.repartidor_id, e.estado.value
    fila.hora_salida, fila.hora_entrega, fila.motivo_falla = e.hora_salida, e.hora_entrega, e.motivo_falla
    return fila


def fila_a_entrega(f: EntregaRow) -> Entrega:
    entrega = Entrega(f.id, f.pedido_id, f.repartidor_id)
    entrega.estado = EstadoEntrega(f.estado)
    entrega.hora_salida, entrega.hora_entrega, entrega.motivo_falla = f.hora_salida, f.hora_entrega, f.motivo_falla
    return entrega


# -- Merma --------------------------------------------------------------------
def merma_a_fila(m: Merma) -> MermaRow:
    return MermaRow(id=m.id, pedido_id=m.pedido_id, motivo=m.motivo, responsable_id=m.responsable.usuario_id,
                    responsable_rol=m.responsable.rol.value, fecha=m.fecha)


def fila_a_merma(f: MermaRow) -> Merma:
    return Merma(f.id, f.pedido_id, f.motivo, Responsable(f.responsable_id, Rol(f.responsable_rol)), f.fecha)
