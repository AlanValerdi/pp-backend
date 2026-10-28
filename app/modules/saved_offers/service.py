from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.saved_offers import repository
from app.modules.saved_offers.models import SavedOffer
from app.modules.saved_offers.schemas import SavedOfferListItem


class OfferNotFoundError(Exception):
    pass


async def remove_saved_offer(
    session: AsyncSession,
    *,
    user_id: UUID,
    offer_uuid: str,
) -> None:
    try:
        await repository.delete_saved_offer(session, user_id=user_id, offer_uuid=offer_uuid)
        await session.commit()
    except Exception:
        await session.rollback()
        raise


async def save_offer(
    session: AsyncSession,
    *,
    user_id: UUID,
    offer_uuid: str,
) -> tuple[SavedOffer, bool]:
    try:
        exists = await repository.offer_exists(
            session,
            offer_uuid=offer_uuid,
        )

        if not exists:
            raise OfferNotFoundError

        result = await repository.create_saved_offer(
            session,
            user_id=user_id,
            offer_uuid=offer_uuid,
        )

        await session.commit()
        return result
    except Exception:
        await session.rollback()
        raise


async def list_saved_offers(
    session: AsyncSession,
    *,
    user_id: UUID,
) -> list[SavedOfferListItem]:
    rows = await repository.list_saved_offers(session, user_id=user_id)
    return [
        SavedOfferListItem(
            offer_uuid=saved.offer_uuid,
            created_at=saved.created_at,
            title=offer.listing_programa,
            folio=offer.folio,
            remuneration=offer.program_info_monthly_stipend,
            is_active=offer.is_active,
            area_slug=slug,
            supervisor_email=offer.supervisor_email,
            work_address=offer.supervisor_work_address,
        )
        for saved, offer, slug in rows
    ]
