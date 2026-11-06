"""Traducción de errores del dominio a códigos HTTP (contrato del equipo, ver docs/api/README.md).

400 solicitud mal formada · 401 sin identificar · 403 sin permiso · 404 no existe ·
409 conflicto con el estado actual · 422 regla de negocio incumplida · 500 error técnico.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sazon_urbano.domain import errores as e

log = logging.getLogger("sazon_urbano.api")

CODIGOS = {
    e.PedidoNoEncontrado: 404, e.PromocionNoEncontrada: 404, e.EntregaNoEncontrada: 404,
    e.RepartidorNoEncontrado: 404, e.PlatilloNoEncontrado: 404, e.OperacionNoEncontrada: 404, e.LineaNoExiste: 404,
    e.AccesoDenegado: 403,
    e.OperacionNoPermitidaEnEstado: 409,   # incluye TransicionDeEstadoInvalida
    e.PedidoYaTienePromocion: 409, e.CancelacionRequiereAutorizacion: 409, e.RepartidorNoDisponible: 409,
    e.PedidoNoEstaListo: 409, e.EntregaSinSalidaRegistrada: 409, e.ProductoNoEstaAgotado: 409,
    e.ErrorDeNegocio: 422,                 # cualquier otra regla de negocio incumplida
}


def codigo_para(error: Exception) -> int:
    for clase in type(error).__mro__:
        if clase in CODIGOS:
            return CODIGOS[clase]
    return 500


def _cuerpo(error: Exception, **extra) -> dict:
    cuerpo = {"error": type(error).__name__, "mensaje": str(error)}
    motivos = getattr(error, "motivos", None)
    if motivos:
        cuerpo["motivos"] = motivos
    return {**cuerpo, **extra}


class ErrorDeApi(Exception):
    """Errores propios de la capa API (identificación), no del dominio."""

    def __init__(self, codigo: int, error: str, mensaje: str):
        super().__init__(mensaje)
        self.codigo, self.error, self.mensaje = codigo, error, mensaje


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(ErrorDeApi)
    async def _api(_: Request, error: ErrorDeApi):
        return JSONResponse(status_code=error.codigo, content={"error": error.error, "mensaje": error.mensaje})

    @app.exception_handler(e.ErrorDeNegocio)
    async def _negocio(_: Request, error: e.ErrorDeNegocio):
        return JSONResponse(status_code=codigo_para(error), content=_cuerpo(error))

    @app.exception_handler(RequestValidationError)
    async def _mal_formada(_: Request, error: RequestValidationError):
        detalles = [{"campo": ".".join(str(p) for p in d["loc"] if p != "body"), "problema": d["msg"]} for d in error.errors()]
        return JSONResponse(status_code=400, content={"error": "SolicitudMalFormada",
                                                      "mensaje": "La solicitud no cumple el esquema", "detalles": detalles})

    @app.exception_handler(Exception)
    async def _tecnico(_: Request, error: Exception):
        log.exception("Error técnico no controlado")  # el detalle va al log, no al cliente
        return JSONResponse(status_code=500, content={"error": "ErrorTecnico", "mensaje": "Error interno del servidor"})
