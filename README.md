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
# Carga inicial de hasta 100 ofertas únicas:
uv run python -m app.modules.scraper.cli run --limit-offers 100
```

`--limit-careers N` consulta solo las primeras N carreras y requiere `--dry-run`; `N` debe ser positivo. `--out` también requiere `--dry-run`. Sin límite recorre todos los programas educativos.

`--limit-offers N` acepta un entero positivo y funciona con persistencia o `--dry-run`. Lee los listados, selecciona las primeras N ofertas únicas en orden de origen y descarga solo sus detalles, conservando sus asociaciones con carreras. Si hay menos de N, guarda las disponibles. Los runs limitados actualizan la muestra sin desactivar ofertas ni áreas existentes fuera de ella; una base con datos previos puede tener más de N ofertas. El límite solicitado se registra como `limitOffers` en las estadísticas. El endpoint HTTP sigue ejecutando el catálogo completo.

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

## Ofertas guardadas

`GET /api/v1/saved-offers` requiere una sesión válida en la cookie `pp_session` y
devuelve solo los guardados del usuario, del más reciente al más antiguo. Incluye
título, folio, remuneración, disponibilidad, carrera para el enlace al detalle y
datos de contacto y ubicación. Las ofertas inactivas permanecen en la lista con
`isActive: false`; `areaSlug` es `null` si no tienen carreras activas asociadas.
Si hay varias carreras activas, se elige la primera por slug. Una lista vacía es `[]`.

`POST /api/v1/saved-offers/{offer_uuid}` guarda una oferta existente para el usuario
de la sesión, sin body. Requiere además `Origin` igual a `FRONTEND_URL` y
`X-Requested-With: XMLHttpRequest`. Responde `201` al crear y `200` si ya estaba
guardada, conservando su fecha original.

`DELETE /api/v1/saved-offers/{offer_uuid}` elimina únicamente el guardado del usuario
de la sesión, con la misma autenticación y protección de escritura del POST.
Responde `204` sin contenido aunque ya no estuviera guardada. Permite quitar ofertas
inactivas y no elimina la oferta del catálogo. Todas estas rutas usan `Cache-Control: no-store`.

El frontend consulta el listado desde el servidor reenviando la cookie y guarda
mediante Server Actions que invalidan `/guardados` y el detalle de ofertas después
de guardar o quitar. Los tipos deben regenerarse
cuando cambie el contrato, siguiendo el procedimiento siguiente.

## Tipos TypeScript para el frontend

Los modelos Pydantic y los endpoints registrados en FastAPI definen el contrato OpenAPI.
Cuando cambies campos de los modelos, parámetros, respuestas o agregues un endpoint,
regenera los tipos de **PPracticaSS**. No es necesario ejecutar el scraper.

Desde la raíz de `pp-backend`, reconstruye y levanta la API para publicar los cambios:

```bash
docker compose up -d --build api
```

Después, desde la misma raíz, genera los tipos en el frontend existente:

```bash
cd ../PPracticaSS
npx --yes openapi-typescript http://localhost:8001/openapi.json -o lib/api-types.d.ts
pnpm exec tsc --noEmit --incremental false
```

Compose expone la API en el puerto `8001`. Si ejecutas FastAPI localmente en el
puerto `8000`, cambia la URL a `http://localhost:8000/openapi.json`.
Los endpoints nuevos deben estar registrados en la aplicación para aparecer en
OpenAPI. El archivo generado incluye tanto los esquemas (`components`) como las
rutas y operaciones (`paths`); no crea un cliente HTTP ni actualiza los componentes
del frontend automáticamente.

Consume los tipos directamente o crea alias en un archivo como `lib/types/catalog.ts`:

```ts
import type { components } from "@/lib/api-types";

export type Area = components["schemas"]["Area"];
export type Offer = components["schemas"]["Offer"];
export type Catalog = components["schemas"]["Catalog"];
```

No edites `lib/api-types.d.ts` manualmente: cada generación reemplaza su contenido.
Revisa el diff generado y adapta los consumidores si cambió el contrato.

## Exportar e importar una instancia

El export incluye el esquema completo, catálogo, relaciones, historial de scraping,
secuencias y versión de Alembic. Requiere `pg_dump` de la misma versión mayor
que el servidor PostgreSQL o una posterior. Lee `DATABASE_URL` de `.env`.

```bash
uv run python -m scripts.export_database data/pp-backup.dump
pg_restore --list data/pp-backup.dump
```

El archivo contiene datos de contacto: transfiérelo por un medio privado.
Para restaurarlo, crea una base **vacía** en la otra instancia y ejecuta
(ajusta host, usuario y base; PostgreSQL solicitará la contraseña):

```bash
pg_restore --host localhost --username pp --dbname pp_new \
  --no-owner --no-privileges --single-transaction --exit-on-error data/pp-backup.dump
```

Usa una versión de PostgreSQL igual o posterior a la de origen y herramientas
cliente compatibles con el archivo. La restauración carga todos los registros
con sus identificadores originales; no combina datos con una base existente.
Después configura `DATABASE_URL` en la instancia destino y ejecuta
`uv run alembic upgrade head` antes de iniciar la API. Evita ejecutar el scraper
en el destino durante la restauración.

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

## Recomendaciones reales con Gemini

La pantalla `/analisis-cv` permite elegir una carrera, seleccionar un CV ficticio en PDF
y obtener un resumen y hasta tres ofertas activas del catálogo, con una explicación de afinidad.
El endpoint `POST /api/v1/recommendations/analyze` recibe `cv` y `areaSlug` como multipart,
requiere sesión y valida el origen y `X-Requested-With: XMLHttpRequest`.

Configura únicamente en el `.env` del backend:

```dotenv
GEMINI_API_KEY=TU_CLAVE_LOCAL
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=45
```

La clave se obtiene en https://aistudio.google.com/apikey. No debe incorporarse al frontend,
ni a variables `NEXT_PUBLIC_*`, ni a archivos versionados. La autenticación de usuarios con
Google y la clave de Gemini son configuraciones distintas.

El modelo es configurable. La demostración utiliza Flash-Lite; si Google reporta saturación,
cuota agotada o timeout, la pantalla muestra el error y permite volver a intentar. No hay
reintentos automáticos ni resultados de ejemplo sustituyendo una llamada fallida.

### Probar desde la pantalla

1. Instala las dependencias con `uv sync` o reconstruye la API con
   `docker compose up -d --build --no-deps api`. No requiere migraciones nuevas.
2. Inicia sesión en el frontend y abre **Ofertas sugeridas**.
3. Selecciona **Ing. Ingeniería Tecnologías de la Información**, confirma que usas un CV
   ficticio y elige uno de los archivos de `output/pdf/`:
   `cv-demo-desarrollo-web.pdf` o `cv-demo-analisis-datos.pdf`.
4. Pulsa **Realizar análisis** y comprueba el resumen y las explicaciones. Ambos CV tienen
   perfiles diferentes; el orden y el número de recomendaciones pueden variar entre llamadas.
5. Abre **Ver oferta** para verificar los datos reales. **Guardar** reutiliza el sistema de
   guardados existente; **Aplicar** abre el correo y **Ver ubicación** busca la dirección en Google Maps.

La API valida formato, estructura, contraseña y tamaño máximo de 10 MB del PDF. Solo envía
a Gemini el documento y los datos profesionales de las ofertas de la carrera, sin datos de
contacto de los supervisores. El CV y las recomendaciones no se almacenan permanentemente
por nuestra aplicación; el archivo de subida se cierra al terminar. La vista previa y los
resultados se eliminan de la pantalla al cambiar el CV o la carrera.

En el nivel gratuito Google puede utilizar el contenido para mejorar sus productos:
https://ai.google.dev/gemini-api/docs/pricing. Para esta demostración utiliza exclusivamente
los CV ficticios. El resumen indica información ausente como **No especificado** y puede
haber menos de tres recomendaciones o ninguna. Una sugerencia no garantiza elegibilidad.
Los identificadores se verifican contra el catálogo; título, folio, apoyos y enlaces proceden
de la base de datos, no de la generación del modelo.

```bash
uv run pytest tests/test_recommendations.py -q
```

Estas pruebas usan un proveedor simulado y no consumen cuota de Google. Cubren autenticación,
origen, PDF inválido/protegido/grande, carrera sin ofertas, identificadores ajenos o repetidos,
respuesta inválida, cuota agotada, timeout y cierre del cliente de Gemini.
