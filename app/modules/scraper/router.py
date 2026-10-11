from fastapi import APIRouter, HTTPException, status

from app.api.deps import AdminDep, JobsDep, SessionDep
from app.modules.catalog.repository import get_run
from app.modules.catalog.schemas import ScrapeRunRead
from app.modules.scraper.jobs import ScrapeAlreadyRunning, run_to_read

router = APIRouter(prefix="/scrape", tags=["scrape"])


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
