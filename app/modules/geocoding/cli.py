import asyncio

import typer

from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.modules.geocoding.client import NominatimClient
from app.modules.geocoding.service import run_geocoding

app = typer.Typer(help="Geocodificación de direcciones de las ofertas (Nominatim).")


@app.callback()
def cli() -> None:
    """Comandos de geocodificación."""


@app.command()
def run(
    retry_not_found: bool = typer.Option(
        False, "--retry-not-found", help="Reintenta las direcciones marcadas como not_found."
    ),
) -> None:
    """Geocodifica las direcciones pendientes (respeta 1 solicitud por segundo)."""
    configure_logging()
    asyncio.run(_run(retry_not_found))


async def _run(retry_not_found: bool) -> None:
    try:
        async with NominatimClient() as client, SessionLocal() as session:
            stats = await run_geocoding(session, client, retry_not_found=retry_not_found)
        typer.echo(
            f"created={stats.created} geocoded={stats.geocoded} approximate={stats.approximate} "
            f"not_found={stats.not_found} failed={stats.failed}"
        )
    finally:
        await engine.dispose()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
