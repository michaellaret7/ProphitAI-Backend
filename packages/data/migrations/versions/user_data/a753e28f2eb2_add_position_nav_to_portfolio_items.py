"""add_position_nav_to_portfolio_items

Revision ID: a753e28f2eb2
Revises: g7h8i9j0k1l2
Create Date: 2026-01-05 22:39:07.504342

Adds position_nav column to portfolio_items table to track individual position
values (num_shares * current_price).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a753e28f2eb2'
down_revision: Union[str, None] = 'g7h8i9j0k1l2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('portfolio_items', sa.Column('position_nav', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolio_items', 'position_nav')
