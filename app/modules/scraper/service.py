import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import SCHEMA_VERSION, SOURCE_URL
from app.modules.catalog.schemas import (
    Area,
    Catalog,
    CatalogMeta,
    Faculty,
    Offer,
    OfferAppointment,
    OfferAreaDetail,
    OfferGeneral,
    OfferListing,
    OfferProgramInfo,
    OfferSummary,
    OfferSupervisor,
    ProgramLevel,
)
from app.modules.scraper.classification import (
    SECTIONS,
    UNKNOWN_FACULTY_ID,
    UNKNOWN_FACULTY_NAME,
    faculty_identity,
    known_unprefixed,
    looks_official,
    section_for,
)
from app.modules.scraper.client import SiiaaClient
from app.modules.scraper.normalize import (
    ParsedArea,
    area_uuid,
    fold,
    levels_in_text,
    offer_kind,
    offer_uuid,
    parse_career_name,
    unprefixed_area,
)
from app.modules.scraper.parsers import parse_careers, parse_detail, parse_listing
from app.modules.scraper.parsers.detail import AreaBlock, ParsedDetail
from app.modules.scraper.parsers.listing import ListingRow
from app.modules.scraper.tracing import DetailProgress, event

logger = logging.getLogger(__name__)


class IncompleteScrape(Exception):
    pass


def require_complete(stats: dict) -> None:
    if stats.get("listingErrors", 0) or stats.get("detailErrors", 0):
        raise IncompleteScrape(f"Incomplete scrape: {stats}")


@dataclass
class AreaDraft:
    uuid: str
    slug: str
    name: str
    raw_name: str
    level: ProgramLevel
    section_id: str
    faculty_raw: str | None = None
    offer_ids: set[str] = field(default_factory=set)


@dataclass
class OfferDraft:
    uuid: str
    listing: OfferListing
    summary: OfferSummary | None = None
    general: OfferGeneral | None = None
    supervisor: OfferSupervisor | None = None
    appointment: OfferAppointment | None = None
    program_info: OfferProgramInfo | None = None
    area_details: dict[str, OfferAreaDetail] = field(default_factory=dict)
    fetches: dict[str, tuple[str, str, str]] = field(default_factory=dict)


class ScraperService:
    def __init__(self, client: SiiaaClient) -> None:
        self.client = client

    async def collect(
        self, limit_careers: int | None = None, limit_offers: int | None = None
    ) -> tuple[Catalog, dict]:
        if limit_offers is not None and limit_offers < 1:
            raise ValueError("limit_offers must be positive")
        if limit_careers is not None and limit_careers < 1:
            raise ValueError("limit_careers must be positive")
        event(logger, "careers_started")
        careers = parse_careers(await self.client.get_careers_html())
        if limit_careers is not None:
            careers = careers[:limit_careers]
        event(logger, "careers_parsed", count=len(careers))

        areas: dict[tuple[str, str], AreaDraft] = {}
        offers: dict[str, OfferDraft] = {}
        stats = {
            "careers": len(careers),
            "listingErrors": 0,
            "rows": 0,
            "details": 0,
            "detailErrors": 0,
        }

        event(logger, "listings_started", total=len(careers))
        listings = await asyncio.gather(
            *(self._load_listing(career.name, career.un, career.se) for career in careers)
        )
        for career_name, rows, error in listings:
            if error is not None:
                stats["listingErrors"] += 1
            stats["rows"] += len(rows)
            self._absorb_career(career_name, rows, areas, offers)
        event(logger, "listings_completed", rows=stats["rows"], failed=stats["listingErrors"])

        if limit_offers is not None:
            stats["limitOffers"] = limit_offers
            offers = dict(list(offers.items())[:limit_offers])
            selected_ids = {offer.uuid for offer in offers.values()}
            for area in areas.values():
                area.offer_ids.intersection_update(selected_ids)
            areas = {key: area for key, area in areas.items() if area.offer_ids}

        jobs: list[tuple[OfferDraft, str, str, str, str]] = []
        for offer in offers.values():
            for area_id, (v_01, ca, perfil) in offer.fetches.items():
                jobs.append((offer, area_id, v_01, ca, perfil))
        progress = DetailProgress(logger, len(jobs))

        async def load_detail(offer, area_id, v_01, ca):
            detail, error = await self._load_detail(offer.listing.folio, v_01, ca)
            event(
                logger,
                "detail_parsed" if error is None else "detail_failed",
                logging.DEBUG if error is None else logging.ERROR,
                folio=offer.listing.folio,
                area_id=area_id,
                error_type=type(error).__name__ if error else None,
            )
            progress.complete(detail is not None and error is None)
            return detail, error

        details = await asyncio.gather(
            *(load_detail(offer, area_id, v_01, ca) for offer, area_id, v_01, ca, _ in jobs)
        )
        event(logger, "details_completed", parsed=progress.parsed, failed=progress.failed)
        event(logger, "normalization_started")
        for (offer, area_id, _v_01, _ca, perfil), (detail, error) in zip(jobs, details, strict=True):
            if error is not None or detail is None:
                stats["detailErrors"] += 1
                self._ensure_area_detail(offer, area_id)
                continue
            stats["details"] += 1
            self._apply_detail(offer, area_id, perfil, detail, areas)
            event(logger, "detail_normalized", logging.DEBUG, folio=offer.listing.folio, area_id=area_id)

        for offer in offers.values():
            for area_id in offer.fetches:
                self._ensure_area_detail(offer, area_id)

        catalog = _build_catalog(areas, offers)
        stats["offers"] = len(catalog.offers)
        stats["areas"] = len(catalog.areas)
        event(logger, "normalization_completed", offers=len(catalog.offers), areas=len(catalog.areas))
        return catalog, stats

    async def _load_listing(
        self, career_name: str, un: str, se: str
    ) -> tuple[str, list[ListingRow], Exception | None]:
        try:
            html = await self.client.post_text("Ss_OFERTA_prog", {"un": un, "se": se})
            rows = parse_listing(html)
            event(logger, "listing_parsed", career=career_name, rows=len(rows))
            return career_name, rows, None
        except Exception as exc:
            event(logger, "listing_failed", logging.ERROR, career=career_name, error_type=type(exc).__name__)
            return career_name, [], exc

    async def _load_detail(
        self, folio: str, v_01: str, ca: str
    ) -> tuple[ParsedDetail | None, Exception | None]:
        try:
            html = await self.client.post_text("Ss_OFERTA_CAR_PROG", {"v_01": v_01, "ca": ca})
            return parse_detail(html), None
        except Exception as exc:
            event(
                logger,
                "detail_parse_or_fetch_failed",
                logging.ERROR,
                folio=folio,
                error_type=type(exc).__name__,
            )
            return None, exc

    def _absorb_career(
        self,
        career_name: str,
        rows: list[ListingRow],
        areas: dict[tuple[str, str], AreaDraft],
        offers: dict[str, OfferDraft],
    ) -> None:
        parsed_areas = _areas_for_career(career_name, rows)
        if not parsed_areas:
            logger.warning("omitiendo carrera sin nivel: %s", career_name)
            return
        drafts = []
        for parsed in parsed_areas:
            key = (parsed.level, fold(parsed.name))
            draft = areas.get(key)
            if draft is None:
                draft = AreaDraft(
                    uuid=area_uuid(parsed.level, parsed.name),
                    slug=parsed.slug,
                    name=parsed.name,
                    raw_name=parsed.raw_name,
                    level=parsed.level,
                    section_id=section_for(parsed.level, parsed.name),
                )
                areas[key] = draft
            drafts.append(draft)
        available = [item.level for item in parsed_areas]
        for row in rows:
            offer = offers.get(row.folio)
            if offer is None:
                offer = OfferDraft(uuid=offer_uuid(row.folio), listing=_listing(row))
                offers[row.folio] = offer
            for level in _target_levels(row.perfil_educativo, available):
                draft = next(item for item in drafts if item.level == level)
                draft.offer_ids.add(offer.uuid)
                offer.area_details.setdefault(
                    draft.uuid,
                    OfferAreaDetail(
                        area_uuid=draft.uuid, activities="", competencies="", listing=_listing(row)
                    ),
                )
                if draft.uuid not in offer.fetches and row.v_01:
                    offer.fetches[draft.uuid] = (row.v_01, row.ca, row.perfil_educativo)

    def _apply_detail(
        self,
        offer: OfferDraft,
        area_id: str,
        perfil: str,
        detail: ParsedDetail,
        areas: dict[tuple[str, str], AreaDraft],
    ) -> None:
        if offer.summary is None:
            offer.summary = _summary(offer.listing, detail)
            offer.general = _general(offer.listing, detail)
            offer.supervisor = _supervisor(detail)
            offer.appointment = _appointment(detail)
            offer.program_info = _program_info(detail)
        block = _pick_block(detail.blocks, _area_name_for(area_id, areas))
        offer.area_details[area_id] = OfferAreaDetail(
            area_uuid=area_id,
            activities=block.activities if block else "",
            competencies=block.competencies if block else "",
            listing=offer.area_details[area_id].listing,
        )
        faculty = _choose_faculty(detail, perfil)
        if faculty:
            _assign_faculty(_area_by_id(areas, area_id), faculty)

    def _ensure_area_detail(self, offer: OfferDraft, area_id: str) -> None:
        offer.area_details.setdefault(
            area_id,
            OfferAreaDetail(area_uuid=area_id, activities="", competencies=""),
        )


def _areas_for_career(career_name: str, rows: list[ListingRow]) -> list[ParsedArea]:
    parsed = parse_career_name(career_name)
    if parsed:
        return parsed
    found: list[ProgramLevel] = []
    for row in rows:
        for level in levels_in_text(row.perfil_educativo):
            if level not in found:
                found.append(level)
    if not found and rows:
        logger.warning("perfil sin nivel, se asume Lic: %s", career_name)
        found = ["Lic"]
    if not found and known_unprefixed(career_name):
        found = ["Lic"]
    return [unprefixed_area(level, career_name) for level in found]


def _target_levels(perfil: str, available: list[ProgramLevel]) -> list[ProgramLevel]:
    found = levels_in_text(perfil)
    if not found:
        if available == ["Lic", "Ing"]:
            return ["Lic"]
        return list(available)
    matched = [level for level in found if level in available]
    return matched or list(available)


def _listing(row: ListingRow) -> OfferListing:
    return OfferListing(
        folio=row.folio,
        programa=row.programa,
        tipo=offer_kind(row.tipo),
        area=row.area,
        perfil_educativo=row.perfil_educativo,
        coordinador=row.coordinador,
        curso_induccion=row.curso_induccion,
        empresa=row.empresa,
    )


def _summary(listing: OfferListing, detail: ParsedDetail) -> OfferSummary:
    return OfferSummary(
        tipo=offer_kind(detail.tipo) if detail.tipo else listing.tipo,
        program_number=detail.program_number or listing.folio,
        registered_at=detail.registered_at,
        registered_at_raw=detail.registered_at_raw,
        company=detail.company or listing.empresa,
        sector=detail.sector,
        period=detail.period,
        revalidated=detail.revalidated,
        status=detail.status,
    )


def _general(listing: OfferListing, detail: ParsedDetail) -> OfferGeneral:
    return OfferGeneral(
        name=detail.name or listing.programa,
        program_type=detail.program_type,
        department=detail.department,
        start_date=detail.start_date,
        start_date_raw=detail.start_date_raw,
        end_date=detail.end_date,
        end_date_raw=detail.end_date_raw,
        duration_months=detail.duration_months,
    )


def _supervisor(detail: ParsedDetail) -> OfferSupervisor:
    return OfferSupervisor(
        name=detail.supervisor_name,
        position=detail.supervisor_position,
        email=detail.email,
        phone=detail.phone,
        interview_address=detail.interview_address,
        work_address=detail.work_address,
    )


def _appointment(detail: ParsedDetail) -> OfferAppointment:
    return OfferAppointment(addressee=detail.addressee, position=detail.appointment_position)


def _program_info(detail: ParsedDetail) -> OfferProgramInfo:
    return OfferProgramInfo(
        monthly_stipend=detail.monthly_stipend,
        other_support=detail.other_support,
        social_axes=detail.social_axes,
        promotes_entrepreneurship=detail.promotes_entrepreneurship,
    )


def _pick_block(blocks: list[AreaBlock], area_name: str) -> AreaBlock | None:
    if not blocks:
        return None
    if len(blocks) == 1:
        return blocks[0]
    target = fold(area_name)
    for block in blocks:
        block_name = fold(block.name)
        if block_name == target or target in block_name or block_name in target:
            return block
    return blocks[0]


def _choose_faculty(detail: ParsedDetail, perfil: str) -> str:
    if not detail.faculties:
        return ""
    folded = fold(perfil)
    for row in detail.faculties:
        row_perfil = fold(row.perfil)
        if row_perfil and (row_perfil in folded or folded in row_perfil):
            return row.faculty
    for row in detail.faculties:
        if looks_official(row.faculty):
            return row.faculty
    return detail.faculties[0].faculty


def _assign_faculty(area: AreaDraft | None, raw: str) -> None:
    if area is None or not raw:
        return
    if area.faculty_raw is None:
        area.faculty_raw = raw
        return
    if looks_official(area.faculty_raw):
        return
    if looks_official(raw):
        area.faculty_raw = raw


def _area_by_id(areas: dict[tuple[str, str], AreaDraft], area_id: str) -> AreaDraft | None:
    return next((area for area in areas.values() if area.uuid == area_id), None)


def _area_name_for(area_id: str, areas: dict[tuple[str, str], AreaDraft]) -> str:
    area = _area_by_id(areas, area_id)
    return area.name if area else ""


def _build_catalog(areas: dict[tuple[str, str], AreaDraft], offers: dict[str, OfferDraft]) -> Catalog:
    faculties: dict[str, str] = {}
    area_models: list[Area] = []
    used_slugs: set[str] = set()
    section_order = {section.id: section.order for section in SECTIONS}
    ordered = sorted(
        areas.values(),
        key=lambda area: (section_order.get(area.section_id, 99), fold(area.name), area.level),
    )
    for draft in ordered:
        if draft.faculty_raw:
            faculty_id, faculty_name = faculty_identity(draft.faculty_raw)
        else:
            faculty_id, faculty_name = UNKNOWN_FACULTY_ID, UNKNOWN_FACULTY_NAME
        faculties[faculty_id] = faculty_name
        slug = _unique_slug(draft.slug, used_slugs)
        area_models.append(
            Area(
                uuid=draft.uuid,
                slug=slug,
                name=draft.name,
                raw_name=draft.raw_name,
                level=draft.level,
                section_id=draft.section_id,
                faculty_id=faculty_id,
                offer_ids=sorted(draft.offer_ids),
            )
        )
    offer_models = [_finalize(offer) for _, offer in sorted(offers.items())]
    scraped_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return Catalog(
        meta=CatalogMeta(source=SOURCE_URL, scraped_at=scraped_at, schema_version=SCHEMA_VERSION),
        sections=list(SECTIONS),
        faculties=sorted(
            (Faculty(id=faculty_id, name=name) for faculty_id, name in faculties.items()),
            key=lambda faculty: faculty.name,
        ),
        areas=area_models,
        offers=offer_models,
    )


def _unique_slug(slug: str, used: set[str]) -> str:
    if slug not in used:
        used.add(slug)
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in used:
        suffix += 1
    unique = f"{slug}-{suffix}"
    used.add(unique)
    return unique


def _finalize(offer: OfferDraft) -> Offer:
    listing = offer.listing
    summary = offer.summary or OfferSummary(
        tipo=listing.tipo,
        program_number=listing.folio,
        registered_at="",
        registered_at_raw="",
        company=listing.empresa,
        sector="",
        period="",
        revalidated=False,
        status="",
    )
    general = offer.general or OfferGeneral(
        name=listing.programa,
        program_type="",
        department="",
        start_date="",
        start_date_raw="",
        end_date="",
        end_date_raw="",
        duration_months=0,
    )
    supervisor = offer.supervisor or OfferSupervisor(
        name="",
        position="",
        email="",
        phone="",
        interview_address="",
        work_address="",
    )
    appointment = offer.appointment or OfferAppointment(addressee="", position="")
    program_info = offer.program_info or OfferProgramInfo(
        monthly_stipend="",
        other_support="",
        social_axes=[],
        promotes_entrepreneurship=False,
    )
    return Offer(
        uuid=offer.uuid,
        listing=listing,
        summary=summary,
        general=general,
        supervisor=supervisor,
        appointment=appointment,
        program_info=program_info,
        area_details=sorted(offer.area_details.values(), key=lambda item: item.area_uuid),
    )
