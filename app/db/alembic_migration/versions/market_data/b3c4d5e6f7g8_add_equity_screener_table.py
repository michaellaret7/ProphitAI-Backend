"""Add equity_screener table

Revision ID: b3c4d5e6f7g8
Revises: dd8692b53765
Create Date: 2025-12-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7g8'
down_revision: Union[str, None] = 'dd8692b53765'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the screener_data schema if it doesn't exist
    op.execute('CREATE SCHEMA IF NOT EXISTS screener_data')

    op.create_table('equity_screener',
        sa.Column('ticker_id', sa.UUID(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),

        # Momentum metrics
        sa.Column('momentum_1m', sa.Float(), nullable=True),
        sa.Column('momentum_3m', sa.Float(), nullable=True),
        sa.Column('momentum_6m', sa.Float(), nullable=True),

        # Performance metrics
        sa.Column('ann_return', sa.Float(), nullable=True),
        sa.Column('ann_vol', sa.Float(), nullable=True),

        # Beta metrics
        sa.Column('beta_vs_spy', sa.Float(), nullable=True),
        sa.Column('beta_vs_sector', sa.Float(), nullable=True),

        # Alpha metrics
        sa.Column('alpha_vs_spy', sa.Float(), nullable=True),
        sa.Column('alpha_vs_sector', sa.Float(), nullable=True),

        # Growth metrics
        sa.Column('ebit_cagr_5yr', sa.Float(), nullable=True),
        sa.Column('ebit_cagr_3yr', sa.Float(), nullable=True),

        # TTM Valuation ratios
        sa.Column('dividend_yield_ttm', sa.Float(), nullable=True),
        sa.Column('pe_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('peg_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('price_to_book_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('price_to_sales_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('price_to_free_cash_flows_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('price_to_operating_cash_flows_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('enterprise_value_multiple_ttm', sa.Float(), nullable=True),

        # TTM Profitability ratios
        sa.Column('payout_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('gross_profit_margin_ttm', sa.Float(), nullable=True),
        sa.Column('operating_profit_margin_ttm', sa.Float(), nullable=True),
        sa.Column('pretax_profit_margin_ttm', sa.Float(), nullable=True),
        sa.Column('net_profit_margin_ttm', sa.Float(), nullable=True),

        # TTM Return ratios
        sa.Column('return_on_assets_ttm', sa.Float(), nullable=True),
        sa.Column('return_on_equity_ttm', sa.Float(), nullable=True),
        sa.Column('return_on_capital_employed_ttm', sa.Float(), nullable=True),

        # TTM Cash flow ratios
        sa.Column('operating_cash_flow_sales_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('free_cash_flow_operating_cash_flow_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('capital_expenditure_coverage_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('dividend_paid_and_capex_coverage_ratio_ttm', sa.Float(), nullable=True),

        # TTM Debt/Solvency ratios
        sa.Column('debt_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('debt_equity_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('long_term_debt_to_capitalization_ttm', sa.Float(), nullable=True),
        sa.Column('total_debt_to_capitalization_ttm', sa.Float(), nullable=True),
        sa.Column('interest_coverage_ttm', sa.Float(), nullable=True),
        sa.Column('cash_flow_to_debt_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('short_term_coverage_ratios_ttm', sa.Float(), nullable=True),
        sa.Column('company_equity_multiplier_ttm', sa.Float(), nullable=True),

        # TTM Liquidity ratios
        sa.Column('quick_ratio_ttm', sa.Float(), nullable=True),
        sa.Column('cash_ratio_ttm', sa.Float(), nullable=True),

        # TTM Efficiency/Activity ratios
        sa.Column('cash_conversion_cycle_ttm', sa.Float(), nullable=True),
        sa.Column('receivables_turnover_ttm', sa.Float(), nullable=True),
        sa.Column('payables_turnover_ttm', sa.Float(), nullable=True),
        sa.Column('inventory_turnover_ttm', sa.Float(), nullable=True),
        sa.Column('asset_turnover_ttm', sa.Float(), nullable=True),

        sa.ForeignKeyConstraint(['ticker_id'], ['ticker_universe.tickers.id']),
        sa.PrimaryKeyConstraint('ticker_id'),
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_equity_screener_ticker_id'),
        'equity_screener',
        ['ticker_id'],
        unique=False,
        schema='screener_data'
    )
    op.create_index(
        op.f('ix_screener_data_equity_screener_updated_at'),
        'equity_screener',
        ['updated_at'],
        unique=False,
        schema='screener_data'
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_screener_data_equity_screener_updated_at'),
        table_name='equity_screener',
        schema='screener_data'
    )
    op.drop_index(
        op.f('ix_screener_data_equity_screener_ticker_id'),
        table_name='equity_screener',
        schema='screener_data'
    )
    op.drop_table('equity_screener', schema='screener_data')
    op.execute('DROP SCHEMA IF EXISTS screener_data')
