from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

GeocodingStatus = Literal["pending", "ok", "approximate", "not_found", "manual", "virtual"]


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class MapPin(CamelModel):
    offer_uuid: str
    title: str
    folio: str
    # First area slug, kept for the offer detail link; area_slugs lists every area the offer is open to.
    area_slug: str | None
    area_slugs: list[str]
    address: str
    lat: float
    lng: float
    precision: Literal["exact", "approximate"]


class GeocodedAddressRead(CamelModel):
    address_key: str
    raw_address: str
    lat: float | None
    lng: float | None
    status: GeocodingStatus
    source: Literal["nominatim", "admin"] | None
    updated_at: datetime


class ManualCoordinates(CamelModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class GeocodingRunRead(CamelModel):
    created: int
    geocoded: int
    approximate: int
    not_found: int
    failed: int
