"""create catalog tables

Revision ID: 0001_create_catalog
Revises:
Create Date: 2026-10-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_create_catalog"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "faculties",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_faculties"),
    )
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_scrape_runs"),
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sections"),
    )
    op.create_table(
        "areas",
        sa.Column("uuid", sa.String(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.Column("level", sa.Text(), nullable=False),
        sa.Column("section_id", sa.String(), nullable=False),
        sa.Column("faculty_id", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["faculty_id"],
            ["faculties.id"],
            name="fk_areas_faculty_id_faculties",
        ),
        sa.ForeignKeyConstraint(
            ["section_id"],
            ["sections.id"],
            name="fk_areas_section_id_sections",
        ),
        sa.PrimaryKeyConstraint("uuid", name="pk_areas"),
        sa.UniqueConstraint("slug", name="uq_areas_slug"),
    )
    op.create_table(
        "offers",
        sa.Column("uuid", sa.String(), nullable=False),
        sa.Column("folio", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_seen_run_id", sa.Integer(), nullable=True),
        sa.Column("listing_programa", sa.Text(), nullable=False),
        sa.Column("listing_tipo", sa.Text(), nullable=False),
        sa.Column("listing_area", sa.Text(), nullable=False),
        sa.Column("listing_perfil_educativo", sa.Text(), nullable=False),
        sa.Column("listing_coordinador", sa.Text(), nullable=False),
        sa.Column("listing_curso_induccion", sa.Text(), nullable=False),
        sa.Column("listing_empresa", sa.Text(), nullable=False),
        sa.Column("summary_tipo", sa.Text(), nullable=False),
        sa.Column("summary_program_number", sa.Text(), nullable=False),
        sa.Column("summary_registered_at", sa.Text(), nullable=False),
        sa.Column("summary_registered_at_raw", sa.Text(), nullable=False),
        sa.Column("summary_company", sa.Text(), nullable=False),
        sa.Column("summary_sector", sa.Text(), nullable=False),
        sa.Column("summary_period", sa.Text(), nullable=False),
        sa.Column("summary_revalidated", sa.Boolean(), nullable=False),
        sa.Column("summary_status", sa.Text(), nullable=False),
        sa.Column("general_name", sa.Text(), nullable=False),
        sa.Column("general_program_type", sa.Text(), nullable=False),
        sa.Column("general_department", sa.Text(), nullable=False),
        sa.Column("general_start_date", sa.Text(), nullable=False),
        sa.Column("general_start_date_raw", sa.Text(), nullable=False),
        sa.Column("general_end_date", sa.Text(), nullable=False),
        sa.Column("general_end_date_raw", sa.Text(), nullable=False),
        sa.Column("general_duration_months", sa.Integer(), nullable=False),
        sa.Column("supervisor_name", sa.Text(), nullable=False),
        sa.Column("supervisor_position", sa.Text(), nullable=False),
        sa.Column("supervisor_email", sa.Text(), nullable=False),
        sa.Column("supervisor_phone", sa.Text(), nullable=False),
        sa.Column("supervisor_interview_address", sa.Text(), nullable=False),
        sa.Column("supervisor_work_address", sa.Text(), nullable=False),
        sa.Column("appointment_addressee", sa.Text(), nullable=False),
        sa.Column("appointment_position", sa.Text(), nullable=False),
        sa.Column("program_info_monthly_stipend", sa.Text(), nullable=False),
        sa.Column("program_info_other_support", sa.Text(), nullable=False),
        sa.Column("program_info_social_axes", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("program_info_promotes_entrepreneurship", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["last_seen_run_id"],
            ["scrape_runs.id"],
            name="fk_offers_last_seen_run_id_scrape_runs",
        ),
        sa.PrimaryKeyConstraint("uuid", name="pk_offers"),
        sa.UniqueConstraint("folio", name="uq_offers_folio"),
    )
    op.create_table(
        "offer_areas",
        sa.Column("offer_uuid", sa.Text(), nullable=False),
        sa.Column("area_uuid", sa.Text(), nullable=False),
        sa.Column("activities", sa.Text(), nullable=False),
        sa.Column("competencies", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["area_uuid"],
            ["areas.uuid"],
            name="fk_offer_areas_area_uuid_areas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_uuid"],
            ["offers.uuid"],
            name="fk_offer_areas_offer_uuid_offers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("offer_uuid", "area_uuid", name="pk_offer_areas"),
    )


def downgrade() -> None:
    op.drop_table("offer_areas")
    op.drop_table("offers")
    op.drop_table("areas")
    op.drop_table("sections")
    op.drop_table("scrape_runs")
    op.drop_table("faculties")
