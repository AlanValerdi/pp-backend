from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from app.modules.geocoding import repository
from app.modules.geocoding.client import NOMINATIM_URL, NominatimClient
from app.modules.geocoding.models import GeocodedAddress
from app.modules.geocoding.normalize import geocoding_query, is_virtual, normalize_address
from app.modules.geocoding.service import run_geocoding


def test_normalize_collapses_casing_accent_and_spacing_variants():
    variants = [
        "Calle 4 Sur 104, Centro, Teziutlán",
        "CALLE 4 SUR 104 ,Centro,  TEZIUTLAN",
        "  calle 4   sur 104,  centro , teziutlán.  ",
    ]
    assert len({normalize_address(v) for v in variants}) == 1
    assert normalize_address(variants[0]) == "calle 4 sur 104, centro, teziutlan"


def test_normalize_keeps_distinct_addresses_distinct():
    assert normalize_address("Calle 4 Sur 104") != normalize_address("Calle 4 Sur 105")


@pytest.mark.parametrize("value", ["", "   ", "Virtual", "EN LÍNEA", "en linea", "Trabajo remoto", "Remoto"])
def test_is_virtual_detects_remote_work(value):
    assert is_virtual(value) is True


@pytest.mark.parametrize("value", ["Calle 4 Sur 104, Puebla", "Biblioteca Central Universitaria"])
def test_is_virtual_rejects_physical_addresses(value):
    assert is_virtual(value) is False


def test_geocoding_query_appends_region_only_when_state_is_missing():
    assert geocoding_query("Biblioteca Central Universitaria") == (
        "Biblioteca Central Universitaria, Puebla, México"
    )
    assert geocoding_query("Calle 4 Sur 104, Puebla") == "Calle 4 Sur 104, Puebla"
    assert geocoding_query("Insurgentes Sur, Ciudad de México") == "Insurgentes Sur, Ciudad de México"


# --- Nominatim client -------------------------------------------------------


@respx.mock
async def test_client_sends_policy_compliant_request_and_parses_coordinates():
    route = respx.get(NOMINATIM_URL).mock(
        return_value=httpx.Response(200, json=[{"lat": "19.0414", "lon": "-98.2063"}])
    )
    async with NominatimClient(contact="ops@example.com", sleep=AsyncMock(), clock=lambda: 0.0) as client:
        result = await client.geocode("Zócalo, Puebla, México")
    assert result == (19.0414, -98.2063)
    request = route.calls.last.request
    assert request.url.params["q"] == "Zócalo, Puebla, México"
    assert request.url.params["format"] == "jsonv2"
    assert request.url.params["limit"] == "1"
    assert request.url.params["countrycodes"] == "mx"
    assert request.headers["user-agent"].startswith("PPracticaSS-geocoder/1.0")
    assert "ops@example.com" in request.headers["user-agent"]


@respx.mock
async def test_client_returns_none_when_nothing_found():
    respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(200, json=[]))
    async with NominatimClient(sleep=AsyncMock(), clock=lambda: 0.0) as client:
        assert await client.geocode("nowhere") is None


@respx.mock
async def test_client_throttles_consecutive_calls_to_one_per_second():
    respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(200, json=[]))
    sleep = AsyncMock()
    async with NominatimClient(sleep=sleep, clock=lambda: 100.0) as client:
        await client.geocode("a")
        sleep.assert_not_awaited()
        await client.geocode("b")
    sleep.assert_awaited_once_with(pytest.approx(1.0))


@respx.mock
async def test_client_raises_on_http_errors():
    respx.get(NOMINATIM_URL).mock(return_value=httpx.Response(503))
    async with NominatimClient(sleep=AsyncMock(), clock=lambda: 0.0) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.geocode("a")


# --- Job ---------------------------------------------------------------------


class FakeStore:
    """In-memory stand-in for the geocoding repository."""

    def __init__(self, addresses: list[str], rows: list[GeocodedAddress] | None = None):
        self.addresses = addresses
        self.rows = {r.address_key: r for r in rows or []}

    async def active_offer_addresses(self, session):
        return self.addresses

    async def insert_missing(self, session, rows):
        created = 0
        for row in rows:
            if row.address_key not in self.rows:
                self.rows[row.address_key] = row
                created += 1
        return created

    async def list_by_status(self, session, status):
        return [r for r in self.rows.values() if r.status == status]

    async def save_result(self, session, address_key, *, lat, lng, status):
        row = self.rows[address_key]
        if row.status != "pending":
            return
        row.lat, row.lng, row.status = lat, lng, status
        row.source = "nominatim" if status == "ok" else None


@pytest.fixture
def install_store(monkeypatch):
    def install(store: FakeStore) -> FakeStore:
        for name in ("active_offer_addresses", "insert_missing", "list_by_status", "save_result"):
            monkeypatch.setattr(repository, name, getattr(store, name))
        return store

    return install


async def test_job_geocodes_only_pending_and_never_calls_client_for_virtual_or_manual(install_store):
    manual = GeocodedAddress(
        address_key="plaza manual",
        raw_address="Plaza Manual",
        lat=1.0,
        lng=2.0,
        status="manual",
        source="admin",
    )
    store = install_store(
        FakeStore(
            [
                "Biblioteca Central",
                "biblioteca  CENTRAL",
                "Virtual",
                "",
                "Plaza Manual",
                "Calle 4 Sur 104, Puebla",
            ],
            [manual],
        )
    )
    client = AsyncMock()
    client.geocode.side_effect = [(19.0, -98.0), None]

    stats = await run_geocoding(AsyncMock(), client)

    queried = [call.args[0] for call in client.geocode.await_args_list]
    assert queried == ["Biblioteca Central, Puebla, México", "Calle 4 Sur 104, Puebla"]
    assert store.rows["biblioteca central"].status == "ok"
    assert store.rows["biblioteca central"].source == "nominatim"
    assert store.rows["calle 4 sur 104, puebla"].status == "not_found"
    assert store.rows["virtual"].status == "virtual"
    assert store.rows[""].status == "virtual"
    assert (manual.status, manual.lat, manual.lng) == ("manual", 1.0, 2.0)
    assert (stats.created, stats.geocoded, stats.not_found, stats.failed) == (4, 1, 1, 0)


async def test_job_rerun_does_not_requery_resolved_rows(install_store):
    install_store(FakeStore(["Biblioteca Central", "Calle Ignota"]))
    client = AsyncMock()
    client.geocode.side_effect = [(19.0, -98.0), None]
    await run_geocoding(AsyncMock(), client)
    client.geocode.reset_mock()

    stats = await run_geocoding(AsyncMock(), client)

    client.geocode.assert_not_awaited()
    assert (stats.created, stats.geocoded, stats.not_found) == (0, 0, 0)


async def test_job_leaves_row_pending_when_the_provider_fails(install_store):
    store = install_store(FakeStore(["Biblioteca Central", "Calle 4 Sur 104, Puebla"]))
    client = AsyncMock()
    client.geocode.side_effect = [httpx.ConnectError("boom"), (19.0, -98.0)]

    stats = await run_geocoding(AsyncMock(), client)

    assert store.rows["biblioteca central"].status == "pending"
    assert store.rows["calle 4 sur 104, puebla"].status == "ok"
    assert (stats.geocoded, stats.failed) == (1, 1)
