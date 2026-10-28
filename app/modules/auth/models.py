from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Text
from sqlmodel import Field, SQLModel

from app.core.db import NAMING_CONVENTION

SQLModel.metadata.naming_convention = NAMING_CONVENTION


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    google_sub: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    email: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field(sa_column=Column(Text, nullable=False))
    avatar_url: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now)
    )


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True, ondelete="CASCADE")
    token_hash: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    created_at: datetime = Field(
        default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
