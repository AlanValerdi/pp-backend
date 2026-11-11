import io

from pypdf import PdfReader
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.integrations.gemini import analyze_with_gemini
from app.modules.catalog.schemas import AreaPage
from app.modules.catalog.service import read_area
from app.modules.recommendations.errors import RecommendationError
from app.modules.recommendations.schemas import RecommendationAnalysis, RecommendedOffer

MAX_CV_BYTES = 10 * 1024 * 1024


def validate_pdf(pdf: bytes) -> None:
    if not pdf:
        raise RecommendationError(422, "El PDF está vacío. Selecciona otro archivo.")
    if len(pdf) > MAX_CV_BYTES:
        raise RecommendationError(413, "El PDF supera los 10 MB.")
    if not pdf.lstrip().startswith(b"%PDF-"):
        raise RecommendationError(422, "El archivo no es un PDF válido.")
    try:
        reader = PdfReader(io.BytesIO(pdf), strict=True)
        if reader.is_encrypted:
            raise RecommendationError(422, "El PDF está protegido. Utiliza un PDF sin contraseña.")
        if not reader.pages:
            raise RecommendationError(422, "El PDF no contiene páginas.")
    except RecommendationError:
        raise
    except Exception:
        raise RecommendationError(422, "El PDF está dañado o no se puede leer.") from None


def candidate_data(page: AreaPage) -> list[dict]:
    result = []
    for offer in page.offers:
        detail = next((item for item in offer.area_details if item.area_uuid == page.area.uuid), None)
        if detail is None:
            continue
        result.append(
            {
                "offer_id": offer.uuid,
                "title": offer.listing.programa,
                "type": offer.listing.tipo,
                "educational_profile": offer.listing.perfil_educativo,
                "activities": detail.activities,
                "competencies": detail.competencies,
            }
        )
    return result


async def analyze_cv(session: AsyncSession, *, area_slug: str, pdf: bytes) -> RecommendationAnalysis:
    await run_in_threadpool(validate_pdf, pdf)
    page = await read_area(session, area_slug)
    if page is None:
        raise RecommendationError(404, "La carrera seleccionada no está disponible.")
    candidates = candidate_data(page)
    if not candidates:
        return RecommendationAnalysis(
            profile=None, recommendations=[], message="No hay ofertas activas para esta carrera."
        )
    analysis = await analyze_with_gemini(
        pdf, career=f"{page.area.level}. {page.area.name}", candidates=candidates
    )
    if not analysis.cv_readable:
        raise RecommendationError(422, "No se encontró un CV legible con información profesional en el PDF.")
    allowed_ids = {item["offer_id"] for item in candidates}
    ids = [item.offer_id for item in analysis.choices]
    if len(ids) != len(set(ids)) or any(item not in allowed_ids for item in ids):
        raise RecommendationError(502, "Gemini devolvió ofertas inválidas. Intenta nuevamente.")
    offers = {offer.uuid: offer for offer in page.offers}
    recommendations = []
    for choice in analysis.choices:
        offer = offers[choice.offer_id]
        recommendations.append(
            RecommendedOffer(
                offer_uuid=offer.uuid,
                area_slug=page.area.slug,
                title=offer.listing.programa,
                folio=offer.listing.folio,
                remuneration=offer.program_info.monthly_stipend,
                reason=choice.reason,
                supervisor_email=offer.supervisor.email,
                work_address=offer.supervisor.work_address,
            )
        )
    return RecommendationAnalysis(
        profile=analysis.profile,
        recommendations=recommendations,
        message=None
        if recommendations
        else "No se encontraron ofertas con afinidad suficiente para este CV.",
    )
