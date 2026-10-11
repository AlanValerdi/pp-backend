import asyncio
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from typer.testing import CliRunner

from app.modules.catalog.schemas import Catalog
from app.modules.scraper import cli, jobs
from app.modules.scraper.jobs import ScrapeAlreadyRunning, ScrapeJobs
from app.modules.scraper.models import ScrapeRun
from app.modules.scraper.service import IncompleteScrape, ScraperService

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def catalog() -> Catalog:
    return Catalog.model_validate_json((FIXTURES / "catalog.json").read_text())


@pytest.fixture
def execution(monkeypatch, catalog):
    session = AsyncMock()

    @asynccontextmanager
    async def sessions():
        yield session

    monkeypatch.setattr(jobs, "SessionLocal", sessions)
    monkeypatch.setattr(jobs, "SiiaaClient", lambda: sessions())
    collect = AsyncMock(return_value=(catalog, {"listingErrors": 0, "detailErrors": 0}))
    monkeypatch.setattr(jobs.ScraperService, "collect", collect)
    save = AsyncMock()
    finish = AsyncMock()
    monkeypatch.setattr(jobs, "save_catalog", save)
    monkeypatch.setattr(jobs, "finish_run", finish)
    return session, collect, save, finish


@pytest.mark.parametrize("error_key", ["listingErrors", "detailErrors"])
async def test_incomplete_run_never_publishes(execution, catalog, error_key):
    session, collect, save, finish = execution
    stats = {"listingErrors": 0, "detailErrors": 0, error_key: 1}
    collect.return_value = catalog, stats
    with pytest.raises(IncompleteScrape):
        await jobs.execute_run(7)
    save.assert_not_awaited()
    assert finish.await_args.args[1:4] == (7, "failed", stats)
    session.commit.assert_awaited_once()


async def test_success_commits_catalog_and_run_together(execution):
    session, _, save, finish = execution
    await jobs.execute_run(7)
    save.assert_awaited_once()
    assert finish.await_args.args[2] == "succeeded"
    session.commit.assert_awaited_once()


async def test_collection_failure_is_recorded(execution):
    _, collect, save, finish = execution
    collect.side_effect = ValueError("invalid careers page")
    with pytest.raises(ValueError):
        await jobs.execute_run(7)
    save.assert_not_awaited()
    assert finish.await_args.args[2:] == ("failed", {}, "invalid careers page")


async def test_persistence_failure_is_recorded(execution):
    _, _, save, finish = execution
    save.side_effect = RuntimeError("write failed")
    with pytest.raises(RuntimeError):
        await jobs.execute_run(7)
    assert finish.await_args.args[2] == "failed"
    assert finish.await_args.args[-1] == "write failed"


async def test_concurrent_start_and_shutdown(monkeypatch, execution):
    _, collect, _, finish = execution
    began = asyncio.Event()

    async def blocked_collect(*args, **kwargs):
        began.set()
        await asyncio.Event().wait()

    collect.side_effect = blocked_collect
    create = AsyncMock(return_value=ScrapeRun(id=7, started_at=datetime.now(UTC), stats={}))
    monkeypatch.setattr(jobs, "create_run", create)
    manager = ScrapeJobs()
    results = await asyncio.gather(
        manager.start(AsyncMock()), manager.start(AsyncMock()), return_exceptions=True
    )
    assert sum(isinstance(item, ScrapeAlreadyRunning) for item in results) == 1
    create.assert_awaited_once()
    await began.wait()
    await manager.close()
    assert not manager._tasks
    assert not manager._running
    assert finish.await_args.args[2] == "failed"
    assert "shutdown" in finish.await_args.args[-1]
    with pytest.raises(ScrapeAlreadyRunning):
        await manager.start(AsyncMock())


async def test_start_failure_allows_retry(monkeypatch):
    create = AsyncMock(side_effect=RuntimeError("database unavailable"))
    monkeypatch.setattr(jobs, "create_run", create)
    manager = ScrapeJobs()
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await manager.start(AsyncMock())
    assert create.await_count == 2
    assert not manager._running


@pytest.mark.parametrize(
    "args", [["--limit-careers", "1"], ["--limit-careers", "0", "--dry-run"], ["--out", "unused.json"]]
)
def test_cli_rejects_unsafe_options(args, monkeypatch):
    run = AsyncMock()
    monkeypatch.setattr(cli, "_run", run)
    result = CliRunner().invoke(cli.app, ["run", *args])
    assert result.exit_code == 2
    run.assert_not_awaited()


def test_cli_run_subcommand(monkeypatch):
    run = AsyncMock()
    monkeypatch.setattr(cli, "_run", run)
    result = CliRunner().invoke(cli.app, ["run", "--dry-run", "--limit-careers", "1"])
    assert result.exit_code == 0, result.output
    run.assert_awaited_once_with(dry_run=True, out=None, limit_careers=1)


async def test_dry_run_exports_partial_without_database(monkeypatch, execution, catalog, tmp_path):
    _, collect, _, _ = execution
    monkeypatch.setattr(cli, "SiiaaClient", jobs.SiiaaClient)
    collect.return_value = catalog, {"listingErrors": 1, "detailErrors": 0}
    create = AsyncMock()
    monkeypatch.setattr(cli, "create_run", create)
    destination = tmp_path / "partial.json"
    with pytest.raises(IncompleteScrape):
        await cli._run(True, destination, 1)
    assert json.loads(destination.read_text())["offers"]
    create.assert_not_awaited()


async def test_cli_creates_run_before_collection(monkeypatch):
    @asynccontextmanager
    async def sessions():
        yield AsyncMock()

    events = []

    async def create(session):
        events.append("create")
        return ScrapeRun(id=7, started_at=datetime.now(UTC), stats={})

    async def execute(run_id):
        events.append("execute")
        assert run_id == 7
        return {}

    monkeypatch.setattr(cli, "SessionLocal", sessions)
    monkeypatch.setattr(cli, "create_run", create)
    monkeypatch.setattr(cli, "execute_run", execute)
    await cli._run(False, None, None)
    assert events == ["create", "execute"]


async def test_listing_error_is_counted():
    class Client:
        async def get_careers_html(self):
            return (FIXTURES / "careers.html").read_text()

        async def post_text(self, path, data):
            raise RuntimeError("source unavailable")

    catalog, stats = await ScraperService(Client()).collect(limit_careers=1)
    assert stats["listingErrors"] == 1
    assert not catalog.offers


async def test_shutdown_immediately_after_start(monkeypatch, execution):
    _, collect, _, finish = execution

    async def blocked_collect(*args, **kwargs):
        await asyncio.Event().wait()

    collect.side_effect = blocked_collect
    monkeypatch.setattr(jobs, "create_run", AsyncMock(return_value=ScrapeRun(id=7)))
    manager = ScrapeJobs()
    await manager.start(AsyncMock())
    await manager.close()
    assert finish.await_args.args[2] == "failed"
    assert not manager._tasks
