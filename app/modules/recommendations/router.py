from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile

from app.api.deps import BrowserRequestDep, CurrentUserDep, SessionDep
from app.modules.recommendations.errors import RecommendationError
from app.modules.recommendations.schemas import RecommendationAnalysis
from app.modules.recommendations.service import MAX_CV_BYTES, analyze_cv

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/analyze", response_model=RecommendationAnalysis)
async def analyze(
    response: Response,
    session: SessionDep,
    current_user: CurrentUserDep,
    browser_request: BrowserRequestDep,
    cv: Annotated[UploadFile, File()],
    area_slug: Annotated[str, Form(alias="areaSlug", min_length=1, max_length=200)],
) -> RecommendationAnalysis:
    response.headers["Cache-Control"] = "no-store"
    try:
        if cv.content_type not in {"application/pdf", "application/octet-stream"}:
            raise RecommendationError(422, "Selecciona un archivo PDF.")
        pdf = await cv.read(MAX_CV_BYTES + 1)
        return await analyze_cv(session, area_slug=area_slug, pdf=pdf)
    except RecommendationError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.message, headers={"Cache-Control": "no-store"}
        ) from None
    finally:
        await cv.close()
