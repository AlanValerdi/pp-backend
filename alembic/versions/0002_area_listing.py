"""Preserve source listings for each offer-area relationship."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "0002_area_listing"
down_revision = "0001_create_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("offer_areas", sa.Column("listing", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("offer_areas", "listing")
