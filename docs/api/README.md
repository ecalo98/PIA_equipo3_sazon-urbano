# API REST y OpenAPI

- **Contrato OpenAPI:** [`openapi.json`](openapi.json), generado del código con `python scripts/exportar_openapi.py`.
- **Swagger UI** (con la API en ejecución): `http://localhost:8000/docs` · **ReDoc:** `/redoc` · **JSON:** `/openapi.json`.

## Cómo identificarse (autenticación simulada)

Los endpoints que cambian datos requieren los encabezados `X-Usuario-Id` y `X-Rol`
(`mesero`, `caja`, `cocina`, `encargado`, `repartidor`, `gerente`). El permiso por rol lo valida la capa de aplicación (US-19).
Una autenticación real (usuarios, contraseñas, tokens) queda fuera del alcance del PIA.

## Contrato de códigos HTTP

| Código | Cuándo | Ejemplos |
|---|---|---|
| 200 / 201 | Éxito (201 al crear un pedido o una entrega) | Pedido registrado, promoción aplicada |
| 400 | Solicitud mal formada o rol no reconocido | cantidad 0, canal inexistente, JSON sin campos |
| 401 | Falta identificar al usuario | Sin `X-Usuario-Id` o `X-Rol` |
| 403 | El rol no tiene permiso | Cocina intenta registrar un pedido; mesero aplica promoción |
| 404 | El recurso no existe | Pedido, platillo, entrega, repartidor, promoción o línea inexistente |
| 409 | Conflicto con el estado actual | Transición inválida, segunda promoción (RN-04), cancelar con preparación sin Encargado (RN-03), entrega sin salida (RN-11) |
| 422 | Regla de negocio incumplida | Domicilio < $150 (RN-01), promoción fuera de vigencia, platillo agotado, cantidad mayor al stock |
| 500 | Error técnico (no de negocio) | Falla de conexión con la base de datos |

Todo error responde `{"error": "<NombreDelError>", "mensaje": "...", "motivos": [...]}`.

## Endpoints y casos de uso

| Método y ruta | Caso de uso | Rol |
|---|---|---|
| `POST /pedidos` | CU-01 Registrar pedido | Mesero (mesa), Caja (demás canales) |
| `GET /pedidos/{id}` | Query: resumen del pedido | — |
| `POST /pedidos/{id}/promocion` | CU-02 Aplicar promoción | Caja |
| `POST /pedidos/{id}/cancelacion` | CU-03 Cancelar pedido | Mesero/Caja; autoriza Encargado |
| `POST /productos/{id}/agotado` | CU-04a Marcar agotado | Cocina |
| `DELETE /pedidos/{id}/lineas/{linea}` | CU-04b Quitar línea agotada | Mesero |
| `POST /entregas` | CU-05 Asignar repartidor | Encargado |
| `POST /entregas/{id}/salida` · `/confirmacion` · `/fallida` | CU-05 Registrar entrega | Repartidor |
| `POST /pedidos/{id}/preparacion` · `/listo` | Flujo de cocina (recorre la máquina de estados) | Cocina |
| `GET /menu` · `/promociones/vigentes` · `/repartidores/disponibles` | Queries | — |
| `GET /operaciones/{id}/evaluacion` | Reglas del paquete PIA (`puede_procesarse`, `beneficio_referencia`) | — |
| `GET /salud` | Estado del servicio | — |

El precio y la estación de cada línea los toma el sistema del catálogo; el cliente solo envía `platillo_id` y `cantidad`.
