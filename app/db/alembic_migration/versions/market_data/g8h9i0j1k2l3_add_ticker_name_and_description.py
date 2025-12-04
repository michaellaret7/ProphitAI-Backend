"""Add ticker_name and ticker_description columns to tickers table

Revision ID: g8h9i0j1k2l3
Revises: f7g8h9i0j1k2
Create Date: 2025-12-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g8h9i0j1k2l3'
down_revision: Union[str, None] = 'f7g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'tickers',
        sa.Column('ticker_name', sa.String(), nullable=True),
        schema='ticker_universe'
    )
    op.add_column(
        'tickers',
        sa.Column('ticker_description', sa.Text(), nullable=True),
        schema='ticker_universe'
    )


def downgrade() -> None:
    op.drop_column('tickers', 'ticker_description', schema='ticker_universe')
    op.drop_column('tickers', 'ticker_name', schema='ticker_universe')
