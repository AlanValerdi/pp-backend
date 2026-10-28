from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlmodel import Field, SQLModel

from app.core.db import NAMING_CONVENTION

SQLModel.metadata.naming_convention = NAMING_CONVENTION


def utc_now() -> datetime:
    return datetime.now(UTC)


class SavedOffer(SQLModel, table=True):
    __tablename__ = "saved_offers"

    user_id: UUID = Field(
        foreign_key="users.id",
        primary_key=True,
        ondelete="CASCADE",
    )

    offer_uuid: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("offers.uuid", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
