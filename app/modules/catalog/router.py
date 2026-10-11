from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.modules.catalog.schemas import AreaPage, Catalog, Offer
from app.modules.catalog.service import read_area, read_catalog, read_offer

health_router = APIRouter(tags=["health"])
router = APIRouter(tags=["catalog"])


@health_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health")
async def health_v1() -> dict[str, str]:
    return {"status": "ok"}


async def get_catalog_payload(session: SessionDep) -> Catalog:
    return await read_catalog(session)


@router.get("/catalog", response_model=Catalog)
async def catalog(payload: Annotated[Catalog, Depends(get_catalog_payload)]) -> Catalog:
    return payload


@router.get("/areas/{slug}", response_model=AreaPage)
async def area(slug: str, session: SessionDep) -> AreaPage:
    page = await read_area(session, slug)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Area not found")
    return page


@router.get("/offers/{offer_uuid}", response_model=Offer)
async def offer(offer_uuid: str, session: SessionDep) -> Offer:
    found = await read_offer(session, offer_uuid)
    if found is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    return found
