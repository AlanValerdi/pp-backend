from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

GeocodingStatus = Literal["pending", "ok", "not_found", "manual", "virtual"]


class CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class MapPin(CamelModel):
    offer_uuid: str
    title: str
    folio: str
    area_slug: str | None
    address: str
    lat: float
    lng: float


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
    not_found: int
    failed: int
