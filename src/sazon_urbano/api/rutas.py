"""Endpoints REST. Solo traducen HTTP <-> Commands/Queries: las reglas viven en el dominio."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request

from sazon_urbano.application import comandos as c
from sazon_urbano.application.catalogo import ItemSolicitado, lineas_desde_catalogo
from sazon_urbano.domain.errores import OperacionNoEncontrada
from sazon_urbano.domain.specifications import beneficio_referencia, puede_procesarse
from sazon_urbano.domain.valores import DatosCliente, Responsable

from . import esquemas as s
from .dependencias import Contexto, contexto, responsable

router = APIRouter()
ERRORES = {
    400: {"model": s.ErrorOut, "description": "Solicitud mal formada o rol no reconocido"},
    401: {"model": s.ErrorOut, "description": "Falta identificar al usuario (X-Usuario-Id, X-Rol)"},
    403: {"model": s.ErrorOut, "description": "El rol no tiene permiso para la acción (US-19)"},
    404: {"model": s.ErrorOut, "description": "El recurso no existe"},
    409: {"model": s.ErrorOut, "description": "Conflicto con el estado actual (transición inválida, etc.)"},
    422: {"model": s.ErrorOut, "description": "Regla de negocio incumplida"},
}


def _pedido_out(r) -> s.ResultadoPedidoOut:
    return s.ResultadoPedidoOut(pedido_id=r.pedido_id, total=r.total.monto, estado=r.estado, genero_merma=r.genero_merma)


def _entrega_out(r) -> s.ResultadoEntregaOut:
    return s.ResultadoEntregaOut(entrega_id=r.entrega_id, estado=r.estado)


# -- Pedidos (CU-01, CU-02, CU-03, CU-04b) -------------------------------------
@router.post("/pedidos", status_code=201, response_model=s.ResultadoPedidoOut, tags=["Pedidos"],
             summary="Registrar un pedido (CU-01)", responses=ERRORES)
def registrar_pedido(datos: s.RegistrarPedidoIn, quien: Responsable = Depends(responsable),
                     ctx: Contexto = Depends(contexto)):
    """Precio y estación los toma el sistema del catálogo. Aplica RN-01 (mínimo a domicilio) y RN-14."""
    items = [ItemSolicitado(i.platillo_id, i.cantidad, tuple(i.modificaciones)) for i in datos.items]
    lineas = lineas_desde_catalogo(ctx.catalogo, ctx.app.disponibilidad, items)
    cliente = DatosCliente(datos.cliente.nombre, datos.cliente.telefono, datos.cliente.direccion) if datos.cliente else None
    return _pedido_out(ctx.app.pedidos_svc.registrar_pedido(c.RegistrarPedido(datos.canal, lineas, quien, cliente, datos.mesa)))


@router.get("/pedidos/{pedido_id}", response_model=s.ResumenPedidoOut, tags=["Pedidos"],
            summary="Consultar el resumen de un pedido", responses={404: ERRORES[404]})
def consultar_pedido(pedido_id: str, ctx: Contexto = Depends(contexto)):
    return ctx.resumen.manejar(pedido_id)


@router.post("/pedidos/{pedido_id}/promocion", response_model=s.ResultadoPedidoOut, tags=["Pedidos"],
             summary="Aplicar una promoción vigente (CU-02)", responses=ERRORES)
def aplicar_promocion(pedido_id: str, datos: s.AplicarPromocionIn, quien: Responsable = Depends(responsable),
                      ctx: Contexto = Depends(contexto)):
    """RN-04: una sola promoción. RN-05: la elige explícitamente Caja; el sistema nunca la aplica solo."""
    cmd = c.AplicarPromocion(pedido_id, datos.promocion_id, datos.fecha_hora or datetime.now(), quien)
    return _pedido_out(ctx.app.pedidos_svc.aplicar_promocion(cmd))


@router.post("/pedidos/{pedido_id}/cancelacion", response_model=s.ResultadoPedidoOut, tags=["Pedidos"],
             summary="Cancelar un pedido (CU-03)", responses=ERRORES)
def cancelar_pedido(pedido_id: str, datos: s.CancelarIn, quien: Responsable = Depends(responsable),
                    ctx: Contexto = Depends(contexto)):
    """RN-02: sin preparación iniciada se cancela directo. RN-03: con preparación iniciada exige al Encargado y genera merma.
    La identidad del autorizador es simulada (supuesto H-10)."""
    autorizador = Responsable(datos.autorizador.usuario_id, datos.autorizador.rol) if datos.autorizador else None
    return _pedido_out(ctx.app.pedidos_svc.cancelar_pedido(c.CancelarPedido(pedido_id, datos.motivo, quien, autorizador)))


@router.delete("/pedidos/{pedido_id}/lineas/{linea_id}", response_model=s.ResultadoPedidoOut, tags=["Pedidos"],
               summary="Quitar una línea de un producto agotado (CU-04b)", responses=ERRORES)
def quitar_linea(pedido_id: str, linea_id: str, quien: Responsable = Depends(responsable),
                 ctx: Contexto = Depends(contexto)):
    """RN-06: cancelación parcial. Solo procede si el producto está marcado como agotado."""
    return _pedido_out(ctx.app.disponibilidad_svc.gestionar_producto_agotado(c.QuitarLineaAgotada(pedido_id, linea_id, quien)))


@router.post("/pedidos/{pedido_id}/preparacion", response_model=s.ResultadoPedidoOut, tags=["Cocina"],
             summary="Iniciar la preparación en una estación", responses=ERRORES)
def iniciar_preparacion(pedido_id: str, datos: s.IniciarPreparacionIn, quien: Responsable = Depends(responsable),
                        ctx: Contexto = Depends(contexto)):
    return _pedido_out(ctx.app.preparacion_svc.gestionar_preparacion(c.IniciarPreparacion(pedido_id, datos.estacion, quien)))


@router.post("/pedidos/{pedido_id}/listo", response_model=s.ResultadoPedidoOut, tags=["Cocina"],
             summary="Marcar el pedido como listo", responses=ERRORES)
def marcar_listo(pedido_id: str, quien: Responsable = Depends(responsable), ctx: Contexto = Depends(contexto)):
    return _pedido_out(ctx.app.preparacion_svc.gestionar_preparacion(c.MarcarPedidoListo(pedido_id, quien)))


# -- Disponibilidad (CU-04a) -----------------------------------------------------
@router.post("/productos/{producto_id}/agotado", status_code=200, tags=["Cocina"],
             summary="Marcar un producto como agotado (CU-04a)", responses=ERRORES)
def marcar_agotado(producto_id: str, quien: Responsable = Depends(responsable), ctx: Contexto = Depends(contexto)):
    ctx.catalogo.obtener(producto_id)  # 404 si el platillo no existe
    ctx.app.disponibilidad_svc.gestionar_producto_agotado(c.MarcarProductoAgotado(producto_id, quien))
    return {"producto_id": producto_id, "disponible": False}


# -- Entregas (CU-05) --------------------------------------------------------------
@router.post("/entregas", status_code=201, response_model=s.ResultadoEntregaOut, tags=["Entregas"],
             summary="Asignar un repartidor a un pedido a domicilio (CU-05)", responses=ERRORES)
def asignar_repartidor(datos: s.AsignarRepartidorIn, quien: Responsable = Depends(responsable),
                       ctx: Contexto = Depends(contexto)):
    return _entrega_out(ctx.app.entregas_svc.gestionar_entrega(c.AsignarRepartidor(datos.pedido_id, datos.repartidor_id, quien)))


@router.post("/entregas/{entrega_id}/salida", response_model=s.ResultadoEntregaOut, tags=["Entregas"],
             summary="Registrar la hora de salida", responses=ERRORES)
def registrar_salida(entrega_id: str, quien: Responsable = Depends(responsable), ctx: Contexto = Depends(contexto)):
    return _entrega_out(ctx.app.entregas_svc.gestionar_entrega(c.RegistrarSalidaDeEntrega(entrega_id, quien)))


@router.post("/entregas/{entrega_id}/confirmacion", response_model=s.ResultadoEntregaOut, tags=["Entregas"],
             summary="Confirmar la entrega al cliente", responses=ERRORES)
def confirmar_entrega(entrega_id: str, quien: Responsable = Depends(responsable), ctx: Contexto = Depends(contexto)):
    return _entrega_out(ctx.app.entregas_svc.gestionar_entrega(c.ConfirmarEntrega(entrega_id, quien)))


@router.post("/entregas/{entrega_id}/fallida", response_model=s.ResultadoEntregaOut, tags=["Entregas"],
             summary="Registrar una entrega fallida con su motivo (RN-11)", responses=ERRORES)
def registrar_entrega_fallida(entrega_id: str, datos: s.EntregaFallidaIn, quien: Responsable = Depends(responsable),
                              ctx: Contexto = Depends(contexto)):
    return _entrega_out(ctx.app.entregas_svc.gestionar_entrega(c.RegistrarEntregaFallida(entrega_id, datos.motivo, quien)))


# -- Consultas ---------------------------------------------------------------------
@router.get("/menu", response_model=list[s.ProductoOut], tags=["Consultas"], summary="Menú con disponibilidad (US-04)")
def consultar_menu(ctx: Contexto = Depends(contexto)):
    return ctx.menu.manejar()


@router.get("/promociones/vigentes", response_model=list[s.PromocionOut], tags=["Consultas"],
            summary="Promociones vigentes en una fecha y hora")
def consultar_promociones_vigentes(fecha_hora: datetime | None = None, ctx: Contexto = Depends(contexto)):
    return ctx.promociones.manejar(fecha_hora or datetime.now())


@router.get("/repartidores/disponibles", response_model=list[s.RepartidorOut], tags=["Consultas"],
            summary="Repartidores disponibles (US-14)")
def consultar_repartidores_disponibles(ctx: Contexto = Depends(contexto)):
    return ctx.repartidores.manejar()


# -- Reglas del paquete del PIA ------------------------------------------------------
@router.get("/operaciones/{operacion_id}/evaluacion", response_model=s.EvaluacionOperacionOut,
            tags=["Paquete PIA"], summary="Evaluar puede_procesarse y beneficio_referencia",
            responses={404: ERRORES[404]})
def evaluar_operacion(operacion_id: str, request: Request):
    """Evalúa con Specifications una operación del paquete de datos del PIA (solo lectura)."""
    operacion = request.app.state.paquete.operaciones.get(operacion_id)
    if operacion is None:
        raise OperacionNoEncontrada(operacion_id)
    regla = puede_procesarse()
    return s.EvaluacionOperacionOut(
        operacion_id=operacion_id, total=operacion.total.monto,
        puede_procesarse=regla.es_satisfecha_por(operacion), motivos_de_rechazo=regla.motivos_de_rechazo(operacion),
        beneficio_referencia=beneficio_referencia().es_satisfecha_por(operacion))


@router.get("/salud", tags=["Operación"], summary="Estado del servicio")
def salud():
    return {"estado": "ok"}
