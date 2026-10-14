import asyncio
import json
from pathlib import Path
from uuid import uuid4

import typer

from app.core.db import SessionLocal, engine
from app.core.logging import configure_logging
from app.modules.catalog.repository import create_run
from app.modules.scraper.client import SiiaaClient
from app.modules.scraper.jobs import execute_run
from app.modules.scraper.service import IncompleteScrape, ScraperService, require_complete
from app.modules.scraper.tracing import trace_scope

app = typer.Typer(help="Scraper del catálogo SIIAA.")


@app.callback()
def cli() -> None:
    """Comandos del scraper SIIAA."""


@app.command()
def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="No escribe en la base de datos."),
    out: Path | None = typer.Option(None, "--out", help="Ruta del JSON cuando se usa --dry-run."),
    limit_careers: int | None = typer.Option(
        None, "--limit-careers", min=1, help="Consulta solo las primeras N carreras (solo --dry-run)."
    ),
) -> None:
    """Descarga el catálogo de programas educativos del SIIAA."""
    if limit_careers is not None and not dry_run:
        raise typer.BadParameter("--limit-careers requires --dry-run")
    if out is not None and not dry_run:
        raise typer.BadParameter("--out requires --dry-run")
    configure_logging()
    try:
        asyncio.run(_run(dry_run=dry_run, out=out, limit_careers=limit_careers))
    except IncompleteScrape as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


async def _run(dry_run: bool, out: Path | None, limit_careers: int | None) -> None:
    try:
        if dry_run:
            with trace_scope(f"dry-run-{uuid4().hex}"):
                return await _dry_run(out, limit_careers)
        async with SessionLocal() as session:
            scrape_run = await create_run(session)
            run_id = scrape_run.id or 0
        stats = await execute_run(run_id)
        typer.echo(f"Catálogo guardado en el run {run_id} ({stats})")
    finally:
        await engine.dispose()


async def _dry_run(out: Path | None, limit_careers: int | None) -> None:
    async with SiiaaClient() as client:
        catalog, stats = await ScraperService(client).collect(limit_careers=limit_careers)
    destination = out or Path("data/siiaa-offers.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = catalog.model_dump(by_alias=True, mode="json")
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"JSON escrito en {destination} ({stats})")
    require_complete(stats)
    return


def main() -> None:
    app()


if __name__ == "__main__":
    main()
