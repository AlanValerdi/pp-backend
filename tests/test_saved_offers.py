from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import auth_service, get_session
from app.core.config import get_settings
from app.modules.auth.models import User
from app.modules.saved_offers import repository, service
from app.modules.saved_offers.models import SavedOffer
from app.modules.saved_offers.router import router
from app.modules.saved_offers.schemas import SavedOfferListItem


@pytest.fixture
def saved_app(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_session] = session_override
    yield app
    get_settings.cache_clear()


async def test_private_routes_reject_missing_and_expired_sessions(saved_app, monkeypatch):
    monkeypatch.setattr(auth_service, "get_current_user", AsyncMock(return_value=None))
    async with AsyncClient(transport=ASGITransport(app=saved_app), base_url="http://test") as client:
        for headers in ({}, {"Cookie": "pp_session=expired"}):
            for response in (
                await client.get("/api/v1/saved-offers", headers=headers),
                await client.post("/api/v1/saved-offers/example", headers=headers),
                await client.delete("/api/v1/saved-offers/example", headers=headers),
            ):
                assert response.status_code == 401
                assert response.headers["cache-control"] == "no-store"


async def test_list_uses_authenticated_user_and_camel_case(saved_app, monkeypatch):
    user = User(google_sub="test", email="test@example.com", name="Test")
    monkeypatch.setattr(auth_service, "get_current_user", AsyncMock(return_value=user))
    item = SavedOfferListItem(
        offer_uuid="example",
        created_at=datetime.now(UTC),
        title="A saved program",
        folio="123",
        remuneration="",
        is_active=False,
        area_slug=None,
        supervisor_email="",
        work_address="",
    )
    listing = AsyncMock(return_value=[item])
    monkeypatch.setattr(service, "list_saved_offers", listing)
    async with AsyncClient(transport=ASGITransport(app=saved_app), base_url="http://test") as client:
        response = await client.get("/api/v1/saved-offers?user_id=someone-else")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()[0]["offerUuid"] == "example"
    assert response.json()[0]["isActive"] is False
    assert response.json()[0]["areaSlug"] is None
    assert "userId" not in response.json()[0]
    assert listing.await_args.kwargs["user_id"] == user.id


async def test_save_requires_browser_headers_and_preserves_post_contract(saved_app, monkeypatch):
    user = User(google_sub="test", email="test@example.com", name="Test")
    monkeypatch.setattr(auth_service, "get_current_user", AsyncMock(return_value=user))
    saved = SavedOffer(user_id=user.id, offer_uuid="example")
    saving = AsyncMock(side_effect=[(saved, True), (saved, False), service.OfferNotFoundError()])
    monkeypatch.setattr(service, "save_offer", saving)
    async with AsyncClient(transport=ASGITransport(app=saved_app), base_url="http://test") as client:
        for headers in (
            {},
            {"Origin": "http://localhost:3000"},
            {"Origin": "https://untrusted.example", "X-Requested-With": "XMLHttpRequest"},
        ):
            assert (await client.post("/api/v1/saved-offers/example", headers=headers)).status_code == 403
        saving.assert_not_awaited()
        headers = {"Origin": "http://localhost:3000", "X-Requested-With": "XMLHttpRequest"}
        created = await client.post("/api/v1/saved-offers/example", headers=headers)
        repeated = await client.post("/api/v1/saved-offers/example", headers=headers)
        missing = await client.post("/api/v1/saved-offers/missing", headers=headers)
    assert created.status_code == 201
    assert repeated.status_code == 200
    assert created.json() == repeated.json()
    assert missing.status_code == 404
    assert saving.await_args_list[0].kwargs["user_id"] == user.id


async def test_save_rolls_back_failed_commit(monkeypatch):
    user = User(google_sub="test", email="test@example.com", name="Test")
    saved = SavedOffer(user_id=user.id, offer_uuid="example")
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("commit failed")
    monkeypatch.setattr(repository, "offer_exists", AsyncMock(return_value=True))
    monkeypatch.setattr(repository, "create_saved_offer", AsyncMock(return_value=(saved, True)))
    with pytest.raises(RuntimeError, match="commit failed"):
        await service.save_offer(session, user_id=user.id, offer_uuid="example")
    session.rollback.assert_awaited_once()


async def test_remove_requires_browser_headers_and_uses_current_user(saved_app, monkeypatch):
    user = User(google_sub="test", email="test@example.com", name="Test")
    monkeypatch.setattr(auth_service, "get_current_user", AsyncMock(return_value=user))
    removing = AsyncMock()
    monkeypatch.setattr(service, "remove_saved_offer", removing)
    async with AsyncClient(transport=ASGITransport(app=saved_app), base_url="http://test") as client:
        for headers in (
            {},
            {"Origin": "http://localhost:3000"},
            {"Origin": "https://untrusted.example", "X-Requested-With": "XMLHttpRequest"},
        ):
            assert (await client.delete("/api/v1/saved-offers/example", headers=headers)).status_code == 403
        removing.assert_not_awaited()
        headers = {"Origin": "http://localhost:3000", "X-Requested-With": "XMLHttpRequest"}
        for _ in range(2):
            response = await client.delete(
                "/api/v1/saved-offers/example?user_id=someone-else", headers=headers
            )
            assert response.status_code == 204
            assert response.content == b""
            assert response.headers["cache-control"] == "no-store"
    assert removing.await_count == 2
    assert removing.await_args.kwargs == {"user_id": user.id, "offer_uuid": "example"}


async def test_remove_commits_and_rolls_back_failure(monkeypatch):
    user = User(google_sub="test", email="test@example.com", name="Test")
    removing = AsyncMock()
    monkeypatch.setattr(repository, "delete_saved_offer", removing)
    session = AsyncMock()
    await service.remove_saved_offer(session, user_id=user.id, offer_uuid="example")
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    assert removing.await_args.kwargs == {"user_id": user.id, "offer_uuid": "example"}
    session.commit.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError, match="commit failed"):
        await service.remove_saved_offer(session, user_id=user.id, offer_uuid="example")
    session.rollback.assert_awaited_once()
