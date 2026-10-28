from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SavedOfferRead(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    offer_uuid: str
    created_at: datetime


class SavedOfferListItem(SavedOfferRead):
    title: str
    folio: str
    remuneration: str
    is_active: bool
    area_slug: str | None
    supervisor_email: str
    work_address: str
