from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.catalog.models import AreaRow, OfferAreaRow, OfferRow
from app.modules.geocoding.models import GeocodedAddress


async def active_offer_addresses(session: AsyncSession) -> list[str]:
    statement = select(OfferRow.supervisor_work_address).where(col(OfferRow.is_active).is_(True))
    return list((await session.exec(statement)).all())


async def insert_missing(session: AsyncSession, rows: list[GeocodedAddress]) -> int:
    """Insert rows that do not exist yet (existing rows, manual ones included, are untouched)."""
    if not rows:
        return 0
    statement = (
        insert(GeocodedAddress)
        .values([row.model_dump() for row in rows])
        .on_conflict_do_nothing(index_elements=["address_key"])
        .returning(col(GeocodedAddress.address_key))
    )
    return len((await session.exec(statement)).all())


async def list_by_status(session: AsyncSession, status: str) -> list[GeocodedAddress]:
    statement = (
        select(GeocodedAddress).where(GeocodedAddress.status == status).order_by(GeocodedAddress.address_key)
    )
    return list((await session.exec(statement)).all())


async def save_result(
    session: AsyncSession,
    address_key: str,
    *,
    lat: float | None,
    lng: float | None,
    status: str,
) -> None:
    """Record a geocoder outcome; only ever touches rows that are still pending."""
    statement = (
        update(GeocodedAddress)
        .where(col(GeocodedAddress.address_key) == address_key, col(GeocodedAddress.status) == "pending")
        .values(
            lat=lat,
            lng=lng,
            status=status,
            source="nominatim" if status in ("ok", "approximate") else None,
            updated_at=datetime.now(UTC),
        )
    )
    await session.exec(statement)


async def reset_not_found(session: AsyncSession) -> int:
    """Send not_found rows back to pending so the job retries them (manual rows are not affected)."""
    statement = (
        update(GeocodedAddress)
        .where(col(GeocodedAddress.status) == "not_found")
        .values(status="pending", updated_at=datetime.now(UTC))
        .returning(col(GeocodedAddress.address_key))
    )
    return len((await session.exec(statement)).all())


async def list_addresses(session: AsyncSession, *, status: str | None = None) -> list[GeocodedAddress]:
    statement = select(GeocodedAddress).order_by(GeocodedAddress.address_key)
    if status is not None:
        statement = statement.where(GeocodedAddress.status == status)
    return list((await session.exec(statement)).all())


async def set_manual(
    session: AsyncSession, address_key: str, *, lat: float, lng: float
) -> GeocodedAddress | None:
    row = await session.get(GeocodedAddress, address_key)
    if row is None:
        return None
    row.lat, row.lng = lat, lng
    row.status, row.source = "manual", "admin"
    row.updated_at = datetime.now(UTC)
    session.add(row)
    await session.flush()
    return row


async def all_by_key(session: AsyncSession) -> dict[str, GeocodedAddress]:
    rows = (await session.exec(select(GeocodedAddress))).all()
    return {row.address_key: row for row in rows}


async def active_offers(session: AsyncSession) -> list[tuple[str, str, str, str, list[str]]]:
    """(uuid, folio, title, work address, sorted area slugs) for every active offer.

    An offer can be open to many areas, so all of them are returned.
    """
    offers = (
        await session.exec(select(OfferRow).where(col(OfferRow.is_active).is_(True)).order_by(OfferRow.folio))
    ).all()
    if not offers:
        return []
    area_statement = (
        select(OfferAreaRow.offer_uuid, AreaRow.slug)
        .join(AreaRow, col(AreaRow.uuid) == OfferAreaRow.area_uuid)
        .where(col(OfferAreaRow.offer_uuid).in_([o.uuid for o in offers]), col(AreaRow.is_active).is_(True))
        .order_by(AreaRow.slug)
    )
    slugs: dict[str, list[str]] = {}
    for offer_uuid, slug in (await session.exec(area_statement)).all():
        slugs.setdefault(offer_uuid, []).append(slug)
    return [
        (o.uuid, o.folio, o.listing_programa, o.supervisor_work_address, slugs.get(o.uuid, []))
        for o in offers
    ]
