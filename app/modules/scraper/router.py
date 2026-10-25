from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, JobsDep, SessionDep
from app.modules.catalog.repository import get_run
from app.modules.catalog.schemas import ScrapeRunRead
from app.modules.scraper.jobs import ScrapeAlreadyRunning, run_to_read
from app.modules.scraper.preview import PreviewRead

router = APIRouter(prefix="/scrape", tags=["scrape"])


@router.post("/preview", response_model=PreviewRead)
async def preview(jobs: JobsDep, _: AdminDep) -> PreviewRead:
    """Preview up to 10 detail pages, plus discovery, without database writes.

    Requests are sequential, spaced at least one second apart, and never retried.
    Discovery inspects at most 10 career listings. The overall deadline is 120 seconds.
    Partial samples and per-request errors are returned directly; an active scrape
    or preview causes HTTP 409.
    """
    try:
        return await jobs.preview()
    except ScrapeAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail="A scrape or preview is already running") from exc


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ScrapeRunRead)
async def start_run(session: SessionDep, jobs: JobsDep, _: AdminDep) -> ScrapeRunRead:
    try:
        run = await jobs.start(session)
    except ScrapeAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scrape is already running",
        ) from exc
    return run_to_read(run)


@router.get("/runs/{run_id}", response_model=ScrapeRunRead)
async def read_run(run_id: int, session: SessionDep, _: AdminDep) -> ScrapeRunRead:
    run = await get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scrape run not found")
    return run_to_read(run)
