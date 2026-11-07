# Sazón Urbano: lógica de negocio (PIA)

Proyecto Integrador de Aprendizaje (PIA) del curso *Componentes de Lógica de Negocios* (UANL, FIME).
Continúa el análisis de negocio de la Unidad 2 (BRD, user stories, glosario y BPMN) y el diseño de arquitectura de la
Unidad 3, y los convierte en un **sistema funcional**: dominio con Specifications y máquina de estados, API REST con
OpenAPI, base de datos PostgreSQL, pruebas automáticas con cobertura, CI/CD, Docker Compose y despliegue en Render.

| | |
|---|---|
| **Empresa** | Sazón Urbano (restaurante con servicio en mesa, para llevar y a domicilio) |
| **Equipo** | 3 |
| **Integrantes** | Emmanuel Carrillo Loera · Edgar Daniel del Ángel Hernández · Fatima Alejandra Cavazos Serrato |
| **Curso / profesor** | Componentes de Lógica de Negocios · Miguel Ángel Gómez Marroquín |
| **Fecha de entrega** | 06/11/2026 |
| **Repositorio** | https://github.com/ecalo98/PIA_equipo3_sazon-urbano |
| **Despliegue (Swagger UI)** | https://pia-equipo3-sazon-urbano.onrender.com/docs |

## Alcance

Se implementan **5 casos de uso** tomados del BRD de la Unidad 2:

| Caso | Descripción | Reglas principales |
|---|---|---|
| CU-01 | Registrar pedido | RN-01, RN-14 |
| CU-02 | Aplicar promoción | RN-04, RN-05 |
| CU-03 | Cancelar pedido | RN-02, RN-03, RN-10 |
| CU-04 | Gestionar producto agotado | RN-06, RN-12 |
| CU-05 | Asignar repartidor y registrar entrega | RN-11 |

Además se trabaja con el **paquete de datos del PIA** (`data/paquete_pia/`): 60 operaciones importadas a la base de
datos, 120 casos de prueba evaluados con Specifications y 20 transiciones de estado ejecutadas con la máquina de estados.

Quedan **fuera** del sistema (documentados en la sección 7 de `docs/architecture/matriz-trazabilidad.md`): alertas de
existencia mínima, tiempo meta y pedidos retrasados, ajuste manual de inventario, configuración de promociones por el
Gerente y reportes.

## Decisiones principales

- **Patrón de lógica de negocio:** Domain Model como patrón principal; Transaction Script solo para marcar un
  producto agotado; Table Module descartado en los 5 casos (ADR-01).
- **Persistencia:** interfaces de Repository en el dominio, implementaciones en infraestructura y una Unit of Work
  por solicitud (ADR-02).
- **CQRS básico:** Commands y Queries con handlers, DTO de lectura y una sola base de datos (ADR-03).
- **Specification:** condiciones de negocio combinables con AND, OR y NOT (ADR-04).
- **Máquina de estados:** transiciones válidas del pedido definidas en una sola tabla (ADR-05).
- **Persistencia relacional:** SQLAlchemy con PostgreSQL; SQLite solo para desarrollo y pruebas (ADR-06).
- **API REST:** FastAPI con OpenAPI, permisos por rol y errores de negocio traducidos a códigos HTTP (ADR-07).
- **Revisión SOLID:** 7 hallazgos y 3 correcciones aplicadas.

## Cómo revisar este repositorio

| Orden | Qué revisar | Dónde |
|---|---|---|
| 1 | BRD, user stories, glosario y BPMN (U2) | `docs/BRD.md`, `docs/BRD/`, `docs/analisis/` |
| 2 | BPMN complementario y conciliación con el paquete del PIA | `docs/analisis/bpmn-complemento.md`, `docs/analisis/conciliacion-u2-paquete.md` |
| 3 | Decisiones de arquitectura (ADR-01 a ADR-07) | `docs/architecture/adr/` |
| 4 | Diagramas de clases (fuente PlantUML y PNG): general, dominio, Specification/estados/eventos, aplicación, API/consultas e infraestructura | `docs/architecture/diagramas/clases*.puml`, `docs/architecture/diagramas/clases*.png` |
| 5 | Diagramas de secuencia y de estados | `docs/architecture/diagramas/secuencia-*`, `docs/architecture/diagramas/estados-pedido.*` |
| 6 | Diagrama de dominio (drawio) | `docs/architecture/diagramas/Dominio*` |
| 7 | **Matriz de trazabilidad** BRD → regla → historia → caso de uso → componente → prueba | `docs/architecture/matriz-trazabilidad.md` |
| 8 | Código fuente | `src/sazon_urbano/` (`domain`, `application`, `infrastructure`, `api`) |
| 9 | Pruebas | `tests/unit`, `tests/integration` |
| 10 | Evidencias de ejecución (120 casos, 20 transiciones, cobertura) | `evidencias/` |
| 11 | CI/CD | `.github/workflows/ci.yml` |
| 12 | Docker | `Dockerfile`, `docker-compose.yml` |
| 13 | Bitácora de uso de IA | `docs/architecture/u3/Bitácora de IA.pdf` |

## Instalación

Requisitos: Python 3.11 o superior (o Docker).

```
git clone https://github.com/ecalo98/PIA_equipo3_sazon-urbano.git
cd PIA_equipo3_sazon-urbano
python -m venv .venv
.venv\Scripts\activate                    # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
copy .env.example .env                    # Linux/macOS: cp .env.example .env  (ajustar valores; .env no se sube)
```

## Ejecución con Docker

`docker-compose.yml` define 3 servicios: **db** (PostgreSQL 16), **app** (API FastAPI) y **tests** (pytest con cobertura).
La configuración sale de `.env` (12-Factor App); no hay secretos en el código.

```
copy .env.example .env          # Linux/macOS: cp .env.example .env   (y cambiar DB_PASSWORD)
docker compose up --build       # db + app  ->  Swagger UI: http://localhost:8000/docs
docker compose run --rm tests   # pruebas + cobertura contra PostgreSQL (corren también las 10 omitidas)
docker compose down -v          # apagar y borrar datos
```

Al arrancar, la app crea las tablas y siembra: catálogo, promoción de martes, repartidores y los **60 pedidos del
dataset del PIA** (`data/paquete_pia/`, importados a PostgreSQL con claves foráneas a `actores` y `platillos`).
Para no sembrar, `SEMBRAR_DATOS=0`. La base de pruebas (`<DB_NAME>_test`) se crea sola la primera vez que se crea el volumen.

## Despliegue

Plataforma: **Render** (el mismo `Dockerfile` también sirve en Railway o Fly.io).

1. Crear en Render una base de datos **PostgreSQL** (plan gratuito) y copiar su **Internal Database URL**.
2. Crear un **Web Service** desde el repositorio de GitHub: lenguaje **Docker**, rama `main`, misma región que la base,
   plan gratuito (el destino por defecto del `Dockerfile` es `app`).
3. Definir las variables de entorno `DATABASE_URL` (la URL de la base; se acepta `postgres://` o `postgresql://` y el
   código la convierte a `postgresql+psycopg://`) y `APP_ENV=production`. Render inyecta `PORT`, que el contenedor ya usa.
4. En *Advanced*, usar `/salud` como **Health Check Path**.
5. Render redespliega solo con cada `git push` a `main`. Verificar `https://<servicio>.onrender.com/docs`.
6. (CD opcional) Guardar el hook de despliegue como secreto `DEPLOY_HOOK_URL` en GitHub para dispararlo desde `.github/workflows/ci.yml`.

El plan gratuito suspende el servicio tras un rato sin uso; la primera visita puede tardar cerca de un minuto en responder.

| | URL |
|---|---|
| Repositorio | https://github.com/ecalo98/PIA_equipo3_sazon-urbano |
| Despliegue (Swagger UI) | https://pia-equipo3-sazon-urbano.onrender.com/docs |

## Demo

Con la API en marcha (en Render o en `http://localhost:8000/docs`), flujo sugerido para la defensa. Los endpoints que
cambian datos llevan los encabezados `X-Usuario-Id` y `X-Rol` (ver `docs/api/README.md`):

1. `GET /openapi.json` y `/docs` para mostrar el contrato.
2. Registrar un pedido a domicilio menor a $150 → **422** (RN-01); uno válido → **201**.
3. Aplicar la promoción de martes y una segunda promoción → **409** (RN-04).
4. Cancelar un pedido en preparación como mesero → **409**; como encargado → permitido (RN-03).
5. Asignar un repartidor, registrar la salida y confirmar la entrega; confirmar sin registrar la salida → **409** (RN-11).
6. Mostrar en PostgreSQL los 60 pedidos importados (con Docker local; usa los valores de `DB_USER` y `DB_NAME` de tu `.env`):
   `docker compose exec db psql -U sazon -d sazon_urbano -c "SELECT count(*) FROM operaciones_pia;"`

## Cómo ejecutar las pruebas

Requisitos: Python 3.11 o superior y `pip install -r requirements-dev.txt`.

```
pytest --cov            # pruebas unitarias e integración + cobertura (mínimo 80 %, configurado en pyproject.toml)
```

Resultado actual: **155 pruebas pasan** y 10 se omiten sin PostgreSQL (corren en el CI y con `docker compose run --rm tests`),
con una cobertura del **99.69 %**. Las pruebas están en `tests/unit` (reglas puras: Specifications, máquina de estados,
arquitectura, casos borde) y `tests/integration` (casos de uso, persistencia SQL, API y paquete del PIA). También corren
con `python -m unittest discover`.

Para correr también las pruebas de persistencia contra PostgreSQL:

```
TEST_DATABASE_URL=postgresql+psycopg://USUARIO:CLAVE@localhost:5432/sazon_test pytest --cov
```

(PowerShell: `$env:TEST_DATABASE_URL="postgresql+psycopg://USUARIO:CLAVE@localhost:5432/sazon_test"; pytest --cov`)

Ejecutar la API (Swagger UI en http://localhost:8000/docs):

```
PYTHONPATH=src uvicorn --factory sazon_urbano.api.main:crear_app --port 8000
```

(PowerShell: `$env:PYTHONPATH="src"; uvicorn --factory sazon_urbano.api.main:crear_app --port 8000`)

Sin variables de base de datos usa un SQLite local; con `DB_HOST` o `DATABASE_URL` usa PostgreSQL (ver `.env.example`).
El contrato de la API está en `docs/api/README.md` y `docs/api/openapi.json`.

Scripts de evidencia y verificación (desde la raíz del repositorio):

```
python scripts/ejecutar_casos_prueba.py      # 120 casos con Specifications -> evidencias/resultados_casos_prueba.csv
python scripts/ejecutar_transiciones.py      # 20 transiciones con la máquina de estados -> evidencias/resultados_transiciones.csv
python scripts/generar_diagrama_estados.py   # regenera el diagrama de estados desde el código
python scripts/exportar_openapi.py           # regenera docs/api/openapi.json
python scripts/prueba_humo_api.py            # arranca la API real y recorre los 5 casos de uso por HTTP (20 pasos)
```

Las pruebas cubren los 5 casos de uso y verifican por código la regla de dependencias
(el dominio no importa aplicación ni infraestructura, ni librerías de SQL).

## Estructura

```
docs/BRD.md          BRD de la Unidad 2 en Markdown (el PDF original está en docs/BRD/)
docs/analisis/       User stories, glosario y BPMN de la U2 (sin modificar) + BPMN complementario y conciliación con el paquete PIA
docs/architecture/   ADR, diagramas, matriz de trazabilidad y entregables de la U3
docs/api/            Contrato OpenAPI y códigos HTTP
data/paquete_pia/    CSV del paquete de datos del PIA (sin modificar)
evidencias/          Resultados de los 120 casos, las 20 transiciones y la cobertura
scripts/             Ejecución de casos y transiciones, generación de diagramas y OpenAPI, prueba de humo de la API
src/sazon_urbano/    domain · application · infrastructure · api
fixtures/            Menú propio de Sazón Urbano y operaciones_extra.csv (canal, responsable y casos de RN-01 y US-02)
tests/               unit/ (reglas puras y arquitectura) · integration/ (casos de uso, persistencia, API, paquete PIA)
.github/workflows/   CI/CD (pruebas con PostgreSQL, cobertura mínima 80 %, construcción de la imagen)
.env.example         Variables de entorno de ejemplo (sin secretos)
Dockerfile           Imagen con destinos app y tests
docker-compose.yml   db (PostgreSQL) + app + tests
docker/              Script que crea la base de pruebas
```

## Supuestos y hallazgos

Los hallazgos sobre la Unidad 2 y los supuestos pendientes de validación (por ejemplo, Mesero y Caja como roles
separados) están registrados en la matriz de trazabilidad (`docs/architecture/matriz-trazabilidad.md`) y en la
conciliación con el paquete del PIA (`docs/analisis/conciliacion-u2-paquete.md`).

## Uso de IA

Se usó Claude (Anthropic) como apoyo. Cada propuesta fue revisada contra el BRD y la guía de la actividad.
Los prompts, errores detectados y decisiones del equipo están en `docs/architecture/u3/Bitácora de IA.pdf`.
