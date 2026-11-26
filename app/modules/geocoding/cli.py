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
def run() -> None:
    """Geocodifica las direcciones pendientes (respeta 1 solicitud por segundo)."""
    configure_logging()
    asyncio.run(_run())


async def _run() -> None:
    try:
        async with NominatimClient() as client, SessionLocal() as session:
            stats = await run_geocoding(session, client)
        typer.echo(
            f"created={stats.created} geocoded={stats.geocoded} "
            f"not_found={stats.not_found} failed={stats.failed}"
        )
    finally:
        await engine.dispose()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
