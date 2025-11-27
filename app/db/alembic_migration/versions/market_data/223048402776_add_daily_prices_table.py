"""Add daily_prices table

Revision ID: 223048402776
Revises:
Create Date: 2025-11-27 16:43:38.276902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '223048402776'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('daily_prices',
        sa.Column('ticker_id', sa.UUID(), nullable=False),
        sa.Column('datetime', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('close', sa.Float(), nullable=True),
        sa.Column('adj_close', sa.Float(), nullable=True),
        sa.Column('volume', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['ticker_id'], ['ticker_universe.tickers.id'], ),
        sa.PrimaryKeyConstraint('ticker_id', 'datetime'),
        schema='price_data'
    )
    op.create_index(op.f('ix_price_data_daily_prices_datetime'), 'daily_prices', ['datetime'], unique=False, schema='price_data')
    op.create_index(op.f('ix_price_data_daily_prices_ticker_id'), 'daily_prices', ['ticker_id'], unique=False, schema='price_data')


def downgrade() -> None:
    op.drop_index(op.f('ix_price_data_daily_prices_ticker_id'), table_name='daily_prices', schema='price_data')
    op.drop_index(op.f('ix_price_data_daily_prices_datetime'), table_name='daily_prices', schema='price_data')
    op.drop_table('daily_prices', schema='price_data')
