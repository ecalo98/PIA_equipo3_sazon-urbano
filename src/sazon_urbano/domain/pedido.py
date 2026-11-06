"""Aggregate Pedido: raíz, líneas y preparación por estación (Etapa 3).

Aquí viven RN-01, RN-02, RN-03, RN-04, RN-06, RN-12 y RN-14. Ninguna otra capa
decide estas reglas: solo piden al Pedido que actúe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .errores import (
    CancelacionRequiereAutorizacion,
    DatosDeDomicilioIncompletos,
    LineaNoExiste,
    EstacionSinLineasEnElPedido,
    MontoMinimoDomicilioNoAlcanzado,
    OperacionNoPermitidaEnEstado,
    PedidoNoEsADomicilio,
    PedidoNoEstaListo,
    PedidoYaTienePromocion,
    ProductoNoEstaAgotado,
)
from .eventos import (
    LineaDePedidoCancelada,
    PedidoCancelado,
    PedidoConfirmado,
    PedidoEntregaNoCompletada,
    PedidoEntregado,
    PedidoListo,
    PreparacionIniciada,
    PromocionAplicadaAPedido,
)
from .maquina_estados import MaquinaDeEstados
from .specifications import MontoMinimoDomicilio
from .valores import (
    Canal,
    Cancelacion,
    DatosCliente,
    Dinero,
    EstacionCocina,
    ProductoPedido,
    PromocionAplicada,
    Responsable,
    Rol,
    TipoCancelacion,
)


class EstadoPedido(Enum):
    """Estados del pedido. Nombres del paquete del PIA + LISTO y ENTREGA_NO_COMPLETADA (decisión B, H-12).

    Equivalencias con la U3: CREADO = Capturado, ACEPTADO = Confirmado.
    """
    CREADO = "creado"
    ACEPTADO = "aceptado"
    EN_PREPARACION = "en_preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"
    ENTREGA_NO_COMPLETADA = "entrega_no_completada"


class AccionPedido(Enum):
    ACEPTAR = "aceptar"
    INICIAR_PREPARACION = "iniciar_preparacion"
    MARCAR_LISTO = "marcar_listo"
    ENTREGAR = "entregar"
    FALLAR_ENTREGA = "fallar_entrega"
    CANCELAR = "cancelar"


_E, _A = EstadoPedido, AccionPedido
MAQUINA_PEDIDO = MaquinaDeEstados("pedido", {
    (_E.CREADO, _A.ACEPTAR): _E.ACEPTADO,
    (_E.CREADO, _A.CANCELAR): _E.CANCELADO,                    # RN-02: sin preparación, sin autorización
    (_E.ACEPTADO, _A.INICIAR_PREPARACION): _E.EN_PREPARACION,
    (_E.ACEPTADO, _A.CANCELAR): _E.CANCELADO,                  # RN-02 si ninguna estación inició
    (_E.EN_PREPARACION, _A.MARCAR_LISTO): _E.LISTO,
    (_E.EN_PREPARACION, _A.CANCELAR): _E.CANCELADO,            # RN-03: autorización + merma
    (_E.LISTO, _A.ENTREGAR): _E.ENTREGADO,
    (_E.LISTO, _A.FALLAR_ENTREGA): _E.ENTREGA_NO_COMPLETADA,   # RN-11
    (_E.LISTO, _A.CANCELAR): _E.CANCELADO,                     # RN-03: ya hubo preparación
})


class EstadoPreparacion(Enum):
    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    TERMINADA = "terminada"


@dataclass
class LineaPedido:
    id: str
    producto: ProductoPedido
    cantidad: int
    estacion: EstacionCocina  # estación que prepara la línea (supuesto: la define el producto)
    modificaciones: tuple = ()

    @property
    def subtotal(self) -> Dinero:
        return self.producto.precio_unitario.por(self.cantidad)


@dataclass
class PreparacionEstacion:
    estacion: EstacionCocina
    estado: EstadoPreparacion = EstadoPreparacion.PENDIENTE


class Pedido:
    MONTO_MINIMO_DOMICILIO = Dinero.mxn(150)  # RN-01

    def __init__(self, id, canal, responsable, lineas, cliente, mesa):
        self.id = id
        self.canal = canal
        self.responsable = responsable  # RN-14
        self.lineas = list(lineas)
        self.cliente = cliente
        self.mesa = mesa
        self.estado = EstadoPedido.CREADO
        self.preparaciones: dict = {}
        self.promocion: PromocionAplicada | None = None
        self.cancelaciones: list = []
        self._eventos: list = []

    # -- creación ------------------------------------------------------------
    @classmethod
    def crear(cls, id, canal: Canal, responsable: Responsable, lineas, cliente: DatosCliente | None = None, mesa=None):
        if canal is Canal.DOMICILIO and (cliente is None or not cliente.telefono or not cliente.direccion):
            raise DatosDeDomicilioIncompletos("El domicilio exige teléfono y dirección")
        return cls(id, canal, responsable, lineas, cliente, mesa)

    # -- consultas internas --------------------------------------------------
    @property
    def subtotal(self) -> Dinero:
        total = Dinero.cero()
        for linea in self.lineas:
            total = total + linea.subtotal
        return total

    @property
    def total(self) -> Dinero:
        descuento = self.promocion.descuento if self.promocion else Dinero.cero()
        return self.subtotal - descuento

    @property
    def preparacion_iniciada(self) -> bool:
        return any(p.estado is not EstadoPreparacion.PENDIENTE for p in self.preparaciones.values())

    @property
    def acciones_permitidas(self) -> list:
        return MAQUINA_PEDIDO.acciones_permitidas(self.estado)

    def _transicionar(self, accion: AccionPedido):
        """Único punto donde cambia el estado: lo decide la tabla de la máquina de estados."""
        self.estado = MAQUINA_PEDIDO.transicionar(self.estado, accion)

    def _exigir_no_final(self):
        if MAQUINA_PEDIDO.es_final(self.estado):
            raise OperacionNoPermitidaEnEstado(f"El pedido está {self.estado.value}")

    # -- comportamiento (casos de uso) ---------------------------------------
    def confirmar(self):
        """CU-01. RN-01: domicilio con total menor al mínimo no se confirma."""
        MAQUINA_PEDIDO.transicionar(self.estado, AccionPedido.ACEPTAR)  # valida antes de tocar nada
        if not MontoMinimoDomicilio(self.MONTO_MINIMO_DOMICILIO).es_satisfecha_por(self):
            raise MontoMinimoDomicilioNoAlcanzado(self.MONTO_MINIMO_DOMICILIO - self.total)
        for linea in self.lineas:
            self.preparaciones.setdefault(linea.estacion, PreparacionEstacion(linea.estacion))
        self._transicionar(AccionPedido.ACEPTAR)
        self._eventos.append(PedidoConfirmado(self.id))

    def aplicar_promocion(self, promocion: PromocionAplicada):
        """CU-02. RN-04: una sola promoción por pedido."""
        self._exigir_no_final()
        if self.promocion is not None:
            raise PedidoYaTienePromocion("Las promociones no son acumulables")
        self.promocion = promocion
        self._eventos.append(PromocionAplicadaAPedido(self.id, promocion.promocion_id))

    def cancelar(self, solicitante: Responsable, motivo: str, autorizador: Responsable | None = None):
        """CU-03. RN-02: sin preparación iniciada se cancela directo.
        RN-03: con preparación iniciada exige al Encargado y genera merma."""
        MAQUINA_PEDIDO.transicionar(self.estado, AccionPedido.CANCELAR)  # valida antes de tocar nada
        preparacion_iniciada = self.preparacion_iniciada
        if preparacion_iniciada and (autorizador is None or autorizador.rol is not Rol.ENCARGADO):
            raise CancelacionRequiereAutorizacion("Se requiere la autorización del Encargado")
        self.cancelaciones.append(
            Cancelacion(TipoCancelacion.TOTAL, motivo, solicitante, autorizador, datetime.now())
        )
        self._transicionar(AccionPedido.CANCELAR)
        self._eventos.append(PedidoCancelado(self.id, requiere_merma=preparacion_iniciada))

    def quitar_linea(self, linea_id: str, producto_agotado: bool, responsable: Responsable):
        """CU-04b. RN-06 (cancelación parcial). Supuesto H-08: RN-06 prevalece sobre RN-12
        cuando el producto está agotado."""
        self._exigir_no_final()
        linea = next((l for l in self.lineas if l.id == linea_id), None)
        if linea is None:
            raise LineaNoExiste(linea_id)
        if not producto_agotado:
            raise ProductoNoEstaAgotado(linea.producto.nombre)
        self.lineas.remove(linea)
        self.cancelaciones.append(
            Cancelacion(TipoCancelacion.PARCIAL, "Producto agotado", responsable, None, datetime.now())
        )
        self._eventos.append(LineaDePedidoCancelada(self.id, linea_id))

    # -- avance de preparación (flujo de cocina, fuera de los 5 casos) --------
    def iniciar_preparacion(self, estacion: EstacionCocina):
        if self.estado is not EstadoPedido.EN_PREPARACION:  # la 2.ª estación no cambia el estado del pedido
            MAQUINA_PEDIDO.transicionar(self.estado, AccionPedido.INICIAR_PREPARACION)  # valida antes de tocar nada
        if estacion not in self.preparaciones:
            raise EstacionSinLineasEnElPedido(estacion.value)
        if self.estado is not EstadoPedido.EN_PREPARACION:
            self._transicionar(AccionPedido.INICIAR_PREPARACION)
        self.preparaciones[estacion].estado = EstadoPreparacion.EN_PREPARACION
        self._eventos.append(PreparacionIniciada(self.id, estacion.value))

    def marcar_listo(self):
        self._transicionar(AccionPedido.MARCAR_LISTO)
        for preparacion in self.preparaciones.values():
            preparacion.estado = EstadoPreparacion.TERMINADA
        self._eventos.append(PedidoListo(self.id, self.canal is Canal.DOMICILIO))

    # -- cierre por entrega (CU-05) ------------------------------------------
    def validar_entrega_a_domicilio(self):
        if self.canal is not Canal.DOMICILIO:
            raise PedidoNoEsADomicilio(self.id)
        if self.estado is not EstadoPedido.LISTO:
            raise PedidoNoEstaListo(self.id)

    def marcar_entregado(self):
        self._transicionar(AccionPedido.ENTREGAR)
        self._eventos.append(PedidoEntregado(self.id))

    def marcar_entrega_no_completada(self):
        self._transicionar(AccionPedido.FALLAR_ENTREGA)
        self._eventos.append(PedidoEntregaNoCompletada(self.id))

    # -- eventos -------------------------------------------------------------
    def recoger_eventos(self) -> list:
        eventos, self._eventos = self._eventos, []
        return eventos
