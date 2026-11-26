import logging
from dataclasses import dataclass
from typing import Protocol

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.geocoding import repository
from app.modules.geocoding.models import GeocodedAddress
from app.modules.geocoding.normalize import geocoding_query, is_virtual, normalize_address
from app.modules.geocoding.schemas import MapPin

logger = logging.getLogger(__name__)


class Geocoder(Protocol):
    async def geocode(self, query: str) -> tuple[float, float] | None: ...


class AddressNotFoundError(Exception):
    pass


@dataclass
class RunStats:
    created: int = 0
    geocoded: int = 0
    not_found: int = 0
    failed: int = 0


async def run_geocoding(session: AsyncSession, client: Geocoder) -> RunStats:
    """Upsert one row per distinct active-offer address, then geocode only the pending ones.

    Resolved rows (ok/not_found) are never re-queried and `manual` rows are never touched.
    """
    stats = RunStats()
    try:
        distinct: dict[str, str] = {}
        for raw in await repository.active_offer_addresses(session):
            distinct.setdefault(normalize_address(raw), raw)
        new_rows = [
            GeocodedAddress(
                address_key=key,
                raw_address=raw,
                status="virtual" if is_virtual(raw) else "pending",
            )
            for key, raw in distinct.items()
        ]
        stats.created = await repository.insert_missing(session, new_rows)
        await session.commit()

        for row in await repository.list_by_status(session, "pending"):
            try:
                coords = await client.geocode(geocoding_query(row.raw_address))
            except httpx.HTTPError:
                logger.warning("geocoding failed for %r; leaving it pending", row.address_key)
                stats.failed += 1
                continue
            if coords is None:
                await repository.save_result(session, row.address_key, lat=None, lng=None, status="not_found")
                stats.not_found += 1
            else:
                lat, lng = coords
                await repository.save_result(session, row.address_key, lat=lat, lng=lng, status="ok")
                stats.geocoded += 1
            await session.commit()
    except Exception:
        await session.rollback()
        raise
    return stats


async def list_addresses(session: AsyncSession, *, status: str | None = None) -> list[GeocodedAddress]:
    return await repository.list_addresses(session, status=status)


async def set_manual(session: AsyncSession, address_key: str, *, lat: float, lng: float) -> GeocodedAddress:
    try:
        row = await repository.set_manual(session, address_key, lat=lat, lng=lng)
        if row is None:
            raise AddressNotFoundError
        await session.commit()
        return row
    except Exception:
        await session.rollback()
        raise


async def list_pins(session: AsyncSession) -> list[MapPin]:
    geocoded = await repository.all_by_key(session)
    pins: list[MapPin] = []
    for offer_uuid, folio, title, address, area_slug in await repository.active_offers(session):
        row = geocoded.get(normalize_address(address))
        if row is None or row.status not in ("ok", "manual") or row.lat is None or row.lng is None:
            continue
        pins.append(
            MapPin(
                offer_uuid=offer_uuid,
                title=title,
                folio=folio,
                area_slug=area_slug,
                address=address,
                lat=row.lat,
                lng=row.lng,
            )
        )
    return pins
