from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.catalog.repository import (
    get_area_by_slug,
    get_offer,
    load_catalog,
    offers_for_area,
)
from app.modules.catalog.schemas import AreaPage, Catalog, Offer


async def read_catalog(session: AsyncSession) -> Catalog:
    return await load_catalog(session)


async def read_area(session: AsyncSession, slug: str) -> AreaPage | None:
    row = await get_area_by_slug(session, slug)
    if row is None:
        return None
    catalog = await load_catalog(session)
    area = next((item for item in catalog.areas if item.uuid == row.uuid), None)
    if area is None:
        return None
    return AreaPage(area=area, offers=await offers_for_area(session, row.uuid))


async def read_offer(session: AsyncSession, offer_uuid: str) -> Offer | None:
    return await get_offer(session, offer_uuid)
