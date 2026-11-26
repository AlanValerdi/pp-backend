"""add approximate geocoding status

Revision ID: f3b8d2a6c715
Revises: e7a1c3b94d20
Create Date: 2026-11-26 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

revision: str = 'f3b8d2a6c715'
down_revision: str | Sequence[str] | None = 'e7a1c3b94d20'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = 'ck_geocoded_addresses_status_valid'


def upgrade() -> None:
    op.drop_constraint(op.f(CONSTRAINT), 'geocoded_addresses', type_='check')
    op.create_check_constraint(
        op.f(CONSTRAINT),
        'geocoded_addresses',
        "status in ('pending', 'ok', 'approximate', 'not_found', 'manual', 'virtual')",
    )


def downgrade() -> None:
    op.execute("update geocoded_addresses set status = 'not_found', lat = null, lng = null, "
               "source = null where status = 'approximate'")
    op.drop_constraint(op.f(CONSTRAINT), 'geocoded_addresses', type_='check')
    op.create_check_constraint(
        op.f(CONSTRAINT),
        'geocoded_addresses',
        "status in ('pending', 'ok', 'not_found', 'manual', 'virtual')",
    )
