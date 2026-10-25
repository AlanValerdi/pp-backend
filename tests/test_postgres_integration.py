"""Run against a disposable DB: TEST_DATABASE_URL=.../pp_backend_test uv run pytest."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_session
from app.core.config import get_settings
from app.main import create_app
from app.modules.catalog.models import AreaRow, OfferAreaRow, OfferRow
from app.modules.catalog.repository import create_run, finish_run, get_run, load_catalog, save_catalog
from app.modules.catalog.schemas import Catalog
from app.modules.scraper import jobs

ROOT = Path(__file__).parents[1]


@pytest.fixture
async def database():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    parsed = make_url(url)
    if parsed.drivername != "postgresql+asyncpg" or not (parsed.database or "").startswith("pp_backend_test"):
        pytest.fail("Use a disposable postgresql+asyncpg database named pp_backend_test...")
    env = {**os.environ, "DATABASE_URL": url}

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    migrate("upgrade", "head")
    migrate("check")
    migrate("downgrade", "base")
    migrate("upgrade", "head")
    engine = create_async_engine(url)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield sessions
    finally:
        await engine.dispose()
        migrate("downgrade", "base")


@pytest.fixture
def catalog():
    return Catalog.model_validate_json((ROOT / "tests/fixtures/catalog.json").read_text())


async def seed(sessions, catalog):
    async with sessions() as session:
        run = await create_run(session)
        await save_catalog(session, catalog, run.id)
        await finish_run(session, run.id, "succeeded", {}, None)
        await session.commit()
        return run.id


async def test_migrations_idempotence_and_deactivation(database, catalog):
    await seed(database, catalog)
    await seed(database, catalog)
    async with database() as session:
        assert len((await session.exec(select(OfferRow))).all()) == 1
        assert len((await session.exec(select(AreaRow))).all()) == 1
        assert len((await session.exec(select(OfferAreaRow))).all()) == 1
        loaded = await load_catalog(session)
        assert loaded.areas[0].offer_ids == [loaded.offers[0].uuid]
        assert loaded.offers[0].area_details[0].area_uuid == loaded.areas[0].uuid
        assert loaded.meta.scraped_at
    empty = catalog.model_copy(deep=True)
    empty.offers = []
    empty.areas[0].offer_ids = []
    await seed(database, empty)
    async with database() as session:
        loaded = await load_catalog(session)
        assert not loaded.offers
        assert not loaded.areas[0].offer_ids
        assert not (await session.exec(select(OfferRow))).one().is_active
    empty.areas = []
    await seed(database, empty)
    async with database() as session:
        assert not (await load_catalog(session)).areas
        assert not (await session.exec(select(AreaRow))).one().is_active


async def test_persistence_failure_rolls_back_snapshot(database, catalog, monkeypatch):
    await seed(database, catalog)
    async with database() as session:
        before = (await load_catalog(session)).model_dump()
        run = await create_run(session)
        run_id = run.id
    modified = catalog.model_copy(deep=True)
    modified.offers[0].general.name = "must roll back"

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    async def collect(self):
        return modified, {"listingErrors": 0, "detailErrors": 0}

    async def broken_save(session, payload, current_run):
        await save_catalog(session, payload, current_run)
        await session.flush()
        raise RuntimeError("injected persistence failure")

    monkeypatch.setattr(jobs, "SessionLocal", database)
    monkeypatch.setattr(jobs, "SiiaaClient", Client)
    monkeypatch.setattr(jobs.ScraperService, "collect", collect)
    monkeypatch.setattr(jobs, "save_catalog", broken_save)
    with pytest.raises(RuntimeError):
        await jobs.execute_run(run_id)
    async with database() as session:
        assert (await load_catalog(session)).model_dump() == before
        failed = await get_run(session, run_id)
        assert failed.status == "failed"
        assert failed.stats == {"listingErrors": 0, "detailErrors": 0}


async def test_database_backed_routes_and_admin_run(database, catalog, monkeypatch):
    run_id = await seed(database, catalog)
    monkeypatch.setenv("ADMIN_API_KEY", "integration-secret")
    get_settings.cache_clear()
    app = create_app()

    async def session_override():
        async with database() as session:
            yield session

    app.dependency_overrides[get_session] = session_override
    area = catalog.areas[0]
    offer = catalog.offers[0]
    key = {"X-Admin-Key": "integration-secret"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/catalog")).json()["offers"][0]["uuid"] == offer.uuid
            page = await client.get(f"/api/v1/areas/{area.slug}")
            assert page.status_code == 200
            assert page.json()["area"]["uuid"] == area.uuid
            assert (await client.get(f"/api/v1/offers/{offer.uuid}")).status_code == 200
            assert (await client.get("/api/v1/areas/missing")).status_code == 404
            assert (await client.get("/api/v1/offers/missing")).status_code == 404
            assert (await client.get(f"/api/v1/scrape/runs/{run_id}")).status_code == 401
            run_response = await client.get(f"/api/v1/scrape/runs/{run_id}", headers=key)
            assert run_response.json()["status"] == "succeeded"
            assert (await client.get("/api/v1/scrape/runs/999999", headers=key)).status_code == 404
            assert (await client.post("/api/v1/scrape/runs")).status_code == 401

            async def collect(self):
                return catalog, {"listingErrors": 0, "detailErrors": 0}

            # Real job admission and persistence, with source HTTP replaced by a fixture.
            monkeypatch.setattr(jobs, "SessionLocal", database)
            monkeypatch.setattr(jobs.ScraperService, "collect", collect)
            response = await client.post("/api/v1/scrape/runs", headers=key)
            assert response.status_code == 202
            await asyncio.gather(*app.state.scrape_jobs._tasks)
            result = await client.get(f"/api/v1/scrape/runs/{response.json()['id']}", headers=key)
            assert result.json()["status"] == "succeeded"
    finally:
        await app.state.scrape_jobs.close()
        get_settings.cache_clear()


async def test_limited_runs_preserve_existing_records_and_are_idempotent(database, catalog):
    await seed(database, catalog)
    sample = catalog.model_copy(deep=True)
    sample.offers[0].uuid = "limited-offer"
    sample.offers[0].listing.folio = "limited-folio"
    sample.areas[0].uuid = "limited-area"
    sample.areas[0].slug = "limited-area"
    sample.areas[0].offer_ids = ["limited-offer"]
    sample.offers[0].area_details[0].area_uuid = "limited-area"
    for _ in range(2):
        async with database() as session:
            run = await create_run(session)
            await save_catalog(session, sample, run.id, deactivate_missing=False)
            await finish_run(session, run.id, "succeeded", {"limitOffers": 1}, None)
            await session.commit()
    async with database() as session:
        loaded = await load_catalog(session)
        assert {offer.uuid for offer in loaded.offers} == {catalog.offers[0].uuid, "limited-offer"}
        assert {area.uuid for area in loaded.areas} == {catalog.areas[0].uuid, "limited-area"}
        assert len((await session.exec(select(OfferAreaRow))).all()) == 2
