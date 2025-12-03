"""Add growth metrics columns to equity_screener table

Revision ID: c4d5e6f7g8h9
Revises: b3c4d5e6f7g8
Create Date: 2025-12-03

New columns:
- information_ratio: ann_return / ann_vol
- revenue_cagr_3yr: 3-year revenue compound annual growth rate
- ebit_growth_yoy: Year-over-year EBIT growth
- eps_growth_yoy: Year-over-year EPS growth
- fcf_growth_yoy: Year-over-year free cash flow growth
- operating_margin_change_yoy: Year-over-year change in operating margin (ppt)
- roce_change_5yr: 5-year change in return on capital employed (ppt)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7g8h9'
down_revision: Union[str, None] = 'b3c4d5e6f7g8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new growth metrics columns to equity_screener table
    op.add_column(
        'equity_screener',
        sa.Column('information_ratio', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('revenue_cagr_3yr', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('ebit_growth_yoy', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('eps_growth_yoy', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('fcf_growth_yoy', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('operating_margin_change_yoy', sa.Float(), nullable=True),
        schema='screener_data'
    )
    op.add_column(
        'equity_screener',
        sa.Column('roce_change_5yr', sa.Float(), nullable=True),
        schema='screener_data'
    )


def downgrade() -> None:
    op.drop_column('equity_screener', 'roce_change_5yr', schema='screener_data')
    op.drop_column('equity_screener', 'operating_margin_change_yoy', schema='screener_data')
    op.drop_column('equity_screener', 'fcf_growth_yoy', schema='screener_data')
    op.drop_column('equity_screener', 'eps_growth_yoy', schema='screener_data')
    op.drop_column('equity_screener', 'ebit_growth_yoy', schema='screener_data')
    op.drop_column('equity_screener', 'revenue_cagr_3yr', schema='screener_data')
    op.drop_column('equity_screener', 'information_ratio', schema='screener_data')
