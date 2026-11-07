# Sazón Urbano: lógica de negocio (U3 y PIA)

Actividad práctica de la **Unidad 3** del curso *Componentes de Lógica de Negocios* (UANL, FIME).
Continúa el análisis de negocio de la Unidad 2 (BRD, user stories, glosario y BPMN) y lo convierte en una
propuesta de arquitectura que separa **dominio, aplicación e infraestructura**.

| | |
|---|---|
| **Empresa** | Sazón Urbano (restaurante con servicio en mesa, para llevar y a domicilio) |
| **Equipo** | 3 |
| **Integrantes** | Emmanuel Carrillo Loera · Edgar Daniel del Ángel Hernández · Fatima Alejandra Cavazos Serrato |
| **Curso / profesor** | Componentes de Lógica de Negocios · Miguel Ángel Gómez Marroquín |
| **Fecha de entrega** | 17/10/2026 |

## Alcance

Se diseñan **5 casos de uso** tomados del BRD de la Unidad 2:

| Caso | Descripción | Reglas principales |
|---|---|---|
| CU-01 | Registrar pedido | RN-01, RN-14 |
| CU-02 | Aplicar promoción | RN-04, RN-05 |
| CU-03 | Cancelar pedido | RN-02, RN-03, RN-10 |
| CU-04 | Gestionar producto agotado | RN-06, RN-12 |
| CU-05 | Asignar repartidor y registrar entrega | RN-11 |

Quedan **fuera** de este diseño (pero contabilizados en la matriz de trazabilidad): inventario en tiempo real,
alertas de existencia mínima, pedidos retrasados y reportes.

## Decisiones principales

- **Patrón de lógica de negocio:** Domain Model como patrón principal; Transaction Script solo para marcar un
  producto agotado; Table Module descartado en los 5 casos (ADR-01).
- **Persistencia:** interfaces de Repository en el dominio, implementaciones en infraestructura y una Unit of Work
  por solicitud (ADR-02).
- **CQRS básico:** Commands y Queries con handlers, DTO de lectura y una sola base de datos (ADR-03).
- **Revisión SOLID:** 7 hallazgos y 3 correcciones aplicadas.

## Cómo revisar este repositorio

| Orden | Qué revisar | Dónde |
|---|---|---|
| 1 | Decisiones de arquitectura (ADR) | `docs/architecture/adr/` |
| 2 | Diagramas de clases (fuente PlantUML y PNG): general + dominio, Specification/estados/eventos, aplicación, API/consultas e infraestructura | `docs/architecture/diagramas/clases*.puml`, `docs/architecture/diagramas/clases*.png` |
| 3 | Diagramas de secuencia (fuente y PNG) | `docs/architecture/diagramas/secuencia-registrar-pedido.*`, `docs/architecture/diagramas/secuencia-cancelar-pedido.*` |
| 4 | Diagrama de Dominio (drawio) | `docs/architecture/diagramas/Dominio*`|
| 5 | Código base | `src/sazon_urbano/` (`domain`, `application`, `infrastructure`, `api`) |
| 6 | Pruebas | `tests/` |
| 7 | Bitácora de uso de IA | `docs/architecture/u3/Bitácora de IA.pdf` |

## Instalación

Requisitos: Python 3.11 o superior (o Docker).

```
git clone <URL_DEL_REPOSITORIO>
cd repositorio-sazon-urbano
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                   # ajustar valores; .env no se sube al repositorio
```

## Ejecución con Docker

`docker-compose.yml` define 3 servicios: **db** (PostgreSQL 16), **app** (API FastAPI) y **tests** (pytest con cobertura).
La configuración sale de `.env` (12-Factor App); sin secretos en el código.

```
cp .env.example .env            # y cambiar DB_PASSWORD
docker compose up --build       # db + app  ->  Swagger UI: http://localhost:8000/docs
docker compose run --rm tests   # pruebas + cobertura contra PostgreSQL (corren también las 10 omitidas)
docker compose down -v          # apagar y borrar datos
```

Al arrancar, la app crea las tablas y siembra: catálogo, promoción de martes, repartidores y los **60 pedidos del
dataset del PIA** (`data/paquete_pia/`, importados a PostgreSQL con claves foráneas a `actores` y `platillos`).
Para no sembrar, `SEMBRAR_DATOS=0`. La base de pruebas (`<DB_NAME>_test`) se crea sola la primera vez que se crea el volumen.

## Despliegue

Plataforma: **Railway** (también sirve Render o Fly.io con el mismo `Dockerfile`).

1. Crear un proyecto desde el repositorio de GitHub (detecta el `Dockerfile`; el destino por defecto es `app`).
2. Agregar el plugin **PostgreSQL** y definir en el servicio de la app `DATABASE_URL` con la URL que entrega la plataforma
   (se acepta `postgres://` o `postgresql://`; el código la convierte a `postgresql+psycopg://`).
3. Opcional: `APP_ENV=production`. La plataforma inyecta `PORT`, que el contenedor ya usa.
4. Generar el dominio público y verificar `https://<dominio>/docs`.
5. (CD) Guardar el hook de despliegue como secreto `DEPLOY_HOOK_URL` en GitHub si se quiere disparar desde `.github/workflows/ci.yml`.

| | URL |
|---|---|
| Repositorio | _pendiente: https://github.com/…_ |
| Despliegue (Swagger UI) | _pendiente: https://…/docs_ |

## Demo

Con la API en marcha (`/docs`), flujo sugerido para la defensa. Los endpoints que cambian datos llevan los encabezados
`X-Usuario-Id` y `X-Rol` (ver `docs/api/README.md`):

1. `GET /openapi.json` y `/docs` para mostrar el contrato.
2. Registrar un pedido a domicilio menor a $150 → **422** (RN-01); uno válido → **201**.
3. Aplicar la promoción de martes y una segunda promoción → **409** (RN-04).
4. Cancelar un pedido en preparación como mesero → **409**; como encargado → permitido (RN-03).
5. Mostrar en PostgreSQL los 60 pedidos importados: `docker compose exec db psql -U $DB_USER -d $DB_NAME -c "SELECT count(*) FROM operaciones_pia;"`.

## Cómo ejecutar las pruebas

Requisitos: Python 3.11 o superior y `pip install -r requirements-dev.txt`.

```
pip install -r requirements-dev.txt
pytest --cov            # pruebas unitarias e integración + cobertura (mínimo 80 %, configurado en pyproject.toml)
```

Las pruebas están en `tests/unit` (reglas puras: Specifications, máquina de estados, arquitectura) y `tests/integration`
(casos de uso, persistencia SQL y API). También corren con `python -m unittest discover`.

Para correr también las pruebas de persistencia contra PostgreSQL:

```
TEST_DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@localhost:5432/sazon_test pytest --cov
```

Ejecutar la API (Swagger UI en http://localhost:8000/docs):

```
PYTHONPATH=src uvicorn --factory sazon_urbano.api.main:crear_app --port 8000
```

Sin variables de base de datos usa un SQLite local; con `DB_HOST`/`DATABASE_URL` usa PostgreSQL (ver `.env.example`).
El contrato de la API está en `docs/api/README.md` y `docs/api/openapi.json`.

Ejecutar los 120 casos del paquete del PIA con las Specifications y generar evidencia:

```
python scripts/ejecutar_casos_prueba.py      # 120 casos con Specifications
python scripts/ejecutar_transiciones.py      # 20 transiciones con la máquina de estados
python scripts/generar_diagrama_estados.py   # regenera el diagrama de estados desde el código
```

Las pruebas cubren los 5 casos de uso y verifican por código la regla de dependencias
(el dominio no importa aplicación ni infraestructura, ni librerías de SQL).

## Estructura

```
docs/BRD/            BRD de la Unidad 2 (sin modificar)
docs/analisis/       User stories, glosario y BPMN de la U2 (sin modificar) + conciliación con el paquete PIA
docs/architecture/   ADR, diagramas y entregables de la U3
docs/api/            Contrato OpenAPI y códigos HTTP
data/paquete_pia/    CSV del paquete de datos del PIA (sin modificar)
evidencias/          Resultados de la ejecución de los casos de prueba
scripts/             Utilidades (ejecución de casos de prueba)
src/sazon_urbano/    domain · application · infrastructure · api
fixtures/            Menú propio de Sazón Urbano (complementa el paquete)
tests/               Pruebas de los casos de uso y de la arquitectura
.env.example         Variables de entorno de ejemplo (sin secretos)
Dockerfile           Imagen con destinos app y tests
docker-compose.yml   db (PostgreSQL) + app + tests
docker/              Script que crea la base de pruebas
```

## Supuestos y hallazgos

Los hallazgos sobre la Unidad 2 y los supuestos pendientes de validación (por ejemplo, Mesero y Caja como roles
separados) están registrados en la matriz de trazabilidad (pendiente de regenerar en el PIA).

## Uso de IA

Se usó Claude (Anthropic) como apoyo. Cada propuesta fue revisada contra el BRD y la guía de la actividad.
Los prompts, errores detectados y decisiones del equipo están en `docs/architecture/u3/Bitácora de IA.pdf`.
