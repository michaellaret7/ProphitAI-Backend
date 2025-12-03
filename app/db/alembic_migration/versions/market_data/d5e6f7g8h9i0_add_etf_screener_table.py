"""Add etf_screener table

Revision ID: d5e6f7g8h9i0
Revises: c4d5e6f7g8h9
Create Date: 2025-12-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7g8h9i0'
down_revision: Union[str, None] = 'c4d5e6f7g8h9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('etf_screener',
        sa.Column('ticker_id', sa.UUID(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # Classification
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('subindustry', sa.String(), nullable=True),

        # Cost metrics
        sa.Column('expense_ratio', sa.Float(), nullable=True),
        sa.Column('nav', sa.Float(), nullable=True),

        # Performance metrics
        sa.Column('ann_vol', sa.Float(), nullable=True),
        sa.Column('ann_ret', sa.Float(), nullable=True),
        sa.Column('information_ratio', sa.Float(), nullable=True),

        # Risk metrics
        sa.Column('beta', sa.Float(), nullable=True),

        # Size metrics
        sa.Column('market_cap', sa.Numeric(), nullable=True),
        sa.Column('dollar_volume', sa.Numeric(), nullable=True),

        sa.ForeignKeyConstraint(['ticker_id'], ['ticker_universe.tickers.id']),
        sa.PrimaryKeyConstraint('ticker_id'),
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_etf_screener_ticker_id'),
        'etf_screener',
        ['ticker_id'],
        unique=False,
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_etf_screener_updated_at'),
        'etf_screener',
        ['updated_at'],
        unique=False,
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_etf_screener_industry'),
        'etf_screener',
        ['industry'],
        unique=False,
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_etf_screener_subindustry'),
        'etf_screener',
        ['subindustry'],
        unique=False,
        schema='screener_data'
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_screener_data_etf_screener_subindustry'),
        table_name='etf_screener',
        schema='screener_data'
    )
    op.drop_index(
        op.f('ix_screener_data_etf_screener_industry'),
        table_name='etf_screener',
        schema='screener_data'
    )
    op.drop_index(
        op.f('ix_screener_data_etf_screener_updated_at'),
        table_name='etf_screener',
        schema='screener_data'
    )
    op.drop_index(
        op.f('ix_screener_data_etf_screener_ticker_id'),
        table_name='etf_screener',
        schema='screener_data'
    )
    op.drop_table('etf_screener', schema='screener_data')
