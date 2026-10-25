# pp-backend

API de prácticas profesionales y servicio social. La consume [pp-app](../pp-app). El catálogo sale del SIIAA y se guarda en PostgreSQL.

La arquitectura, las librerías y la política de migraciones están en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker, para PostgreSQL

## Arranque local

```bash
cp .env.example .env
docker compose up -d db
uv run alembic upgrade head
uv run fastapi dev
```

La API queda en http://localhost:8000 y la documentación en http://localhost:8000/docs.

## Scraper

```bash
uv run python -m app.modules.scraper.cli run --dry-run --out data/siiaa-offers.json
uv run python -m app.modules.scraper.cli run
# Carga inicial de hasta 100 ofertas únicas:
uv run python -m app.modules.scraper.cli run --limit-offers 100
```

`--limit-careers N` consulta solo las primeras N carreras y requiere `--dry-run`; `N` debe ser positivo. `--out` también requiere `--dry-run`. Sin límite recorre todos los programas educativos.

`--limit-offers N` acepta un entero positivo y funciona con persistencia o `--dry-run`. Lee los listados, selecciona las primeras N ofertas únicas en orden de origen y descarga solo sus detalles, conservando sus asociaciones con carreras. Si hay menos de N, guarda las disponibles. Los runs limitados actualizan la muestra sin desactivar ofertas ni áreas existentes fuera de ella; una base con datos previos puede tener más de N ofertas. El límite solicitado se registra como `limitOffers` en las estadísticas. El endpoint HTTP sigue ejecutando el catálogo completo.

Si falla un listado o un detalle después de los reintentos, el run queda `failed` y conserva el catálogo anterior. Un dry run puede exportar un JSON parcial para diagnóstico: imprime estadísticas y termina con código 1 si hubo errores.

También se puede disparar con `POST /api/v1/scrape/runs` y el header `X-Admin-Key`. Consulta su estado con `GET /api/v1/scrape/runs/{id}` usando la misma llave.

La API usa un solo worker y una sola instancia: el lock del scraper vive en memoria. Ejecuta la CLI de persistencia cuando no haya un scrape de la API en curso. Al apagar la API se cancela la tarea y se registra el fallo antes de cerrar el engine.

Compose lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `COMPOSE_DATABASE_URL` de `.env`; si falta alguna variable o está vacía, falla con un mensaje indicando cuál configurar. `COMPOSE_DATABASE_URL` usa `db` como host y se entrega a la API como `DATABASE_URL`. Fuera de Docker se usa `DATABASE_URL` con `localhost`.

Configura las mismas credenciales y base en ambas URLs; codifica los caracteres especiales del usuario o contraseña para usarlos en una URL. Cambiar `.env` no modifica usuarios ni contraseñas en un volumen PostgreSQL ya inicializado.

## Tipos TypeScript para el frontend

Los modelos Pydantic definen el contrato y FastAPI lo publica en `http://localhost:8000/openapi.json`. No es necesario ejecutar el scraper para generar tipos. Con la API en marcha, ejecuta en el frontend:

```bash
npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.d.ts
```

```ts
import type { components } from "./api-types";

type Offer = components["schemas"]["Offer"];
type Catalog = components["schemas"]["Catalog"];
```

Regenera el archivo cuando cambie el contrato de la API.

## Tests

```bash
uv run pytest
uv run ruff check .
uv run mypy app
```

Los tests normales usan fixtures locales y no necesitan pp-app, PostgreSQL ni red. Los tests de integración requieren una base **desechable**, cuyo nombre empiece con `pp_backend_test`; aplican migraciones y eliminan las tablas al terminar.

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" pp_backend_test'
# Ajusta las credenciales para que coincidan con tu .env.
TEST_DATABASE_URL=postgresql+asyncpg://pp:change-me@localhost:5432/pp_backend_test uv run pytest tests/test_postgres_integration.py -q
```

Estos tests comprueban migraciones, idempotencia, desactivación, rollback y endpoints con datos reales en PostgreSQL. Sin `TEST_DATABASE_URL` se omiten explícitamente.
