import asyncio
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.core.config import Settings
from app.modules.scraper import preview
from app.modules.scraper.jobs import ScrapeAlreadyRunning, ScrapeJobs
from app.modules.scraper.parsers import parse_listing
from app.modules.scraper.router import router

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def source(monkeypatch):
    requests = []
    detail = (FIXTURES / "detail.html").read_text()
    row = parse_listing((FIXTURES / "listing.html").read_text())[0]
    monkeypatch.setattr(
        preview,
        "parse_listing",
        lambda _: [replace(row, folio=str(i), v_01=str(i)) for i in range(20)],
    )
    client_class = httpx.AsyncClient

    def handle(request):
        requests.append(request)
        if "ss_oferta_ss" in request.url.path:
            text = (FIXTURES / "careers.html").read_text()
        elif request.url.path.endswith("Ss_OFERTA_prog"):
            text = "listing"
        else:
            text = detail
        return httpx.Response(200, content=text.encode("latin-1"))

    monkeypatch.setattr(
        preview.httpx,
        "AsyncClient",
        lambda **kwargs: client_class(transport=httpx.MockTransport(handle), **kwargs),
    )
    sleep = AsyncMock()
    monkeypatch.setattr(preview.asyncio, "sleep", sleep)
    return requests, sleep


async def test_preview_caps_details_and_normalizes_without_database(source, caplog):
    requests, sleep = source
    with caplog.at_level("INFO"):
        result = await preview.ScrapePreview(Settings()).run()
    assert caplog.text.count("event=preview_sample_normalized") == 10
    assert "trace_id=preview-" in caplog.text
    assert result.status == "succeeded"
    assert result.detail_attempts == result.successful_parses == 10
    assert len(requests) == result.request_count == 12
    assert len(result.offers) == 10
    assert all(offer.area_details for offer in result.offers)
    assert result.offers[0].general.name == "PRACTICANTE DE COMPRAS"
    assert all(request.method == "POST" for request in requests[1:])
    assert all(b"v_01=" in request.content and b"ca=" in request.content for request in requests[2:])
    assert sleep.await_count == 11
    assert all(0 < call.args[0] <= 1 for call in sleep.await_args_list)


async def test_http_200_error_pages_are_reported_and_bounded(source, monkeypatch):
    original = preview.parse_detail
    count = 0

    def parse(html):
        nonlocal count
        count += 1
        if count == 1:
            return original(html)
        raise ValueError("SIGNATURE MISMATCH")

    monkeypatch.setattr(preview, "parse_detail", parse)
    result = await preview.ScrapePreview(Settings()).run()
    assert result.status == "partial"
    assert result.successful_parses == 1
    assert result.failures == 9
    assert result.requests[-1].http_status == 200
    assert result.requests[-1].error == "SIGNATURE MISMATCH"
    assert len(result.requests[-1].response_excerpt) <= 500


async def test_discovery_is_bounded(source, monkeypatch):
    monkeypatch.setattr(preview, "parse_listing", lambda _: [])
    result = await preview.ScrapePreview(Settings()).run()
    assert result.request_count == 11
    assert result.detail_attempts == 0
    assert result.stop_reason == "discovery_exhausted"


@pytest.mark.parametrize("kind", ["http", "timeout"])
async def test_transport_errors_are_not_retried(source, monkeypatch, kind):
    async def request(self, method, path, **kwargs):
        if kind == "timeout":
            raise httpx.ReadTimeout("sensitive URL must not appear")
        return httpx.Response(500, request=httpx.Request(method, "http://example.test"))

    monkeypatch.setattr(AsyncClient, "request", request)
    result = await preview.ScrapePreview(Settings()).run()
    assert result.request_count == result.failures == 1
    assert result.status == "failed"
    assert "sensitive" not in result.requests[0].error


async def test_deadline_preserves_completed_samples(source, monkeypatch):
    fetch = preview.ScrapePreview._fetch

    async def blocked_fetch(self, http, stage, path, parameters=None):
        if stage == "detail" and self.result.successful_parses == 1:
            await asyncio.Event().wait()
        return await fetch(self, http, stage, path, parameters)

    timeout = asyncio.timeout
    monkeypatch.setattr(preview.asyncio, "timeout", lambda _: timeout(0.05))
    monkeypatch.setattr(preview.ScrapePreview, "_fetch", blocked_fetch)
    result = await preview.ScrapePreview(Settings()).run()
    assert result.stop_reason == "overall_deadline"
    assert result.status == "partial"
    assert result.successful_parses == 1
    assert len(result.offers) == 1


async def test_preview_admission_and_cancellation_release_lock(monkeypatch):
    started = asyncio.Event()

    async def run(self):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(preview.ScrapePreview, "run", run)
    manager = ScrapeJobs()
    task = asyncio.create_task(manager.preview())
    await started.wait()
    with pytest.raises(ScrapeAlreadyRunning):
        await manager.preview()
    with pytest.raises(ScrapeAlreadyRunning):
        await manager.start(AsyncMock())
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not manager._running
    assert not manager._preview_tasks


async def test_preview_failure_releases_lock(monkeypatch):
    monkeypatch.setattr(preview.ScrapePreview, "run", AsyncMock(side_effect=RuntimeError("oops")))
    manager = ScrapeJobs()
    with pytest.raises(RuntimeError):
        await manager.preview()
    assert not manager._running


def test_signature_mismatch_page_is_rejected(caplog):
    with pytest.raises(ValueError):
        preview.parse_detail("<pre>SIGNATURE (parameter names) MISMATCH: V_01,CA</pre>")
    diagnostic = preview.PreviewRequest(stage="detail", url="http://example.test", http_status=200)
    assert (
        preview.ScrapePreview._parse(
            preview.parse_detail, "<pre>SIGNATURE (parameter names) MISMATCH: V_01,CA</pre>", diagnostic
        )
        is None
    )
    assert "event=preview_parse_failed" in caplog.text
    assert "event=preview_sample_normalized" not in caplog.text


async def test_preview_endpoint_auth_response_and_conflict(monkeypatch):
    from app.core.security import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "admin_api_key", "preview-test")
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    manager = ScrapeJobs()
    app.state.scrape_jobs = manager
    monkeypatch.setattr(
        preview.ScrapePreview,
        "run",
        AsyncMock(return_value=preview.PreviewRead(status="partial", stop_reason="discovery_exhausted")),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post("/api/v1/scrape/preview")).status_code == 401
        headers = {"X-Admin-Key": "preview-test"}
        response = await client.post("/api/v1/scrape/preview", headers=headers)
        assert response.status_code == 200
        assert response.json()["stopReason"] == "discovery_exhausted"
        manager._running = True
        assert (await client.post("/api/v1/scrape/preview", headers=headers)).status_code == 409
