"""Puertos de la capa de aplicación: interfaces que la infraestructura implementa."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from sazon_urbano.domain.valores import EstacionCocina, Responsable


class Accion(Enum):
    REGISTRAR_PEDIDO_MESA = "registrar_pedido_mesa"
    REGISTRAR_PEDIDO_REMOTO = "registrar_pedido_remoto"  # teléfono, WhatsApp o domicilio
    APLICAR_PROMOCION = "aplicar_promocion"
    SOLICITAR_CANCELACION = "solicitar_cancelacion"
    AUTORIZAR_CANCELACION = "autorizar_cancelacion"
    MARCAR_AGOTADO = "marcar_agotado"
    QUITAR_LINEA_AGOTADA = "quitar_linea_agotada"
    ASIGNAR_REPARTIDOR = "asignar_repartidor"
    REGISTRAR_ENTREGA = "registrar_entrega"  # salida, entrega o entrega fallida
    INICIAR_PREPARACION = "iniciar_preparacion"  # flujo de cocina (fuera de los 5 casos de uso)
    MARCAR_LISTO = "marcar_listo"


class ControlDeAcceso(ABC):
    @abstractmethod
    def verificar_permiso(self, responsable: Responsable, accion: Accion) -> None:
        """Lanza AccesoDenegado si el rol no puede ejecutar la acción (US-19)."""


class PublicadorDeEventos(ABC):
    @abstractmethod
    def publicar(self, eventos: list) -> None: ...


class Notificador(ABC):
    @abstractmethod
    def avisar(self, destinatarios: list, mensaje: str) -> None: ...


class ConsultasDeDisponibilidad(ABC):
    """Interfaz de lectura (H5): quien solo consulta no depende de métodos de escritura."""

    @abstractmethod
    def esta_agotado(self, producto_id: str) -> bool: ...


@dataclass(frozen=True)
class PlatilloDto:
    id: str
    nombre: str
    precio: Decimal
    estacion: EstacionCocina
    stock: int
    habilitado: bool


class CatalogoDePlatillos(ABC):
    """Interfaz de lectura del catálogo (no es aggregate: decisión 3 de la U3)."""

    @abstractmethod
    def obtener(self, platillo_id: str) -> PlatilloDto:
        """Lanza PlatilloNoEncontrado si no existe."""

    @abstractmethod
    def listar(self) -> list[PlatilloDto]: ...
