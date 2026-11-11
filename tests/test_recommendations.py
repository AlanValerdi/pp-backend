import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from google.genai import errors
from httpx import ASGITransport, AsyncClient
from pypdf import PdfWriter

from app.api.deps import get_session, require_current_user
from app.core.config import get_settings
from app.integrations import gemini
from app.modules.auth.models import User
from app.modules.catalog.schemas import AreaPage, Catalog
from app.modules.recommendations import service
from app.modules.recommendations.errors import RecommendationError
from app.modules.recommendations.router import router
from app.modules.recommendations.schemas import ModelAnalysis, ModelChoice, ProfileSummary


def pdf_bytes(*, encrypted=False, pages=1):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    if encrypted:
        writer.encrypt("secret")
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.fixture
def page():
    catalog = Catalog.model_validate_json((Path(__file__).parent / "fixtures/catalog.json").read_text())
    return AreaPage(area=catalog.areas[0], offers=catalog.offers)


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.parametrize(
    "payload,status",
    [(b"", 422), (b"not pdf", 422), (b"%PDF-1.7 broken", 422), (b"x" * (service.MAX_CV_BYTES + 1), 413)],
)
def test_invalid_pdf(payload, status):
    with pytest.raises(RecommendationError) as error:
        service.validate_pdf(payload)
    assert error.value.status_code == status


def test_protected_and_pageless_pdf():
    for payload in [pdf_bytes(encrypted=True), pdf_bytes(pages=0)]:
        with pytest.raises(RecommendationError) as error:
            service.validate_pdf(payload)
        assert error.value.status_code == 422
    service.validate_pdf(pdf_bytes())


async def test_results_use_catalog_details_and_only_professional_data(page, monkeypatch):
    model = ModelAnalysis(
        cv_readable=True,
        profile=ProfileSummary(skills="Python"),
        choices=[
            ModelChoice(
                offer_id=page.offers[0].uuid, reason="Python se relaciona con las actividades del programa."
            ),
        ],
    )
    read = AsyncMock(return_value=page)
    google = AsyncMock(return_value=model)
    monkeypatch.setattr(service, "read_area", read)
    monkeypatch.setattr(service, "analyze_with_gemini", google)
    result = await service.analyze_cv(None, area_slug=page.area.slug, pdf=pdf_bytes())
    read.assert_awaited_once_with(None, page.area.slug)
    offer = result.recommendations[0]
    assert (offer.title, offer.folio, offer.remuneration) == (
        page.offers[0].listing.programa,
        page.offers[0].listing.folio,
        page.offers[0].program_info.monthly_stipend,
    )
    assert offer.area_slug == page.area.slug
    candidates = google.call_args.kwargs["candidates"]
    assert set(candidates[0]) == {
        "offer_id",
        "title",
        "type",
        "educational_profile",
        "activities",
        "competencies",
    }
    assert "supervisor" not in json.dumps(candidates)
    assert result.profile.education is None


@pytest.mark.parametrize("case", ["unknown", "duplicate", "not_cv"])
async def test_rejects_invalid_model_results(page, monkeypatch, case):
    chosen = ModelChoice(offer_id=page.offers[0].uuid, reason="Afinidad con el perfil")
    choices = [chosen]
    if case == "unknown":
        choices = [ModelChoice(offer_id="invented-offer", reason="Falsa")]
    if case == "duplicate":
        choices = [chosen, chosen]
    model = ModelAnalysis(cv_readable=case != "not_cv", profile=ProfileSummary(), choices=choices)
    monkeypatch.setattr(service, "read_area", AsyncMock(return_value=page))
    monkeypatch.setattr(service, "analyze_with_gemini", AsyncMock(return_value=model))
    with pytest.raises(RecommendationError) as error:
        await service.analyze_cv(None, area_slug=page.area.slug, pdf=pdf_bytes())
    assert error.value.status_code == (422 if case == "not_cv" else 502)


async def test_no_career_or_no_offers_do_not_call_google(page, monkeypatch):
    google = AsyncMock()
    monkeypatch.setattr(service, "analyze_with_gemini", google)
    monkeypatch.setattr(service, "read_area", AsyncMock(return_value=None))
    with pytest.raises(RecommendationError) as error:
        await service.analyze_cv(None, area_slug="missing", pdf=pdf_bytes())
    assert error.value.status_code == 404
    page.offers = []
    monkeypatch.setattr(service, "read_area", AsyncMock(return_value=page))
    result = await service.analyze_cv(None, area_slug=page.area.slug, pdf=pdf_bytes())
    assert result.recommendations == []
    assert result.profile is None
    assert result.message
    google.assert_not_awaited()


async def test_no_matches_is_valid_analysis(page, monkeypatch):
    model = ModelAnalysis(cv_readable=True, profile=ProfileSummary(skills="Fotografía"), choices=[])
    monkeypatch.setattr(service, "read_area", AsyncMock(return_value=page))
    monkeypatch.setattr(service, "analyze_with_gemini", AsyncMock(return_value=model))
    result = await service.analyze_cv(None, area_slug=page.area.slug, pdf=pdf_bytes())
    assert result.profile.skills == "Fotografía"
    assert not result.recommendations
    assert result.message


@pytest.mark.parametrize(
    "kind,status",
    [
        ("quota", 429),
        ("timeout", 504),
        ("malformed", 502),
        ("empty", 502),
        ("denied", 503),
        ("busy", 503),
        ("deadline", 504),
    ],
)
async def test_provider_errors_are_safe_and_connections_close(monkeypatch, kind, status):
    method = AsyncMock()
    if kind == "quota":
        method.side_effect = errors.ClientError(429, {"error": {"message": "sensitive provider detail"}})
    elif kind in {"denied", "busy", "deadline"}:
        method.side_effect = errors.APIError(
            {"denied": 403, "busy": 503, "deadline": 504}[kind],
            {"error": {"message": "sensitive provider detail"}},
        )
    elif kind == "timeout":
        method.side_effect = TimeoutError()
    else:
        method.return_value = SimpleNamespace(text="invalid json" if kind == "malformed" else None)
    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=method), aclose=AsyncMock()),
        close=Mock(),
    )
    monkeypatch.setattr(gemini.genai, "Client", Mock(return_value=client))
    with pytest.raises(RecommendationError) as error:
        await gemini.analyze_with_gemini(b"pdf", career="Computación", candidates=[])
    assert error.value.status_code == status
    assert "sensitive" not in error.value.message
    assert method.await_count == 1
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()


async def test_provider_schema_and_missing_key(monkeypatch):
    model = ModelAnalysis(cv_readable=True, profile=ProfileSummary(tools="React"), choices=[])
    method = AsyncMock(return_value=SimpleNamespace(text=model.model_dump_json()))
    client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content=method), aclose=AsyncMock()),
        close=Mock(),
    )
    factory = Mock(return_value=client)
    monkeypatch.setattr(gemini.genai, "Client", factory)
    result = await gemini.analyze_with_gemini(b"pdf", career="Computación", candidates=[])
    assert result.profile.tools == "React"
    assert method.call_args.kwargs["config"].response_json_schema
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(RecommendationError) as error:
        await gemini.analyze_with_gemini(b"pdf", career="Computación", candidates=[])
    assert error.value.status_code == 503
    assert factory.call_count == 1


async def test_http_auth_origin_and_upload_contract(page, monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session():
        yield None

    app.dependency_overrides[get_session] = session
    monkeypatch.setattr(service, "read_area", AsyncMock(return_value=page))
    monkeypatch.setattr(
        service,
        "analyze_with_gemini",
        AsyncMock(
            return_value=ModelAnalysis(
                cv_readable=True,
                profile=ProfileSummary(tools="React"),
                choices=[
                    ModelChoice(offer_id=page.offers[0].uuid, reason="Afinidad con el perfil"),
                ],
            )
        ),
    )
    headers = {"Origin": "http://localhost:3000", "X-Requested-With": "XMLHttpRequest"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        path = "/api/v1/recommendations/analyze"
        data = {"areaSlug": page.area.slug}
        files = {"cv": ("cv.pdf", pdf_bytes(), "application/pdf")}
        assert (await client.post(path, data=data, files=files, headers=headers)).status_code == 401
        app.dependency_overrides[require_current_user] = lambda: User(
            google_sub="recommendation-test",
            email="test@example.invalid",
            name="Test",
        )
        assert (await client.post(path, data=data, files=files)).status_code == 403
        response = await client.post(path, data=data, files=files, headers=headers)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        item = response.json()["recommendations"][0]
        assert item["offerUuid"] == page.offers[0].uuid
        assert item["areaSlug"] == page.area.slug
        invalid = await client.post(
            path, data=data, files={"cv": ("cv.pdf", b"broken", "application/pdf")}, headers=headers
        )
        assert invalid.status_code == 422
        assert invalid.headers["cache-control"] == "no-store"
        too_big = await client.post(
            path,
            data=data,
            files={"cv": ("cv.pdf", b"x" * (service.MAX_CV_BYTES + 1), "application/pdf")},
            headers=headers,
        )
        assert too_big.status_code == 413
