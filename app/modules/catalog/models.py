from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.elements import quoted_name
from sqlmodel import Field, SQLModel

from app.core.db import NAMING_CONVENTION

SQLModel.metadata.naming_convention = NAMING_CONVENTION


class SectionRow(SQLModel, table=True):
    __tablename__ = "sections"

    id: str = Field(primary_key=True)
    name: str = Field(sa_column=Column(Text, nullable=False))
    order: int = Field(sa_column=Column(quoted_name("order", True), Integer, nullable=False))


class FacultyRow(SQLModel, table=True):
    __tablename__ = "faculties"

    id: str = Field(primary_key=True)
    name: str = Field(sa_column=Column(Text, nullable=False))


class AreaRow(SQLModel, table=True):
    __tablename__ = "areas"

    uuid: str = Field(primary_key=True)
    slug: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    name: str = Field(sa_column=Column(Text, nullable=False))
    raw_name: str = Field(sa_column=Column(Text, nullable=False))
    level: str = Field(sa_column=Column(Text, nullable=False))
    section_id: str = Field(foreign_key="sections.id")
    faculty_id: str = Field(foreign_key="faculties.id")
    is_active: bool = Field(default=True)


class OfferRow(SQLModel, table=True):
    __tablename__ = "offers"

    uuid: str = Field(primary_key=True)
    folio: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    is_active: bool = Field(default=True)
    last_seen_run_id: int | None = Field(default=None, foreign_key="scrape_runs.id")

    listing_programa: str = Field(sa_column=Column(Text, nullable=False))
    listing_tipo: str = Field(sa_column=Column(Text, nullable=False))
    listing_area: str = Field(sa_column=Column(Text, nullable=False))
    listing_perfil_educativo: str = Field(sa_column=Column(Text, nullable=False))
    listing_coordinador: str = Field(sa_column=Column(Text, nullable=False))
    listing_curso_induccion: str = Field(sa_column=Column(Text, nullable=False))
    listing_empresa: str = Field(sa_column=Column(Text, nullable=False))

    summary_tipo: str = Field(sa_column=Column(Text, nullable=False))
    summary_program_number: str = Field(sa_column=Column(Text, nullable=False))
    summary_registered_at: str = Field(sa_column=Column(Text, nullable=False))
    summary_registered_at_raw: str = Field(sa_column=Column(Text, nullable=False))
    summary_company: str = Field(sa_column=Column(Text, nullable=False))
    summary_sector: str = Field(sa_column=Column(Text, nullable=False))
    summary_period: str = Field(sa_column=Column(Text, nullable=False))
    summary_revalidated: bool = Field(default=False)
    summary_status: str = Field(sa_column=Column(Text, nullable=False))

    general_name: str = Field(sa_column=Column(Text, nullable=False))
    general_program_type: str = Field(sa_column=Column(Text, nullable=False))
    general_department: str = Field(sa_column=Column(Text, nullable=False))
    general_start_date: str = Field(sa_column=Column(Text, nullable=False))
    general_start_date_raw: str = Field(sa_column=Column(Text, nullable=False))
    general_end_date: str = Field(sa_column=Column(Text, nullable=False))
    general_end_date_raw: str = Field(sa_column=Column(Text, nullable=False))
    general_duration_months: int = Field(default=0)

    supervisor_name: str = Field(sa_column=Column(Text, nullable=False))
    supervisor_position: str = Field(sa_column=Column(Text, nullable=False))
    supervisor_email: str = Field(sa_column=Column(Text, nullable=False))
    supervisor_phone: str = Field(sa_column=Column(Text, nullable=False))
    supervisor_interview_address: str = Field(sa_column=Column(Text, nullable=False))
    supervisor_work_address: str = Field(sa_column=Column(Text, nullable=False))

    appointment_addressee: str = Field(sa_column=Column(Text, nullable=False))
    appointment_position: str = Field(sa_column=Column(Text, nullable=False))

    program_info_monthly_stipend: str = Field(sa_column=Column(Text, nullable=False))
    program_info_other_support: str = Field(sa_column=Column(Text, nullable=False))
    program_info_social_axes: list[str] = Field(
        default_factory=list,
        sa_column=Column(ARRAY(Text), nullable=False),
    )
    program_info_promotes_entrepreneurship: bool = Field(default=False)


class OfferAreaRow(SQLModel, table=True):
    __tablename__ = "offer_areas"

    offer_uuid: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("offers.uuid", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    area_uuid: str = Field(
        sa_column=Column(
            Text,
            ForeignKey("areas.uuid", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    activities: str = Field(default="", sa_column=Column(Text, nullable=False))
    competencies: str = Field(default="", sa_column=Column(Text, nullable=False))
