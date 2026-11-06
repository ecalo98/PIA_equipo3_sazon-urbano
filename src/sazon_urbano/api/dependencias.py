"""Dependencias de FastAPI: identidad del usuario y contexto por solicitud (una sesión de BD por request)."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader

from sazon_urbano.application import consultas as q
from sazon_urbano.domain.valores import Responsable, Rol
from sazon_urbano.infrastructure.composicion import Aplicacion, construir_aplicacion_sql
from sazon_urbano.infrastructure.persistence import consultas_sql as cs

from .errores import ErrorDeApi

_usuario = APIKeyHeader(name="X-Usuario-Id", scheme_name="UsuarioId", auto_error=False,
                        description="Identificador del usuario que actúa (autenticación simulada).")
_rol = APIKeyHeader(name="X-Rol", scheme_name="Rol", auto_error=False,
                    description="mesero, caja, cocina, encargado, repartidor, gerente o cliente.")


def responsable(usuario: str | None = Depends(_usuario), rol: str | None = Depends(_rol)) -> Responsable:
    """Identifica quién actúa (RN-14, NEC-04). El permiso por rol lo valida la capa de aplicación (US-19)."""
    if not usuario or not rol:
        raise ErrorDeApi(401, "NoIdentificado", "Falta X-Usuario-Id o X-Rol")
    try:
        return Responsable(usuario, Rol(rol.strip().lower()))
    except ValueError:
        validos = ", ".join(r.value for r in Rol)
        raise ErrorDeApi(400, "RolInvalido", f"Rol '{rol}' no reconocido. Válidos: {validos}") from None


@dataclass
class Contexto:
    app: Aplicacion
    catalogo: cs.CatalogoDePlatillosSql
    resumen: q.ConsultarResumenDelPedidoHandler
    menu: q.ConsultarMenuDisponibleHandler
    promociones: q.ConsultarPromocionesVigentesHandler
    repartidores: q.ConsultarRepartidoresDisponiblesHandler


def contexto(request: Request):
    session = request.app.state.session_factory()
    try:
        yield Contexto(
            app=construir_aplicacion_sql(session),
            catalogo=cs.CatalogoDePlatillosSql(session),
            resumen=q.ConsultarResumenDelPedidoHandler(cs.ConsultasDePedidosSql(session)),
            menu=q.ConsultarMenuDisponibleHandler(cs.ConsultasDeMenuSql(session)),
            promociones=q.ConsultarPromocionesVigentesHandler(cs.ConsultasDePromocionesSql(session)),
            repartidores=q.ConsultarRepartidoresDisponiblesHandler(cs.ConsultasDeRepartidoresSql(session)),
        )
    finally:
        session.close()
