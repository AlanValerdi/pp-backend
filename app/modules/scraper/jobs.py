import asyncio
import logging
from time import monotonic

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import SessionLocal
from app.modules.catalog.repository import create_run, finish_run, save_catalog
from app.modules.catalog.schemas import ScrapeRunRead
from app.modules.scraper.client import SiiaaClient
from app.modules.scraper.models import ScrapeRun
from app.modules.scraper.preview import PreviewRead, ScrapePreview
from app.modules.scraper.service import ScraperService, require_complete
from app.modules.scraper.tracing import event, trace_scope

logger = logging.getLogger(__name__)


class ScrapeAlreadyRunning(Exception):
    pass


async def execute_run(run_id: int) -> dict:
    with trace_scope(f"run-{run_id}"):
        return await _execute_run(run_id)


async def _execute_run(run_id: int) -> dict:
    """Publish a complete snapshot atomically, recording failures in a fresh transaction."""
    stats: dict = {}
    started = monotonic()
    stage = "collection"
    event(logger, "run_started", run_id=run_id)
    try:
        async with SiiaaClient() as client:
            catalog, stats = await ScraperService(client).collect()
        stage = "validation"
        event(logger, "validation_started")
        require_complete(stats)
        event(logger, "validation_completed", **stats)
        stage = "persistence"
        event(logger, "persistence_started")
        async with SessionLocal() as session:
            await save_catalog(session, catalog, run_id)
            await finish_run(session, run_id, "succeeded", stats, None)
            await session.commit()
        event(
            logger,
            "catalog_committed",
            sections=len(catalog.sections),
            faculties=len(catalog.faculties),
            areas=len(catalog.areas),
            offers=len(catalog.offers),
            relationships=sum(len(offer.area_details) for offer in catalog.offers),
        )
        event(logger, "run_succeeded", duration_seconds=round(monotonic() - started, 3))
    except (Exception, asyncio.CancelledError) as exc:
        error = "Scrape cancelled during shutdown" if isinstance(exc, asyncio.CancelledError) else str(exc)
        event(
            logger,
            "run_cancelled" if isinstance(exc, asyncio.CancelledError) else "run_failed",
            logging.ERROR,
            stage=stage,
            error_type=type(exc).__name__,
            duration_seconds=round(monotonic() - started, 3),
        )
        async with SessionLocal() as session:
            await finish_run(session, run_id, "failed", stats, error)
            await session.commit()
        event(logger, "failure_recorded", run_id=run_id)
        raise
    return stats


class ScrapeJobs:
    def __init__(self) -> None:
        self._running = False
        self._closing = False
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[None]] = set()
        self._preview_tasks: set[asyncio.Task[PreviewRead]] = set()

    async def preview(self) -> PreviewRead:
        async with self._lock:
            if self._running or self._closing:
                raise ScrapeAlreadyRunning()
            self._running = True
            task = asyncio.create_task(ScrapePreview().run())
            self._preview_tasks.add(task)
        try:
            return await task
        finally:
            self._preview_tasks.discard(task)
            self._running = False

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
            # execute_run records the failure with its trace and stage.
            pass
        finally:
            self._running = False

    async def close(self) -> None:
        async with self._lock:
            self._closing = True
        tasks = [*self._tasks, *self._preview_tasks]
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
