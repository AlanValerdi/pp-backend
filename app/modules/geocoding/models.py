from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Text
from sqlmodel import Field, SQLModel

from app.core.db import NAMING_CONVENTION

SQLModel.metadata.naming_convention = NAMING_CONVENTION

STATUSES = ("pending", "ok", "not_found", "manual", "virtual")
SOURCES = ("nominatim", "admin")


def utc_now() -> datetime:
    return datetime.now(UTC)


class GeocodedAddress(SQLModel, table=True):
    __tablename__ = "geocoded_addresses"
    __table_args__ = (
        CheckConstraint("status in ('pending', 'ok', 'not_found', 'manual', 'virtual')", name="status_valid"),
        CheckConstraint("source is null or source in ('nominatim', 'admin')", name="source_valid"),
    )

    address_key: str = Field(sa_column=Column(Text, primary_key=True))
    raw_address: str = Field(sa_column=Column(Text, nullable=False))
    lat: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    lng: float | None = Field(default=None, sa_column=Column(Float, nullable=True))
    status: str = Field(default="pending", sa_column=Column(Text, nullable=False))
    source: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )
