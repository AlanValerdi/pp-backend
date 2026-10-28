from datetime import datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.auth.models import User, UserSession


async def upsert_google_user(
    session: AsyncSession,
    *,
    google_sub: str,
    email: str,
    name: str,
    avatar_url: str | None,
) -> User:
    user = User(
        google_sub=google_sub,
        email=email,
        name=name,
        avatar_url=avatar_url,
    )

    statement = insert(User).values(user.model_dump())

    statement = statement.on_conflict_do_update(
        index_elements=[User.google_sub],
        set_={
            "email": statement.excluded.email,
            "name": statement.excluded.name,
            "avatar_url": statement.excluded.avatar_url,
            "updated_at": statement.excluded.updated_at,
        },
    ).returning(User)

    result = await session.exec(
        statement,
        execution_options={"populate_existing": True},
    )
    return result.scalar_one()

async def create_user_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_hash: str,
    expires_at: datetime,
) -> UserSession:
    user_session = UserSession(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    session.add(user_session)
    await session.flush()
    return user_session

async def get_user_for_session(
    session: AsyncSession,
    *,
    token_hash: str,
    now: datetime,
) -> User | None:
    statement = (
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            UserSession.token_hash == token_hash,
            UserSession.expires_at > now,
        )
    )

    result = await session.exec(statement)
    return result.first()

async def delete_user_session(
    session: AsyncSession,
    *,
    token_hash: str,
) -> None:
    statement = delete(UserSession).where(
        UserSession.token_hash == token_hash,
    )
    await session.execute(statement)