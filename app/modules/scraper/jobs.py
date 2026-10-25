import asyncio
import logging

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import SessionLocal
from app.modules.catalog.repository import create_run, finish_run, save_catalog
from app.modules.catalog.schemas import ScrapeRunRead
from app.modules.scraper.client import SiiaaClient
from app.modules.scraper.models import ScrapeRun
from app.modules.scraper.service import ScraperService, require_complete

logger = logging.getLogger(__name__)


class ScrapeAlreadyRunning(Exception):
    pass


async def execute_run(run_id: int, *, limit_offers: int | None = None) -> dict:
    """Publish atomically; limited runs preserve records outside their sample."""
    stats: dict = {"limitOffers": limit_offers} if limit_offers is not None else {}
    try:
        async with SiiaaClient() as client:
            service = ScraperService(client)
            if limit_offers is None:
                catalog, stats = await service.collect()
            else:
                catalog, collected_stats = await service.collect(limit_offers=limit_offers)
                stats.update(collected_stats)
        require_complete(stats)
        async with SessionLocal() as session:
            if limit_offers is None:
                await save_catalog(session, catalog, run_id)
            else:
                await save_catalog(session, catalog, run_id, deactivate_missing=False)
            await finish_run(session, run_id, "succeeded", stats, None)
            await session.commit()
    except (Exception, asyncio.CancelledError) as exc:
        error = "Scrape cancelled during shutdown" if isinstance(exc, asyncio.CancelledError) else str(exc)
        async with SessionLocal() as session:
            await finish_run(session, run_id, "failed", stats, error)
            await session.commit()
        raise
    return stats


class ScrapeJobs:
    def __init__(self) -> None:
        self._running = False
        self._closing = False
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()

    async def start(self, session: AsyncSession) -> ScrapeRun:
        async with self._lock:
            if self._running or self._closing:
                raise ScrapeAlreadyRunning()
            run = await create_run(session)
            self._running = True
            task = asyncio.create_task(self._execute(run.id or 0))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return run

    async def _execute(self, run_id: int) -> None:
        try:
            await execute_run(run_id)
        except Exception:
            logger.exception("scrape run %s failed", run_id)
        finally:
            self._running = False

    async def close(self) -> None:
        async with self._lock:
            self._closing = True
        tasks = list(self._tasks)
        if tasks:
            # Yield first so newly admitted tasks enter their cancellation handler.
            await asyncio.sleep(0)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def run_to_read(run: ScrapeRun) -> ScrapeRunRead:
    started = run.started_at.isoformat().replace("+00:00", "Z")
    finished = None
    if run.finished_at is not None:
        finished = run.finished_at.isoformat().replace("+00:00", "Z")
    return ScrapeRunRead(
        id=run.id or 0,
        status=run.status,
        started_at=started,
        finished_at=finished,
        stats=run.stats or {},
        error=run.error,
    )
