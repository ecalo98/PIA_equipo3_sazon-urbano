"""Conexión a la base de datos. La configuración viene de variables de entorno (.env.example)."""
from __future__ import annotations

import os
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .modelos import Base


def _normalizar_url(url: str) -> str:
    """Railway/Render/Fly.io entregan `postgres://` o `postgresql://`; SQLAlchemy necesita el driver psycopg."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


def url_desde_entorno(entorno=os.environ) -> str:
    """DATABASE_URL si existe; si no, PostgreSQL con DB_*; sin nada configurado, un SQLite local de desarrollo."""
    if entorno.get("DATABASE_URL"):
        return _normalizar_url(entorno["DATABASE_URL"])
    if entorno.get("DB_HOST"):
        usuario, clave = entorno.get("DB_USER", ""), entorno.get("DB_PASSWORD", "")
        return (f"postgresql+psycopg://{quote_plus(usuario)}:{quote_plus(clave)}"
                f"@{entorno['DB_HOST']}:{entorno.get('DB_PORT', '5432')}/{entorno.get('DB_NAME', 'sazon_urbano')}")
    return "sqlite:///sazon_urbano.db"


def crear_engine(url: str | None = None) -> Engine:
    url = url or url_desde_entorno()
    if url.startswith("sqlite"):
        # La API atiende cada solicitud en un hilo distinto; en memoria hace falta una sola conexión compartida.
        opciones = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            opciones["poolclass"] = StaticPool
        engine = create_engine(url, future=True, **opciones)
    else:
        engine = create_engine(url, future=True, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":  # SQLite ignora las llaves foráneas salvo que se active
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def crear_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def crear_tablas(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def borrar_tablas(engine: Engine) -> None:
    Base.metadata.drop_all(engine)
