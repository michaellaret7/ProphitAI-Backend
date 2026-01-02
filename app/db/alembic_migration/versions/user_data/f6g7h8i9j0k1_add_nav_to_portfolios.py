"""Add nav column to portfolios table

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2026-01-02

Adds nav (Net Asset Value) column to track the total value of each portfolio.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('portfolios', sa.Column('nav', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolios', 'nav')
