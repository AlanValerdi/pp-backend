from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import update
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import SCHEMA_VERSION, SOURCE_URL
from app.modules.catalog.models import AreaRow, FacultyRow, OfferAreaRow, OfferRow, SectionRow
from app.modules.catalog.schemas import (
    Area,
    Catalog,
    CatalogMeta,
    Faculty,
    Offer,
    OfferAppointment,
    OfferAreaDetail,
    OfferGeneral,
    OfferKind,
    OfferListing,
    OfferProgramInfo,
    OfferSummary,
    OfferSupervisor,
    ProgramLevel,
    Section,
)
from app.modules.scraper.classification import SECTIONS
from app.modules.scraper.models import ScrapeRun


async def create_run(session: AsyncSession) -> ScrapeRun:
    run = ScrapeRun(status="running", started_at=datetime.now(UTC), stats={})
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_run(session: AsyncSession, run_id: int) -> ScrapeRun | None:
    return await session.get(ScrapeRun, run_id)


async def finish_run(
    session: AsyncSession,
    run_id: int,
    status: str,
    stats: dict,
    error: str | None,
) -> None:
    run = await session.get(ScrapeRun, run_id)
    if run is None:
        return
    run.status = status
    run.finished_at = datetime.now(UTC)
    run.stats = stats
    run.error = error


async def save_catalog(
    session: AsyncSession, catalog: Catalog, run_id: int, *, deactivate_missing: bool = True
) -> None:
    for section in catalog.sections:
        await _merge_section(session, section)
    for faculty in catalog.faculties:
        await _merge_faculty(session, faculty)
    seen_areas: set[str] = set()
    for area in catalog.areas:
        seen_areas.add(area.uuid)
        await _merge_area(session, area)
    seen_offers: set[str] = set()
    for offer in catalog.offers:
        seen_offers.add(offer.uuid)
        await _merge_offer(session, offer, run_id)
        await session.flush()
        await _replace_links(session, offer)
    await session.flush()
    if not deactivate_missing:
        return
    area_update = update(AreaRow).values(is_active=False)
    offer_update = update(OfferRow).values(is_active=False)
    if seen_areas:
        area_update = area_update.where(col(AreaRow.uuid).not_in(seen_areas))
    if seen_offers:
        offer_update = offer_update.where(col(OfferRow.uuid).not_in(seen_offers))
    await session.execute(area_update)
    await session.execute(offer_update)


async def load_catalog(session: AsyncSession) -> Catalog:
    faculties = (await session.exec(select(FacultyRow).order_by(FacultyRow.name))).all()
    areas = (await session.exec(select(AreaRow).where(col(AreaRow.is_active).is_(True)))).all()
    offers = (await session.exec(select(OfferRow).where(col(OfferRow.is_active).is_(True)))).all()
    links = (await session.exec(select(OfferAreaRow))).all()
    links_by_offer: dict[str, list[OfferAreaRow]] = {}
    for link in links:
        links_by_offer.setdefault(link.offer_uuid, []).append(link)
    offer_models = [_offer_from_row(row, links_by_offer.get(row.uuid, [])) for row in offers]
    offer_ids_by_area: dict[str, list[str]] = {}
    active_offer_ids = {offer.uuid for offer in offer_models}
    for link in links:
        if link.offer_uuid in active_offer_ids:
            offer_ids_by_area.setdefault(link.area_uuid, []).append(link.offer_uuid)
    area_models = [
        Area(
            uuid=row.uuid,
            slug=row.slug,
            name=row.name,
            raw_name=row.raw_name,
            level=_level(row.level),
            section_id=row.section_id,
            faculty_id=row.faculty_id,
            offer_ids=sorted(offer_ids_by_area.get(row.uuid, [])),
        )
        for row in areas
    ]
    area_models.sort(key=lambda area: (area.section_id, area.name, area.level))
    referenced = {area.faculty_id for area in area_models}
    return Catalog(
        meta=CatalogMeta(
            source=SOURCE_URL,
            scraped_at=await _latest_scraped_at(session),
            schema_version=SCHEMA_VERSION,
        ),
        sections=[Section(id=item.id, name=item.name, order=item.order) for item in SECTIONS],
        faculties=[Faculty(id=row.id, name=row.name) for row in faculties if row.id in referenced],
        areas=area_models,
        offers=sorted(offer_models, key=lambda offer: offer.listing.folio),
    )


async def get_area_by_slug(session: AsyncSession, slug: str) -> AreaRow | None:
    result = await session.exec(select(AreaRow).where(AreaRow.slug == slug, col(AreaRow.is_active).is_(True)))
    return result.first()


async def offers_for_area(session: AsyncSession, area_uuid: str) -> list[Offer]:
    links = (await session.exec(select(OfferAreaRow).where(OfferAreaRow.area_uuid == area_uuid))).all()
    offers: list[Offer] = []
    for link in links:
        row = await session.get(OfferRow, link.offer_uuid)
        if row is None or not row.is_active:
            continue
        area_links = (
            await session.exec(select(OfferAreaRow).where(OfferAreaRow.offer_uuid == row.uuid))
        ).all()
        offer = _offer_from_row(row, area_links)
        if link.listing is not None:
            offer.listing = OfferListing.model_validate(link.listing)
        else:
            offer.listing = offer.listing.model_copy(update={"perfil_educativo": ""})
        offers.append(offer)
    offers.sort(key=lambda offer: offer.listing.folio)
    return offers


async def get_offer(session: AsyncSession, offer_uuid: str) -> Offer | None:
    row = await session.get(OfferRow, offer_uuid)
    if row is None or not row.is_active:
        return None
    links = (await session.exec(select(OfferAreaRow).where(OfferAreaRow.offer_uuid == offer_uuid))).all()
    return _offer_from_row(row, links)


async def _latest_scraped_at(session: AsyncSession) -> str:
    result = await session.exec(
        select(ScrapeRun).where(ScrapeRun.status == "succeeded").order_by(col(ScrapeRun.finished_at).desc())
    )
    run = result.first()
    if run is None or run.finished_at is None:
        return ""
    return run.finished_at.astimezone(UTC).isoformat().replace("+00:00", "Z")


async def _merge_section(session: AsyncSession, section: Section) -> None:
    row = await session.get(SectionRow, section.id)
    if row is None:
        session.add(SectionRow(id=section.id, name=section.name, order=section.order))
        return
    row.name = section.name
    row.order = section.order


async def _merge_faculty(session: AsyncSession, faculty: Faculty) -> None:
    row = await session.get(FacultyRow, faculty.id)
    if row is None:
        session.add(FacultyRow(id=faculty.id, name=faculty.name))
        return
    row.name = faculty.name


async def _merge_area(session: AsyncSession, area: Area) -> None:
    row = await session.get(AreaRow, area.uuid)
    if row is None:
        session.add(
            AreaRow(
                uuid=area.uuid,
                slug=area.slug,
                name=area.name,
                raw_name=area.raw_name,
                level=area.level,
                section_id=area.section_id,
                faculty_id=area.faculty_id,
                is_active=True,
            )
        )
        return
    row.slug = area.slug
    row.name = area.name
    row.raw_name = area.raw_name
    row.level = area.level
    row.section_id = area.section_id
    row.faculty_id = area.faculty_id
    row.is_active = True


async def _merge_offer(session: AsyncSession, offer: Offer, run_id: int) -> None:
    values = _offer_values(offer)
    row = await session.get(OfferRow, offer.uuid)
    if row is None:
        session.add(
            OfferRow(
                uuid=offer.uuid,
                folio=offer.listing.folio,
                is_active=True,
                last_seen_run_id=run_id,
                **values,
            )
        )
        return
    row.folio = offer.listing.folio
    row.is_active = True
    row.last_seen_run_id = run_id
    for key, value in values.items():
        setattr(row, key, value)


async def _replace_links(session: AsyncSession, offer: Offer) -> None:
    existing = (await session.exec(select(OfferAreaRow).where(OfferAreaRow.offer_uuid == offer.uuid))).all()
    for link in existing:
        await session.delete(link)
    await session.flush()
    for detail in offer.area_details:
        session.add(
            OfferAreaRow(
                offer_uuid=offer.uuid,
                area_uuid=detail.area_uuid,
                activities=detail.activities,
                competencies=detail.competencies,
                listing=detail.listing.model_dump() if detail.listing is not None else None,
            )
        )


def _offer_values(offer: Offer) -> dict:
    return {
        "listing_programa": offer.listing.programa,
        "listing_tipo": offer.listing.tipo,
        "listing_area": offer.listing.area,
        "listing_perfil_educativo": offer.listing.perfil_educativo,
        "listing_coordinador": offer.listing.coordinador,
        "listing_curso_induccion": offer.listing.curso_induccion,
        "listing_empresa": offer.listing.empresa,
        "summary_tipo": offer.summary.tipo,
        "summary_program_number": offer.summary.program_number,
        "summary_registered_at": offer.summary.registered_at,
        "summary_registered_at_raw": offer.summary.registered_at_raw,
        "summary_company": offer.summary.company,
        "summary_sector": offer.summary.sector,
        "summary_period": offer.summary.period,
        "summary_revalidated": offer.summary.revalidated,
        "summary_status": offer.summary.status,
        "general_name": offer.general.name,
        "general_program_type": offer.general.program_type,
        "general_department": offer.general.department,
        "general_start_date": offer.general.start_date,
        "general_start_date_raw": offer.general.start_date_raw,
        "general_end_date": offer.general.end_date,
        "general_end_date_raw": offer.general.end_date_raw,
        "general_duration_months": offer.general.duration_months,
        "supervisor_name": offer.supervisor.name,
        "supervisor_position": offer.supervisor.position,
        "supervisor_email": offer.supervisor.email,
        "supervisor_phone": offer.supervisor.phone,
        "supervisor_interview_address": offer.supervisor.interview_address,
        "supervisor_work_address": offer.supervisor.work_address,
        "appointment_addressee": offer.appointment.addressee,
        "appointment_position": offer.appointment.position,
        "program_info_monthly_stipend": offer.program_info.monthly_stipend,
        "program_info_other_support": offer.program_info.other_support,
        "program_info_social_axes": list(offer.program_info.social_axes),
        "program_info_promotes_entrepreneurship": offer.program_info.promotes_entrepreneurship,
    }


def _offer_from_row(row: OfferRow, links: Sequence[OfferAreaRow]) -> Offer:
    return Offer(
        uuid=row.uuid,
        listing=OfferListing(
            folio=row.folio,
            programa=row.listing_programa,
            tipo=_kind(row.listing_tipo),
            area=row.listing_area,
            perfil_educativo=row.listing_perfil_educativo,
            coordinador=row.listing_coordinador,
            curso_induccion=row.listing_curso_induccion,
            empresa=row.listing_empresa,
        ),
        summary=OfferSummary(
            tipo=_kind(row.summary_tipo),
            program_number=row.summary_program_number,
            registered_at=row.summary_registered_at,
            registered_at_raw=row.summary_registered_at_raw,
            company=row.summary_company,
            sector=row.summary_sector,
            period=row.summary_period,
            revalidated=row.summary_revalidated,
            status=row.summary_status,
        ),
        general=OfferGeneral(
            name=row.general_name,
            program_type=row.general_program_type,
            department=row.general_department,
            start_date=row.general_start_date,
            start_date_raw=row.general_start_date_raw,
            end_date=row.general_end_date,
            end_date_raw=row.general_end_date_raw,
            duration_months=row.general_duration_months,
        ),
        supervisor=OfferSupervisor(
            name=row.supervisor_name,
            position=row.supervisor_position,
            email=row.supervisor_email,
            phone=row.supervisor_phone,
            interview_address=row.supervisor_interview_address,
            work_address=row.supervisor_work_address,
        ),
        appointment=OfferAppointment(
            addressee=row.appointment_addressee,
            position=row.appointment_position,
        ),
        program_info=OfferProgramInfo(
            monthly_stipend=row.program_info_monthly_stipend,
            other_support=row.program_info_other_support,
            social_axes=list(row.program_info_social_axes or []),
            promotes_entrepreneurship=row.program_info_promotes_entrepreneurship,
        ),
        area_details=sorted(
            (
                OfferAreaDetail(
                    area_uuid=link.area_uuid,
                    activities=link.activities,
                    competencies=link.competencies,
                    listing=OfferListing.model_validate(link.listing) if link.listing is not None else None,
                )
                for link in links
            ),
            key=lambda item: item.area_uuid,
        ),
    )


def _kind(value: str) -> OfferKind:
    if value == "practica_profesional":
        return "practica_profesional"
    return "servicio_social"


def _level(value: str) -> ProgramLevel:
    if value == "Ing":
        return "Ing"
    return "Lic"
