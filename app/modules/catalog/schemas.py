from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

OfferKind = Literal["servicio_social", "practica_profesional"]
ProgramLevel = Literal["Lic", "Ing"]


class APIModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CatalogMeta(APIModel):
    source: str
    scraped_at: str
    schema_version: int


class Section(APIModel):
    id: str
    name: str
    order: int


class Faculty(APIModel):
    id: str
    name: str


class Area(APIModel):
    uuid: str
    slug: str
    name: str
    raw_name: str
    level: ProgramLevel
    section_id: str
    faculty_id: str
    offer_ids: list[str]


class OfferListing(APIModel):
    folio: str
    programa: str
    tipo: OfferKind
    area: str
    perfil_educativo: str
    coordinador: str
    curso_induccion: str
    empresa: str


class OfferSummary(APIModel):
    tipo: OfferKind
    program_number: str
    registered_at: str
    registered_at_raw: str
    company: str
    sector: str
    period: str
    revalidated: bool
    status: str


class OfferGeneral(APIModel):
    name: str
    program_type: str
    department: str
    start_date: str
    start_date_raw: str
    end_date: str
    end_date_raw: str
    duration_months: int


class OfferSupervisor(APIModel):
    name: str
    position: str
    email: str
    phone: str
    interview_address: str
    work_address: str


class OfferAppointment(APIModel):
    addressee: str
    position: str


class OfferProgramInfo(APIModel):
    monthly_stipend: str
    other_support: str
    social_axes: list[str]
    promotes_entrepreneurship: bool


class OfferAreaDetail(APIModel):
    area_uuid: str
    activities: str
    competencies: str
    listing: OfferListing | None = None


class Offer(APIModel):
    uuid: str
    listing: OfferListing
    summary: OfferSummary
    general: OfferGeneral
    supervisor: OfferSupervisor
    appointment: OfferAppointment
    program_info: OfferProgramInfo
    area_details: list[OfferAreaDetail]


class Catalog(APIModel):
    meta: CatalogMeta
    sections: list[Section]
    faculties: list[Faculty]
    areas: list[Area]
    offers: list[Offer]


class AreaPage(APIModel):
    area: Area
    offers: list[Offer]


class ScrapeRunRead(APIModel):
    id: int
    status: str
    started_at: str
    finished_at: str | None = None
    stats: dict = Field(default_factory=dict)
    error: str | None = None
