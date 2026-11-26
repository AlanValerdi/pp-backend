"""create geocoded addresses and user role

Revision ID: e7a1c3b94d20
Revises: d2ced4865fd9
Create Date: 2026-11-26 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e7a1c3b94d20'
down_revision: str | Sequence[str] | None = 'd2ced4865fd9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('geocoded_addresses',
    sa.Column('address_key', sa.Text(), nullable=False),
    sa.Column('raw_address', sa.Text(), nullable=False),
    sa.Column('lat', sa.Float(), nullable=True),
    sa.Column('lng', sa.Float(), nullable=True),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint(
        "status in ('pending', 'ok', 'not_found', 'manual', 'virtual')",
        name=op.f('ck_geocoded_addresses_status_valid'),
    ),
    sa.CheckConstraint(
        "source is null or source in ('nominatim', 'admin')",
        name=op.f('ck_geocoded_addresses_source_valid'),
    ),
    sa.PrimaryKeyConstraint('address_key', name=op.f('pk_geocoded_addresses'))
    )
    op.add_column('users', sa.Column('role', sa.Text(), server_default='user', nullable=False))
    op.create_check_constraint(op.f('ck_users_role_valid'), 'users', "role in ('user', 'admin')")


def downgrade() -> None:
    op.drop_constraint(op.f('ck_users_role_valid'), 'users', type_='check')
    op.drop_column('users', 'role')
    op.drop_table('geocoded_addresses')
