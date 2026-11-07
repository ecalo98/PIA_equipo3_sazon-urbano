"""Tablas relacionales. Son un detalle de infraestructura: el dominio no las conoce (ADR-02)."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

DINERO = Numeric(12, 2)


class Base(DeclarativeBase):
    pass


class PedidoRow(Base):
    __tablename__ = "pedidos"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canal: Mapped[str] = mapped_column(String(30))
    estado: Mapped[str] = mapped_column(String(30), index=True)
    responsable_id: Mapped[str] = mapped_column(String(60))      # RN-14
    responsable_rol: Mapped[str] = mapped_column(String(20))
    cliente_nombre: Mapped[str | None] = mapped_column(String(120))
    cliente_telefono: Mapped[str | None] = mapped_column(String(30))
    cliente_direccion: Mapped[str | None] = mapped_column(String(250))
    mesa: Mapped[str | None] = mapped_column(String(20))
    promocion_id: Mapped[str | None] = mapped_column(String(40))
    promocion_descripcion: Mapped[str | None] = mapped_column(String(200))
    promocion_descuento: Mapped[Decimal | None] = mapped_column(DINERO)

    lineas: Mapped[list["LineaPedidoRow"]] = relationship(
        cascade="all, delete-orphan", order_by="LineaPedidoRow.posicion", lazy="selectin")
    preparaciones: Mapped[list["PreparacionRow"]] = relationship(cascade="all, delete-orphan", lazy="selectin")
    cancelaciones: Mapped[list["CancelacionRow"]] = relationship(
        cascade="all, delete-orphan", order_by="CancelacionRow.id", lazy="selectin")


class LineaPedidoRow(Base):
    __tablename__ = "lineas_pedido"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), index=True)
    posicion: Mapped[int] = mapped_column(Integer)
    producto_id: Mapped[str] = mapped_column(String(60))
    nombre: Mapped[str] = mapped_column(String(120))
    precio_unitario: Mapped[Decimal] = mapped_column(DINERO)     # instantánea del precio (H-09)
    cantidad: Mapped[int] = mapped_column(Integer)
    estacion: Mapped[str] = mapped_column(String(20))
    modificaciones: Mapped[list] = mapped_column(JSON, default=list)


class PreparacionRow(Base):
    __tablename__ = "preparaciones"
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), primary_key=True)
    estacion: Mapped[str] = mapped_column(String(20), primary_key=True)
    estado: Mapped[str] = mapped_column(String(20))


class CancelacionRow(Base):
    __tablename__ = "cancelaciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))
    motivo: Mapped[str] = mapped_column(String(300))
    responsable_id: Mapped[str] = mapped_column(String(60))
    responsable_rol: Mapped[str] = mapped_column(String(20))
    autorizado_por_id: Mapped[str | None] = mapped_column(String(60))
    autorizado_por_rol: Mapped[str | None] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime)


class PromocionRow(Base):
    __tablename__ = "promociones"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    dias: Mapped[list] = mapped_column(JSON)                      # 0 = lunes ... 6 = domingo
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)
    productos_ids: Mapped[list] = mapped_column(JSON)
    porcentaje_descuento: Mapped[Decimal] = mapped_column(Numeric(5, 2))


class RepartidorRow(Base):
    __tablename__ = "repartidores"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)


class EntregaRow(Base):
    __tablename__ = "entregas"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id"), index=True)
    repartidor_id: Mapped[str] = mapped_column(ForeignKey("repartidores.id"))
    estado: Mapped[str] = mapped_column(String(20))
    hora_salida: Mapped[datetime | None] = mapped_column(DateTime)   # RN-11
    hora_entrega: Mapped[datetime | None] = mapped_column(DateTime)
    motivo_falla: Mapped[str | None] = mapped_column(String(300))


class MermaRow(Base):
    __tablename__ = "mermas"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    pedido_id: Mapped[str] = mapped_column(ForeignKey("pedidos.id"), index=True)
    motivo: Mapped[str] = mapped_column(String(300))
    responsable_id: Mapped[str] = mapped_column(String(60))
    responsable_rol: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime)


class ProductoAgotadoRow(Base):
    __tablename__ = "productos_agotados"
    producto_id: Mapped[str] = mapped_column(String(60), primary_key=True)
    marcado_por_id: Mapped[str] = mapped_column(String(60))
    marcado_por_rol: Mapped[str] = mapped_column(String(20))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class PlatilloRow(Base):
    """Catálogo de solo lectura (no es aggregate). Precio y estación se copian al pedido al registrarlo (H-09)."""
    __tablename__ = "platillos"
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    precio: Mapped[Decimal] = mapped_column(DINERO)
    estacion: Mapped[str] = mapped_column(String(20))
    stock: Mapped[int] = mapped_column(Integer)
    habilitado: Mapped[bool] = mapped_column(Boolean, default=True)


class ActorRow(Base):
    """Comensales del paquete de datos del PIA (`actores.csv`). Solo lectura."""
    __tablename__ = "actores"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    es_preferente: Mapped[bool] = mapped_column(Boolean, default=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ciudad: Mapped[str] = mapped_column(String(60))


class OperacionPiaRow(Base):
    """Los 60 pedidos del dataset (`operaciones.csv`) con claves foráneas a actores y platillos."""
    __tablename__ = "operaciones_pia"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("actores.id"), index=True)
    estado_inicial: Mapped[str] = mapped_column(String(30))
    fecha_solicitud: Mapped[date] = mapped_column(Date)
    promocion_activa: Mapped[bool] = mapped_column(Boolean, default=False)
    autorizado: Mapped[bool] = mapped_column(Boolean, default=False)
    referencia: Mapped[str] = mapped_column(String(40))

    detalle: Mapped[list["DetalleOperacionPiaRow"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin")


class DetalleOperacionPiaRow(Base):
    __tablename__ = "detalle_operaciones_pia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operacion_id: Mapped[str] = mapped_column(ForeignKey("operaciones_pia.id", ondelete="CASCADE"), index=True)
    platillo_id: Mapped[str] = mapped_column(ForeignKey("platillos.id"))
    cantidad: Mapped[int] = mapped_column(Integer)
