# pp-backend

API de prácticas profesionales y servicio social. La consume [pp-app](../pp-app). El catálogo sale del SIIAA y se guarda en PostgreSQL.

La arquitectura, las librerías y la política de migraciones están en [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requisitos

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Docker, para PostgreSQL

## Arranque

### Con Docker Compose (recomendado)

Levanta la base de datos PostgreSQL y la API en contenedores:

```bash
cp .env.example .env  # Si aún no existe .env
docker compose up -d
```

La API queda en http://localhost:8001 (mapeada al puerto 8000 del contenedor) y la documentación en http://localhost:8001/docs.

### Arranque local (sin contenedor de API)

```bash
cp .env.example .env
docker compose up -d db
uv run alembic upgrade head
uv run fastapi dev
```

La API queda en http://localhost:8000 (o agrega `--port 8001` si el 8000 está ocupado) y la documentación en http://localhost:8000/docs.

## Scraper

```bash
uv run python -m app.modules.scraper.cli run --dry-run --out data/siiaa-offers.json
uv run python -m app.modules.scraper.cli run
```

`--limit-careers N` consulta solo las primeras N carreras y requiere `--dry-run`; `N` debe ser positivo. `--out` también requiere `--dry-run`. Sin límite recorre todos los programas educativos.

Si falla un listado o un detalle después de los reintentos, el run queda `failed` y conserva el catálogo anterior. Un dry run puede exportar un JSON parcial para diagnóstico: imprime estadísticas y termina con código 1 si hubo errores.

También se puede disparar con `POST /api/v1/scrape/runs` y el header `X-Admin-Key`. Consulta su estado con `GET /api/v1/scrape/runs/{id}` usando la misma llave.

Para diagnosticar la extracción, usa `POST /api/v1/scrape/preview` con `X-Admin-Key`.
Devuelve hasta 10 muestras de detalles con sus datos normalizados, parámetros de formulario,
estado HTTP, duración y errores de cada solicitud. Las páginas que no se pueden interpretar
incluyen un extracto de hasta 500 caracteres. No crea registros ni modifica el catálogo.
Consulta además la página de carreras y hasta 10 listados para descubrir las muestras;
las solicitudes son secuenciales, separadas por al menos un segundo y sin reintentos.
El timeout por solicitud es de 15 segundos y el límite total de 120 segundos devuelve
los resultados parciales. Si hay un scrape o preview activo, responde `409`.
Un `200` del endpoint puede contener muestras fallidas: revisa `status`, `failures`
y los diagnósticos de `requests`.

Los logs del scraper incluyen `trace_id` (`run-ID`, `preview-ID` o `dry-run-ID`)
y `event` para distinguir descarga, parsing, normalización, validación y persistencia.
En `INFO`, `details_progress` muestra completados/total, parseados, fallidos,
tiempo transcurrido y tiempo restante estimado, al primer resultado, cada 50 resultados
o 10 segundos al completar una solicitud, y al último resultado.
`normalization_completed` confirma que se construyó el catálogo; solo
`catalog_committed` confirma que se guardó en PostgreSQL. Cada muestra del preview
registra `preview_sample_normalized` o `preview_sample_failed` y nunca publica un catálogo.
Con `LOG_LEVEL=DEBUG` se ven los eventos individuales por folio/área y las descargas
con estado HTTP, bytes y duración. Los logs no incluyen HTML, llaves ni datos de contacto.

La API usa un solo worker y una sola instancia: el lock del scraper vive en memoria. Ejecuta la CLI de persistencia cuando no haya un scrape de la API en curso. Al apagar la API se cancela la tarea y se registra el fallo antes de cerrar el engine.

Compose lee `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` y `COMPOSE_DATABASE_URL` de `.env`; si falta alguna variable o está vacía, falla con un mensaje indicando cuál configurar. `COMPOSE_DATABASE_URL` usa `db` como host y se entrega a la API como `DATABASE_URL`. Fuera de Docker se usa `DATABASE_URL` con `localhost`.

Configura las mismas credenciales y base en ambas URLs; codifica los caracteres especiales del usuario o contraseña para usarlos en una URL. Cambiar `.env` no modifica usuarios ni contraseñas en un volumen PostgreSQL ya inicializado.

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
