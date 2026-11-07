"""Punto de entrada de la API.  Ejecutar:  uvicorn --factory sazon_urbano.api.main:crear_app"""
from __future__ import annotations

import os

from fastapi import FastAPI

from sazon_urbano.infrastructure.paquete_pia import PaquetePia
from sazon_urbano.infrastructure.persistence import semilla
from sazon_urbano.infrastructure.persistence.base_datos import crear_engine, crear_session_factory, crear_tablas

from .errores import registrar_manejadores
from .rutas import router

DESCRIPCION = """
API de **Sazón Urbano**: pedidos por mesa, teléfono/WhatsApp y domicilio.

**Autenticación simulada:** cada solicitud que cambia datos envía `X-Usuario-Id` y `X-Rol`
(mesero, caja, cocina, encargado, repartidor, gerente). El permiso por rol lo valida la capa de aplicación (US-19).

**Códigos:** 200/201 éxito · 400 solicitud mal formada · 401 sin identificar · 403 sin permiso ·
404 no existe · 409 conflicto de estado · 422 regla de negocio incumplida.
"""


def crear_app(url_bd: str | None = None, sembrar: bool | None = None) -> FastAPI:
    engine = crear_engine(url_bd)
    crear_tablas(engine)
    factory = crear_session_factory(engine)
    if sembrar is None:
        sembrar = os.environ.get("SEMBRAR_DATOS", "1") != "0"
    if sembrar:
        with factory() as sesion:
            semilla.cargar_catalogo(sesion)
            semilla.cargar_demo(sesion)
            semilla.cargar_paquete_pia(sesion)

    app = FastAPI(title="Sazón Urbano API", version="1.0.0", description=DESCRIPCION)
    app.state.engine, app.state.session_factory = engine, factory
    app.state.paquete = PaquetePia()  # datos de prueba del PIA, solo lectura
    registrar_manejadores(app)
    app.include_router(router)
    return app
