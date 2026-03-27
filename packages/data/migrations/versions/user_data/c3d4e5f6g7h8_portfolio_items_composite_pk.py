"""Change portfolio_items to use composite primary key (portfolio_id, ticker)

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-12-30

Removes the auto-increment id column and uses (portfolio_id, ticker) as composite PK,
consistent with WatchlistItem pattern.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing primary key constraint
    op.drop_constraint('portfolio_items_pkey', 'portfolio_items', type_='primary')

    # Drop the id column
    op.drop_column('portfolio_items', 'id')

    # Drop the index on portfolio_id (will be part of PK now)
    op.drop_index('ix_portfolio_items_portfolio_id', table_name='portfolio_items')

    # Create composite primary key
    op.create_primary_key('portfolio_items_pkey', 'portfolio_items', ['portfolio_id', 'ticker'])


def downgrade() -> None:
    # Drop composite primary key
    op.drop_constraint('portfolio_items_pkey', 'portfolio_items', type_='primary')

    # Add back the id column
    op.add_column('portfolio_items', sa.Column('id', sa.Integer(), autoincrement=True, nullable=False))

    # Create primary key on id
    op.create_primary_key('portfolio_items_pkey', 'portfolio_items', ['id'])

    # Recreate index on portfolio_id
    op.create_index('ix_portfolio_items_portfolio_id', 'portfolio_items', ['portfolio_id'], unique=False)
