from typing import Annotated
from fastapi import HTTPException

from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session

from app.core.security import require_admin, require_browser_request
from app.modules.scraper.jobs import ScrapeJobs
from app.modules.auth import service as auth_service
from app.modules.auth.models import User


SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[None, Depends(require_admin)]
BrowserRequestDep = Annotated[None, Depends(require_browser_request)]


async def get_scrape_jobs(request: Request) -> ScrapeJobs:
    return request.app.state.scrape_jobs

async def require_current_user(
    request: Request,
    session: SessionDep,
) -> User:
    user = await auth_service.get_current_user(
        session,
        token=request.cookies.get("pp_session"),
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada",
            headers={"Cache-Control": "no-store"},
        )

    return user


JobsDep = Annotated[ScrapeJobs, Depends(get_scrape_jobs)]
CurrentUserDep = Annotated[User, Depends(require_current_user)]
