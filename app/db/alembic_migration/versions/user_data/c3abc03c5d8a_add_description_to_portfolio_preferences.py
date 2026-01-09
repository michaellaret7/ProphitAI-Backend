"""add_description_to_portfolio_preferences

Revision ID: c3abc03c5d8a
Revises: h8i9j0k1l2m3
Create Date: 2026-01-09 11:42:35.856125

Adds a description column to the portfolio_preferences table to store
a string description for portfolios.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3abc03c5d8a'
down_revision: Union[str, None] = 'h8i9j0k1l2m3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('portfolio_preferences', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolio_preferences', 'description')
