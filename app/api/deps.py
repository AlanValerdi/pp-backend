from typing import Annotated

from fastapi import Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.security import require_admin
from app.modules.scraper.jobs import ScrapeJobs

SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[None, Depends(require_admin)]


async def get_scrape_jobs(request: Request) -> ScrapeJobs:
    return request.app.state.scrape_jobs


JobsDep = Annotated[ScrapeJobs, Depends(get_scrape_jobs)]
