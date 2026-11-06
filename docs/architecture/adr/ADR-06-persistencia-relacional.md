# ADR-06: Persistencia relacional con SQLAlchemy y PostgreSQL

**Estado:** Aceptada · **Fecha:** 03/11/2026

## Contexto
La U3 solo tenía repositorios en memoria. El PIA exige persistencia/DB y Docker Compose con base de datos. El ADR-02
ya definió que las interfaces de Repository viven en el dominio y las implementaciones en infraestructura.

## Alternativas
- **Mapear las clases del dominio directamente con el ORM:** menos código, pero el dominio quedaría atado a SQLAlchemy.
- **Guardar cada aggregate como un documento JSON:** simple, pero no aprovecha el modelo relacional ni permite consultas/reportes.
- **Tablas relacionales + mapeo explícito dominio ↔ filas:** más código, dominio limpio y consultable.

## Decisión
PostgreSQL como base (SQLite en memoria para pruebas rápidas) y SQLAlchemy 2.x. Las tablas (`persistence/modelos.py`)
y el mapeo (`persistence/mapeo.py`) viven en infraestructura; el dominio no importa SQLAlchemy (lo verifica
`tests/test_arquitectura.py`). Cada aggregate se guarda completo: el Pedido reemplaza sus líneas, preparaciones y
cancelaciones. Los repositorios SQL no confirman: `UnitOfWorkSql` hace `commit`/`rollback`, una sesión por solicitud.
Las filas se reconstruyen en aggregates sin ejecutar reglas ni emitir eventos. La conexión se configura con variables
de entorno (`DATABASE_URL` o `DB_*`, ver `.env.example`).

## Consecuencias
- **Beneficios:** el mismo caso de uso corre sobre memoria o SQL sin cambios (principio L); `cancelarPedido` sigue
  guardando Pedido y Merma de forma atómica (RN-03); los datos sobreviven a un reinicio.
- **Costos:** el mapeo explícito se mantiene a mano cuando cambia un aggregate.
- **Riesgos:** sin control de concurrencia (aceptado en ADR-02). Las tablas se crean con `create_all`; si el
  esquema cambia en un sistema real habría que introducir migraciones (Alembic).
- **Pendiente:** tablas de catálogo y actores (solo lectura) se agregan junto con la API.

## Trazabilidad
NEC-01, NEC-04, NEC-11 · RN-03, RN-11, RN-13, RN-14 · ADR-02 · Pruebas: `tests/test_persistencia.py`
(SQLite y PostgreSQL 16)
