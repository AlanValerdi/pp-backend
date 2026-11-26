from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.api.deps import AdminUserDep, BrowserRequestDep, SessionDep
from app.modules.geocoding import service
from app.modules.geocoding.client import NominatimClient
from app.modules.geocoding.schemas import (
    GeocodedAddressRead,
    GeocodingRunRead,
    GeocodingStatus,
    ManualCoordinates,
    MapPin,
)

router = APIRouter(tags=["geocoding"])


async def get_geocoder() -> AsyncIterator[service.Geocoder]:
    async with NominatimClient() as client:
        yield client


GeocoderDep = Annotated[service.Geocoder, Depends(get_geocoder)]


@router.get("/map/pins", response_model=list[MapPin])
async def list_map_pins(session: SessionDep) -> list[MapPin]:
    return await service.list_pins(session)


@router.get("/admin/geocoding", response_model=list[GeocodedAddressRead])
async def list_geocoded_addresses(
    response: Response,
    session: SessionDep,
    _: AdminUserDep,
    status: GeocodingStatus | None = None,
) -> list[GeocodedAddressRead]:
    response.headers["Cache-Control"] = "no-store"
    rows = await service.list_addresses(session, status=status)
    return [GeocodedAddressRead.model_validate(row) for row in rows]


@router.put("/admin/geocoding/{address_key:path}", response_model=GeocodedAddressRead)
async def set_manual_coordinates(
    address_key: str,
    body: ManualCoordinates,
    response: Response,
    session: SessionDep,
    _: AdminUserDep,
    __: BrowserRequestDep,
) -> GeocodedAddressRead:
    response.headers["Cache-Control"] = "no-store"
    try:
        row = await service.set_manual(session, address_key, lat=body.lat, lng=body.lng)
    except service.AddressNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dirección no encontrada",
            headers={"Cache-Control": "no-store"},
        ) from None
    return GeocodedAddressRead.model_validate(row)


@router.post("/geocoding/runs", response_model=GeocodingRunRead)
async def run_geocoding(
    response: Response,
    session: SessionDep,
    geocoder: GeocoderDep,
    _: AdminUserDep,
    __: BrowserRequestDep,
    retry_not_found: Annotated[bool, Query(alias="retryNotFound")] = False,
) -> GeocodingRunRead:
    response.headers["Cache-Control"] = "no-store"
    stats = await service.run_geocoding(session, geocoder, retry_not_found=retry_not_found)
    return GeocodingRunRead(
        created=stats.created,
        geocoded=stats.geocoded,
        approximate=stats.approximate,
        not_found=stats.not_found,
        failed=stats.failed,
    )
