"""add_broker_columns_to_users

Revision ID: a1b2c3d4e5f7
Revises: 994860482e56
Create Date: 2026-02-22

Adds broker and broker_account_id columns to users table
for linking ProphitAI users to their brokerage accounts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '5a6b7c8d9e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('broker', sa.String(), nullable=True))
    op.add_column('users', sa.Column('broker_account_id', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_broker_account_id', 'users', ['broker_account_id'])
    op.create_index('ix_users_broker_account_id', 'users', ['broker_account_id'])


def downgrade() -> None:
    op.drop_index('ix_users_broker_account_id', table_name='users')
    op.drop_constraint('uq_users_broker_account_id', 'users', type_='unique')
    op.drop_column('users', 'broker_account_id')
    op.drop_column('users', 'broker')
