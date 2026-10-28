from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.catalog.models import AreaRow, OfferAreaRow, OfferRow
from app.modules.saved_offers.models import SavedOffer


async def delete_saved_offer(
    session: AsyncSession,
    *,
    user_id: UUID,
    offer_uuid: str,
) -> None:
    statement = delete(SavedOffer).where(
        col(SavedOffer.user_id) == user_id,
        col(SavedOffer.offer_uuid) == offer_uuid,
    )
    await session.exec(statement)


async def offer_exists(
    session: AsyncSession,
    *,
    offer_uuid: str,
) -> bool:
    offer = await session.get(OfferRow, offer_uuid)
    return offer is not None


async def create_saved_offer(
    session: AsyncSession,
    *,
    user_id: UUID,
    offer_uuid: str,
) -> tuple[SavedOffer, bool]:
    saved_offer = SavedOffer(
        user_id=user_id,
        offer_uuid=offer_uuid,
    )

    statement = (
        insert(SavedOffer)
        .values(saved_offer.model_dump())
        .on_conflict_do_nothing(
            index_elements=["user_id", "offer_uuid"],
        )
        .returning(SavedOffer)
    )

    result = await session.exec(statement)
    created = result.scalar_one_or_none()

    if created is not None:
        return created, True

    existing = await session.get(
        SavedOffer,
        (user_id, offer_uuid),
    )

    if existing is None:
        raise RuntimeError("No se pudo recuperar la oferta guardada")

    return existing, False


async def list_saved_offers(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> list[tuple[SavedOffer, OfferRow, str | None]]:
    statement = (
        select(SavedOffer, OfferRow)
        .join(OfferRow, col(OfferRow.uuid) == SavedOffer.offer_uuid)
        .where(SavedOffer.user_id == user_id)
        .order_by(col(SavedOffer.created_at).desc(), SavedOffer.offer_uuid)
    )
    saved_rows = (await session.exec(statement)).all()
    if not saved_rows:
        return []

    area_statement = (
        select(OfferAreaRow.offer_uuid, AreaRow.slug)
        .join(AreaRow, col(AreaRow.uuid) == OfferAreaRow.area_uuid)
        .where(
            col(OfferAreaRow.offer_uuid).in_([saved.offer_uuid for saved, _ in saved_rows]),
            col(AreaRow.is_active).is_(True),
        )
        .order_by(AreaRow.slug)
    )
    slugs: dict[str, str] = {}
    for offer_uuid, slug in (await session.exec(area_statement)).all():
        slugs.setdefault(offer_uuid, slug)

    return [(saved, offer, slugs.get(saved.offer_uuid)) for saved, offer in saved_rows]
