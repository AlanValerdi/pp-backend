from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import BrowserRequestDep, CurrentUserDep, SessionDep
from app.modules.saved_offers import service
from app.modules.saved_offers.schemas import SavedOfferListItem, SavedOfferRead

router = APIRouter(
    prefix="/saved-offers",
    tags=["saved-offers"],
)


@router.delete("/{offer_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_saved_offer(
    offer_uuid: str,
    session: SessionDep,
    current_user: CurrentUserDep,
    _: BrowserRequestDep,
) -> Response:
    await service.remove_saved_offer(session, user_id=current_user.id, offer_uuid=offer_uuid)
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={"Cache-Control": "no-store"})


@router.get("", response_model=list[SavedOfferListItem])
async def list_saved_offers(
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[SavedOfferListItem]:
    response.headers["Cache-Control"] = "no-store"
    return await service.list_saved_offers(session, user_id=current_user.id)


@router.post(
    "/{offer_uuid}",
    response_model=SavedOfferRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        200: {
            "model": SavedOfferRead,
            "description": "La oferta ya estaba guardada",
        },
    },
)
async def save_offer(
    offer_uuid: str,
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
    _: BrowserRequestDep,
) -> SavedOfferRead:
    try:
        saved_offer, created = await service.save_offer(
            session,
            user_id=current_user.id,
            offer_uuid=offer_uuid,
        )
    except service.OfferNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada",
            headers={"Cache-Control": "no-store"},
        ) from None

    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    response.headers["Cache-Control"] = "no-store"

    return SavedOfferRead.model_validate(saved_offer)
