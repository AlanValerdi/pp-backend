from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import auth_service, get_session
from app.core.config import get_settings
from app.modules.auth.models import User
from app.modules.auth.schemas import UserRead
from app.modules.geocoding import repository, service
from app.modules.geocoding.models import GeocodedAddress
from app.modules.geocoding.router import get_geocoder, router
from app.modules.geocoding.service import RunStats

BROWSER = {"Origin": "http://localhost:3000", "X-Requested-With": "XMLHttpRequest"}


@pytest.fixture
def geo_app(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def session_override():
        yield AsyncMock()

    async def geocoder_override():
        yield AsyncMock()

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_geocoder] = geocoder_override
    yield app
    get_settings.cache_clear()


def _login(monkeypatch, role: str | None):
    user = None if role is None else User(google_sub="t", email="t@example.com", name="T", role=role)
    monkeypatch.setattr(auth_service, "get_current_user", AsyncMock(return_value=user))


def _row(key: str, status: str, lat=None, lng=None) -> GeocodedAddress:
    return GeocodedAddress(
        address_key=key,
        raw_address=key.title(),
        lat=lat,
        lng=lng,
        status=status,
        source="admin" if status == "manual" else None,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


ADMIN_CALLS = [
    ("get", "/api/v1/admin/geocoding", None),
    ("put", "/api/v1/admin/geocoding/some%20key", {"lat": 19.0, "lng": -98.0}),
    ("post", "/api/v1/geocoding/runs", None),
]


@pytest.mark.parametrize(("method", "url", "body"), ADMIN_CALLS)
async def test_admin_endpoints_return_401_without_session(geo_app, monkeypatch, method, url, body):
    _login(monkeypatch, None)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.request(method, url, json=body, headers=BROWSER)
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "url", "body"), ADMIN_CALLS)
async def test_admin_endpoints_return_403_for_plain_users(geo_app, monkeypatch, method, url, body):
    _login(monkeypatch, "user")
    run = AsyncMock()
    monkeypatch.setattr(service, "run_geocoding", run)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.request(method, url, json=body, headers=BROWSER)
    assert response.status_code == 403
    run.assert_not_awaited()


async def test_admin_lists_addresses_filtered_by_status(geo_app, monkeypatch):
    _login(monkeypatch, "admin")
    listing = AsyncMock(return_value=[_row("plaza", "not_found")])
    monkeypatch.setattr(service, "list_addresses", listing)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/geocoding?status=not_found")
        approx = await client.get("/api/v1/admin/geocoding?status=approximate")
        invalid = await client.get("/api/v1/admin/geocoding?status=bogus")
    assert response.status_code == 200
    assert response.json()[0]["addressKey"] == "plaza"
    assert response.json()[0]["rawAddress"] == "Plaza"
    assert response.json()[0]["status"] == "not_found"
    assert listing.await_args_list[0].kwargs["status"] == "not_found"
    assert invalid.status_code == 422
    assert approx.status_code == 200
    assert listing.await_args.kwargs["status"] == "approximate"


async def test_admin_sets_manual_coordinates(geo_app, monkeypatch):
    _login(monkeypatch, "admin")
    setting = AsyncMock(return_value=_row("a/b, c", "manual", 19.04, -98.2))
    monkeypatch.setattr(service, "set_manual", setting)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.put(
            "/api/v1/admin/geocoding/a%2Fb, c", json={"lat": 19.04, "lng": -98.2}, headers=BROWSER
        )
    assert response.status_code == 200
    assert response.json()["status"] == "manual"
    assert response.json()["source"] == "admin"
    assert setting.await_args.args[1] == "a/b, c"
    assert (setting.await_args.kwargs["lat"], setting.await_args.kwargs["lng"]) == (19.04, -98.2)


@pytest.mark.parametrize(
    "body", [{"lat": 91, "lng": 0}, {"lat": -91, "lng": 0}, {"lat": 0, "lng": 181}, {"lat": 0}]
)
async def test_admin_put_validates_coordinate_ranges(geo_app, monkeypatch, body):
    _login(monkeypatch, "admin")
    setting = AsyncMock()
    monkeypatch.setattr(service, "set_manual", setting)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.put("/api/v1/admin/geocoding/plaza", json=body, headers=BROWSER)
    assert response.status_code == 422
    setting.assert_not_awaited()


async def test_admin_put_unknown_address_is_404(geo_app, monkeypatch):
    _login(monkeypatch, "admin")
    monkeypatch.setattr(service, "set_manual", AsyncMock(side_effect=service.AddressNotFoundError()))
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.put(
            "/api/v1/admin/geocoding/nope", json={"lat": 1, "lng": 1}, headers=BROWSER
        )
    assert response.status_code == 404


async def test_admin_put_requires_browser_headers(geo_app, monkeypatch):
    _login(monkeypatch, "admin")
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.put("/api/v1/admin/geocoding/plaza", json={"lat": 1, "lng": 1})
    assert response.status_code == 403


async def test_admin_triggers_a_geocoding_run(geo_app, monkeypatch):
    _login(monkeypatch, "admin")
    run = AsyncMock(return_value=RunStats(created=2, geocoded=1, approximate=3, not_found=1, failed=0))
    monkeypatch.setattr(service, "run_geocoding", run)
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.post("/api/v1/geocoding/runs", headers=BROWSER)
    assert response.status_code == 200
    assert response.json() == {
        "created": 2,
        "geocoded": 1,
        "approximate": 3,
        "notFound": 1,
        "failed": 0,
    }
    assert run.await_args.kwargs == {"retry_not_found": False}
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        await client.post("/api/v1/geocoding/runs?retryNotFound=true", headers=BROWSER)
    assert run.await_args.kwargs == {"retry_not_found": True}


async def test_set_manual_is_stored_as_manual_by_admin(monkeypatch):
    saving = AsyncMock(return_value=_row("plaza", "manual", 1.0, 2.0))
    monkeypatch.setattr(repository, "set_manual", saving)
    session = AsyncMock()
    row = await service.set_manual(session, "plaza", lat=1.0, lng=2.0)
    assert row.status == "manual"
    session.commit.assert_awaited_once()
    monkeypatch.setattr(repository, "set_manual", AsyncMock(return_value=None))
    with pytest.raises(service.AddressNotFoundError):
        await service.set_manual(session, "missing", lat=1.0, lng=2.0)


# --- /map/pins -----------------------------------------------------------------


def _offers():
    # (uuid, folio, title, address, area_slug)
    return [
        ("u1", "F1", "Offer 1", "Plaza Ok", "salud"),
        ("u2", "F2", "Offer 2", "plaza  MANUAL", None),
        ("u3", "F3", "Offer 3", "Plaza Pending", "salud"),
        ("u4", "F4", "Offer 4", "Plaza Missing", "salud"),
        ("u5", "F5", "Offer 5", "Virtual", "salud"),
        ("u6", "F6", "Offer 6", "Plaza Unknown", "salud"),
        ("u7", "F7", "Offer 7", "Plaza Broken", "salud"),
        ("u8", "F8", "Offer 8", "Plaza Approx", "salud"),
    ]


def _rows():
    return {
        "plaza ok": _row("plaza ok", "ok", 19.0, -98.0),
        "plaza manual": _row("plaza manual", "manual", 20.0, -99.0),
        "plaza pending": _row("plaza pending", "pending"),
        "plaza missing": _row("plaza missing", "not_found"),
        "virtual": _row("virtual", "virtual"),
        "plaza approx": _row("plaza approx", "approximate", 21.0, -97.0),
        "plaza broken": _row("plaza broken", "ok"),  # ok without coordinates must be ignored
    }


async def test_list_pins_returns_only_ok_and_manual_addresses(monkeypatch):
    monkeypatch.setattr(repository, "active_offers", AsyncMock(return_value=_offers()))
    monkeypatch.setattr(repository, "all_by_key", AsyncMock(return_value=_rows()))
    pins = await service.list_pins(AsyncMock())
    assert [p.offer_uuid for p in pins] == ["u1", "u2", "u8"]
    assert [p.precision for p in pins] == ["exact", "exact", "approximate"]
    assert (pins[0].lat, pins[0].lng) == (19.0, -98.0)
    assert (pins[1].lat, pins[1].lng) == (20.0, -99.0)
    assert pins[1].address == "plaza  MANUAL"


async def test_map_pins_endpoint_is_public_and_camel_case(geo_app, monkeypatch):
    monkeypatch.setattr(repository, "active_offers", AsyncMock(return_value=_offers()))
    monkeypatch.setattr(repository, "all_by_key", AsyncMock(return_value=_rows()))
    async with AsyncClient(transport=ASGITransport(app=geo_app), base_url="http://test") as client:
        response = await client.get("/api/v1/map/pins")
    assert response.status_code == 200
    assert response.json()[0] == {
        "offerUuid": "u1",
        "title": "Offer 1",
        "folio": "F1",
        "areaSlug": "salud",
        "address": "Plaza Ok",
        "lat": 19.0,
        "lng": -98.0,
        "precision": "exact",
    }
    assert response.json()[1]["areaSlug"] is None


def test_user_read_exposes_role():
    user = User(google_sub="t", email="t@example.com", name="T", role="admin")
    assert UserRead.model_validate(user).model_dump(by_alias=True)["role"] == "admin"
    assert User(google_sub="t", email="t@example.com", name="T").role == "user"
