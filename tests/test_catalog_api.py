import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_session
from app.core.config import get_settings
from app.main import app
from app.modules.catalog.router import get_catalog_payload
from app.modules.catalog.schemas import Catalog
from app.modules.scraper.jobs import ScrapeAlreadyRunning
from app.modules.scraper.models import ScrapeRun
from app.modules.scraper.service import ScraperService

SAMPLE = Path(__file__).parent / "fixtures" / "catalog.json"
FIXTURES = Path(__file__).parent / "fixtures"


class FixtureClient:
    async def get_careers_html(self) -> str:
        return (FIXTURES / "careers.html").read_text(encoding="utf-8")

    async def post_text(self, path: str, data: dict[str, str]) -> str:
        if "CAR_PROG" in path.upper():
            return (FIXTURES / "detail.html").read_text(encoding="utf-8")
        return (FIXTURES / "listing.html").read_text(encoding="utf-8")


class FakeJobs:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    async def start(self, session: object) -> ScrapeRun:
        if self.error:
            raise self.error
        return ScrapeRun(
            id=7,
            status="running",
            started_at=datetime.now(UTC),
            stats={},
        )


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_sample_catalog_matches_the_api_schema() -> None:
    payload = json.loads(SAMPLE.read_text(encoding="utf-8"))
    catalog = Catalog.model_validate(payload)
    dumped = catalog.model_dump(by_alias=True)
    assert set(dumped) == {"meta", "sections", "faculties", "areas", "offers"}
    assert set(dumped["offers"][0]) == set(payload["offers"][0])
    assert set(dumped["offers"][0]["listing"]) == set(payload["offers"][0]["listing"])
    assert set(dumped["offers"][0]["areaDetails"][0]) == {"areaUuid", "activities", "competencies", "listing"}
    assert catalog.sections[3].id == "economia"


async def test_fixture_scrape_builds_a_catalog() -> None:
    catalog, stats = await ScraperService(FixtureClient()).collect(limit_careers=1)  # type: ignore[arg-type]
    dumped = catalog.model_dump(by_alias=True)
    sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    assert set(dumped) == set(sample)
    assert set(dumped["offers"][0]) == set(sample["offers"][0])
    assert stats["careers"] == 1
    assert len(catalog.areas) == 1
    area = catalog.areas[0]
    assert area.name == "Actuaría"
    assert area.level == "Lic"
    assert area.section_id == "licenciaturas"
    assert area.faculty_id == "fcfm"
    assert area.slug == "actuaria"
    assert len(area.offer_ids) == 117
    offer = next(item for item in catalog.offers if item.listing.folio == "246965")
    assert offer.summary.registered_at == "2026-09-01"
    assert offer.summary.period == "1, 2027"
    assert offer.program_info.promotes_entrepreneurship is True
    assert offer.area_details[0].area_uuid == area.uuid
    assert "SAP" in offer.area_details[0].activities


async def test_health_and_catalog_endpoint() -> None:
    sample = Catalog.model_validate(json.loads(SAMPLE.read_text(encoding="utf-8")))

    async def override_catalog() -> Catalog:
        return sample

    app.dependency_overrides[get_catalog_payload] = override_catalog
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        payload = await client.get("/api/v1/catalog")
    assert health.json() == {"status": "ok"}
    body = payload.json()
    assert body["meta"]["schemaVersion"] == 1
    assert body["areas"][0]["offerIds"]
    assert body["offers"][0]["programInfo"]["socialAxes"]


async def test_scrape_run_requires_admin_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    get_settings.cache_clear()

    async def override_session():
        yield None

    app.dependency_overrides[get_session] = override_session
    from app.api.deps import get_scrape_jobs

    async def override_jobs():
        return FakeJobs()

    async def conflicting_jobs():
        return FakeJobs(ScrapeAlreadyRunning())

    app.dependency_overrides[get_scrape_jobs] = override_jobs
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        rejected = await client.post("/api/v1/scrape/runs")
        accepted = await client.post("/api/v1/scrape/runs", headers={"X-Admin-Key": "secret"})
        app.dependency_overrides[get_scrape_jobs] = conflicting_jobs
        conflict = await client.post("/api/v1/scrape/runs", headers={"X-Admin-Key": "secret"})
    assert rejected.status_code == 401
    assert accepted.status_code == 202
    assert accepted.json()["id"] == 7
    assert accepted.json()["status"] == "running"
    assert conflict.status_code == 409


async def test_missing_catalog_resources_and_run_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    from unittest.mock import AsyncMock

    from app.modules.catalog import router as catalog_router
    from app.modules.scraper import router as scrape_router

    monkeypatch.setenv("ADMIN_API_KEY", "secret")
    get_settings.cache_clear()

    async def override_session():
        yield None

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(catalog_router, "read_area", AsyncMock(return_value=None))
    monkeypatch.setattr(catalog_router, "read_offer", AsyncMock(return_value=None))
    monkeypatch.setattr(scrape_router, "get_run", AsyncMock(return_value=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/v1/areas/missing")).status_code == 404
        assert (await client.get("/api/v1/offers/missing")).status_code == 404
        assert (await client.get("/api/v1/scrape/runs/7")).status_code == 401
        assert (
            await client.get("/api/v1/scrape/runs/7", headers={"X-Admin-Key": "secret"})
        ).status_code == 404
