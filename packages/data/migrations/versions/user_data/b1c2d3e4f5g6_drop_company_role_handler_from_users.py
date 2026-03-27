"""drop_company_role_handler_from_users

Revision ID: b1c2d3e4f5g6
Revises: a1b2c3d4e5f7
Create Date: 2026-02-22

Removes the company/role/handler system from users. Drops the
company_id, role, and handler_id columns along with their FK and
check constraints, and drops the companies table entirely.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'b1c2d3e4f5g6'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reason: Use raw SQL with IF EXISTS to handle production environments
    # where some/all of these objects were never created

    # Drop FK: users.handler_id -> users.id
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS fk_users_handler_id")

    # Drop check constraint on role
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS chk_user_role")

    # Drop index on handler_id
    op.execute("DROP INDEX IF EXISTS ix_users_handler_id")

    # Drop columns (only if they exist)
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS handler_id")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS role")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS company_id")

    # Drop the companies table entirely
    op.execute("DROP TABLE IF EXISTS companies")


def downgrade() -> None:
    # Recreate companies table
    op.create_table(
        'companies',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('creation_date', sa.DateTime(), nullable=True),
        sa.Column('seats', sa.Integer(), nullable=True),
    )

    # Recreate columns
    op.add_column('users', sa.Column('company_id', UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))
    op.add_column('users', sa.Column('handler_id', UUID(as_uuid=True), nullable=True))

    # Recreate index
    op.create_index('ix_users_handler_id', 'users', ['handler_id'])

    # Recreate constraints
    op.create_check_constraint(
        'chk_user_role', 'users',
        "role IN ('ria', 'client', 'individual', 'system')"
    )
    op.create_foreign_key('fk_users_handler_id', 'users', 'users', ['handler_id'], ['id'])
