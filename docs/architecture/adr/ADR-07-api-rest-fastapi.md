# ADR-07: API REST con FastAPI como capa de entrada

**Estado:** Aceptada · **Fecha:** 03/11/2026

## Contexto
El PIA exige una API REST documentada con OpenAPI/Swagger y que responda con 200/201, 400/409/422 y 404 según el contrato
del equipo. El dominio y la aplicación ya existen (U3, ADR-01 a ADR-06); falta la capa `api`.

## Alternativas
- **Flask + generación manual de OpenAPI:** conocido, pero la documentación se escribiría a mano y se desactualiza.
- **Django REST Framework:** completo, pero trae un ORM propio que choca con el dominio (ADR-06).
- **FastAPI:** OpenAPI y Swagger UI automáticos desde el código, validación declarativa de las solicitudes.

## Decisión
`api/` (FastAPI + Pydantic) solo traduce HTTP ↔ Commands/Queries de la capa de aplicación. No contiene reglas de negocio.
- **Errores:** `api/errores.py` traduce las excepciones del dominio a códigos HTTP (404, 403, 409, 422); las solicitudes mal
  formadas responden 400; los errores técnicos 500 sin exponer detalles.
- **Identidad:** encabezados `X-Usuario-Id` y `X-Rol` (autenticación simulada); el permiso por rol sigue en `ControlDeAcceso`.
- **Una sesión de BD por solicitud:** `dependencias.contexto` arma la aplicación con la Unit of Work SQL (ADR-06).
- **Catálogo:** el cliente envía `platillo_id` y `cantidad`; precio y estación los pone el sistema (snapshot, H-09).
- **Queries:** `GET` de resumen, menú, promociones vigentes y repartidores, con DTO y sin exponer aggregates (ADR-03).
- La arquitectura se verifica por código: dominio y aplicación no importan FastAPI/Pydantic ni la capa `api`.

## Consecuencias
- **Beneficios:** contrato OpenAPI siempre coherente con el código; la API es una capa delgada y reemplazable.
- **Costos:** esquemas Pydantic que duplican parcialmente los comandos (se aceptan por mantener el dominio sin frameworks).
- **Riesgos:** la identidad por encabezados no es segura para producción (se declara como supuesto).
- **Pendiente:** autenticación real, paginación y endpoints de administración (US-18, US-10, reportes).

## Trazabilidad
NEC-10, NEC-11, NEC-12 · RN-01 a RN-06, RN-11, RN-14 · US-01 a US-09, US-14, US-15, US-19 · CU-01 a CU-05
· Pruebas: `tests/test_api.py`, `tests/test_arquitectura.py` · Contrato: `docs/api/openapi.json`
