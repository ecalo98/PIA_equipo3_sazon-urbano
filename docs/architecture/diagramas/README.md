# Diagramas de arquitectura

Todos los diagramas de clases usan los nombres reales del código (`src/sazon_urbano/`). Las flechas de
dependencia apuntan hacia las interfaces, nunca hacia las implementaciones.

| Archivo | Qué muestra | Capa |
|---|---|---|
| `clases.puml/png` | Vista general por capas (solo clases principales) | Todas |
| `clases-dominio.puml/png` | Aggregates (Pedido, Promoción, Entrega, Repartidor, Merma), entidades, Value Objects, Domain Services y puertos de persistencia | `domain/` |
| `clases-specifications.puml/png` | Patrón Specification (AND/OR/NOT), máquina de estados del Pedido y los 14 Domain Events | `domain/` |
| `clases-aplicacion.puml/png` | Application Services, Commands y Handlers, puertos (Service Layer + CQRS, lado escritura) | `application/` |
| `clases-api-consultas.puml/png` | API REST (17 endpoints), traducción de errores, Queries y DTO (CQRS, lado lectura) | `api/` + `application/` |
| `clases-infraestructura.puml/png` | Repositorios en memoria y SQL, Unit of Work, mapeo, tablas, composición y datos del PIA | `infrastructure/` |
| `secuencia-registrar-pedido.puml/png` | CU-01, flujo principal | — |
| `secuencia-cancelar-pedido.puml/png` | CU-03, regla con excepción y alternativa | — |
| `estados-pedido.puml/png` | Máquina de estados del Pedido (se genera desde el código) | `domain/` |
| `Dominio.drawio.png` | Mapa de dominio (DDD) | — |

## Regenerar los PNG

PlantUML limita el ancho de imagen por defecto; hay que subir el límite para que no se recorte:

```bash
java -DPLANTUML_LIMIT_SIZE=20000 -jar plantuml.jar -tpng -charset UTF-8 docs/architecture/diagramas/clases*.puml
```

El diagrama de estados se regenera con `python scripts/generar_diagrama_estados.py`.
