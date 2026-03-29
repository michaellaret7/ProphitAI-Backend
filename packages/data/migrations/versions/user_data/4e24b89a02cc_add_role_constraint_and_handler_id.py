"""add_role_constraint_and_handler_id

Revision ID: 4e24b89a02cc
Revises: 994860482e56
Create Date: 2026-02-06 10:34:39.703033

Adds a CheckConstraint on users.role to restrict values to ('ria', 'client', 'individual').
Adds handler_id (UUID, FK to users.id) column for RIA-client relationships.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4e24b89a02cc'
down_revision: Union[str, None] = '994860482e56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add check constraint on role column
    op.create_check_constraint(
        'chk_user_role',
        'users',
        "role IN ('ria', 'client', 'individual', 'system')"
    )

    # Add handler_id column with FK to users.id and index
    op.add_column('users', sa.Column('handler_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_users_handler_id'), 'users', ['handler_id'], unique=False)
    op.create_foreign_key('fk_users_handler_id', 'users', 'users', ['handler_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_users_handler_id', 'users', type_='foreignkey')
    op.drop_index(op.f('ix_users_handler_id'), table_name='users')
    op.drop_column('users', 'handler_id')
    op.drop_constraint('chk_user_role', 'users', type_='check')
