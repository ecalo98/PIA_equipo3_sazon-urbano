"""Esquemas de entrada y salida de la API (Pydantic). Las reglas de negocio NO viven aquí: viven en el dominio."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from sazon_urbano.domain.valores import Canal, EstacionCocina, Rol


class ItemIn(BaseModel):
    platillo_id: str = Field(min_length=1, examples=["taco-pastor"])
    cantidad: int = Field(gt=0, le=99, examples=[2])
    modificaciones: list[str] = Field(default_factory=list, examples=[["sin cebolla"]])


class ClienteIn(BaseModel):
    nombre: str = Field(min_length=1, examples=["Marta"])
    telefono: str = Field(min_length=1, examples=["8112345678"])
    direccion: str = Field(default="", examples=["Calle 1 #100"])


class RegistrarPedidoIn(BaseModel):
    canal: Canal
    items: list[ItemIn] = Field(min_length=1)
    mesa: str | None = Field(default=None, examples=["5"])
    cliente: ClienteIn | None = None


class AplicarPromocionIn(BaseModel):
    promocion_id: str = Field(examples=["promo-martes"])
    fecha_hora: datetime | None = Field(default=None, description="Por omisión, el momento actual. Útil para pruebas.")


class AutorizadorIn(BaseModel):
    usuario_id: str = Field(examples=["eva"])
    rol: Rol = Rol.ENCARGADO


class CancelarIn(BaseModel):
    motivo: str = Field(min_length=3, examples=["El cliente cambió de opinión"])
    autorizador: AutorizadorIn | None = Field(default=None, description="Requerido si ya inició la preparación (RN-03).")


class IniciarPreparacionIn(BaseModel):
    estacion: EstacionCocina


class AsignarRepartidorIn(BaseModel):
    pedido_id: str
    repartidor_id: str


class EntregaFallidaIn(BaseModel):
    motivo: str = Field(min_length=3, examples=["Cliente ausente"])


class ResultadoPedidoOut(BaseModel):
    pedido_id: str
    total: Decimal
    estado: str
    genero_merma: bool = False


class ResultadoEntregaOut(BaseModel):
    entrega_id: str
    estado: str


class ErrorOut(BaseModel):
    error: str
    mensaje: str
    motivos: list[str] | None = None


class LineaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    linea_id: str
    producto_id: str
    producto: str
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    modificaciones: list[str] = []


class ResumenPedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    canal: str
    mesa_o_cliente: str
    lineas: list[LineaOut]
    promocion: str | None
    descuento: Decimal
    total: Decimal
    estado: str
    responsable: str
    acciones_permitidas: list[str]


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    nombre: str
    precio: Decimal
    disponible: bool


class PromocionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    nombre: str
    productos: list[str]
    horario: str


class RepartidorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    nombre: str


class EvaluacionOperacionOut(BaseModel):
    operacion_id: str
    total: Decimal
    puede_procesarse: bool
    motivos_de_rechazo: list[str]
    beneficio_referencia: bool
    nota: str = "beneficio_referencia es solo elegibilidad; no aplica descuentos (RN-05)."
