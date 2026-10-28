import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import get_settings
from app.modules.auth import repository
from app.modules.auth.models import User


@dataclass
class LoginResult:
    user: User
    expires_at: datetime
    token: str = field(repr=False)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def login_verified_google_user(
    session: AsyncSession,
    *,
    google_sub: str,
    email: str,
    name: str,
    avatar_url: str | None,
) -> LoginResult:
    settings = get_settings()

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(
        seconds=settings.session_ttl_seconds,
    )

    try:
        user = await repository.upsert_google_user(
            session,
            google_sub=google_sub,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )

        await repository.create_user_session(
            session,
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
        )

        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return LoginResult(
        user=user,
        expires_at=expires_at,
        token=token,
    )


async def get_current_user(
    session: AsyncSession,
    *,
    token: str | None,
) -> User | None:
    if not token:
        return None

    return await repository.get_user_for_session(
        session,
        token_hash=hash_session_token(token),
        now=datetime.now(UTC),
    )


async def logout(
    session: AsyncSession,
    *,
    token: str | None,
) -> None:
    if not token:
        return

    try:
        await repository.delete_user_session(
            session,
            token_hash=hash_session_token(token),
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise