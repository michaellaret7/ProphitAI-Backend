"""Add dividend_yield_ttm column to etf_screener table

Revision ID: f7g8h9i0j1k2
Revises: e6f7g8h9i0j1
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = 'e6f7g8h9i0j1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'etf_screener',
        sa.Column('dividend_yield_ttm', sa.Float(), nullable=True),
        schema='screener_data'
    )


def downgrade() -> None:
    op.drop_column('etf_screener', 'dividend_yield_ttm', schema='screener_data')
