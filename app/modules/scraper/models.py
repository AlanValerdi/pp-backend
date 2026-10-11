from datetime import datetime

from sqlalchemy import Column, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.core.db import NAMING_CONVENTION

SQLModel.metadata.naming_convention = NAMING_CONVENTION


class ScrapeRun(SQLModel, table=True):
    __tablename__ = "scrape_runs"

    id: int | None = Field(default=None, primary_key=True)
    status: str = Field(sa_column=Column(Text, nullable=False))
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    stats: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
