"""Add portfolio_preferences table

Revision ID: h8i9j0k1l2m3
Revises: bab6c29ecb4c
Create Date: 2026-01-09

Creates the portfolio_preferences table for storing investment preferences
per portfolio including:
- Risk tolerance and investment objectives
- Asset allocation targets (decimal 0-1)
- Equity and fixed income sector preferences
- Ticker include/exclude lists
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


revision: str = 'h8i9j0k1l2m3'
down_revision: Union[str, None] = 'bab6c29ecb4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portfolio_preferences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('portfolio_id', UUID(as_uuid=True), nullable=False),

        # Risk Profile
        sa.Column('risk_tolerance', sa.String(50), nullable=True),
        sa.Column('investment_time_horizon', sa.String(30), nullable=True),
        sa.Column('liquidity_needs', sa.String(10), nullable=True),

        # Asset Allocation Preferences (decimal 0-1)
        sa.Column('equities_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('fixed_income_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('commodities_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('currencies_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('cryptocurrencies_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('alternatives_hedge_funds_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('alternatives_pe_vc_allocation', sa.Numeric(5, 4), nullable=True),
        sa.Column('cash_allocation', sa.Numeric(5, 4), nullable=True),

        # Equity Sector Preferences
        sa.Column('equity_sector_communication_services', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_consumer_discretionary', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_consumer_staples', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_energy', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_financials', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_health_care', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_industrials', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_information_technology', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_materials', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_real_estate', sa.String(15), server_default='Not Selected'),
        sa.Column('equity_sector_utilities', sa.String(15), server_default='Not Selected'),

        # Fixed Income Sector Preferences
        sa.Column('fixed_income_sector_sovereign_treasuries', sa.String(15), server_default='Not Selected'),
        sa.Column('fixed_income_sector_ig_credit', sa.String(15), server_default='Not Selected'),
        sa.Column('fixed_income_sector_high_yield', sa.String(15), server_default='Not Selected'),
        sa.Column('fixed_income_sector_securitized_products', sa.String(15), server_default='Not Selected'),

        # Ticker Lists
        sa.Column('tickers_to_include', ARRAY(sa.String()), nullable=True),
        sa.Column('tickers_to_exclude', ARRAY(sa.String()), nullable=True),

        # Timestamps
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),

        # Foreign key constraint
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),

        # Check constraints for allocation values (0-1)
        sa.CheckConstraint('equities_allocation >= 0 AND equities_allocation <= 1', name='chk_equities_allocation'),
        sa.CheckConstraint('fixed_income_allocation >= 0 AND fixed_income_allocation <= 1', name='chk_fixed_income_allocation'),
        sa.CheckConstraint('commodities_allocation >= 0 AND commodities_allocation <= 1', name='chk_commodities_allocation'),
        sa.CheckConstraint('currencies_allocation >= 0 AND currencies_allocation <= 1', name='chk_currencies_allocation'),
        sa.CheckConstraint('cryptocurrencies_allocation >= 0 AND cryptocurrencies_allocation <= 1', name='chk_cryptocurrencies_allocation'),
        sa.CheckConstraint('alternatives_hedge_funds_allocation >= 0 AND alternatives_hedge_funds_allocation <= 1', name='chk_hedge_funds_allocation'),
        sa.CheckConstraint('alternatives_pe_vc_allocation >= 0 AND alternatives_pe_vc_allocation <= 1', name='chk_pe_vc_allocation'),
        sa.CheckConstraint('cash_allocation >= 0 AND cash_allocation <= 1', name='chk_cash_allocation'),

        # Check constraints for enum-like string columns
        sa.CheckConstraint(
            "risk_tolerance IN ('Capital Preservation', 'Income', 'Balanced/Moderate Growth', 'Growth', 'Aggressive Growth/Speculation')",
            name='chk_risk_tolerance'
        ),
        sa.CheckConstraint(
            "investment_time_horizon IN ('Short term (0-2 years)', 'Medium term (3-7 years)', 'Long term (8+ years)')",
            name='chk_time_horizon'
        ),
        sa.CheckConstraint(
            "liquidity_needs IN ('High', 'Medium', 'Low')",
            name='chk_liquidity_needs'
        ),
    )

    # Create indexes
    op.create_index('ix_portfolio_preferences_id', 'portfolio_preferences', ['id'], unique=False)
    op.create_index('ix_portfolio_preferences_portfolio_id', 'portfolio_preferences', ['portfolio_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_portfolio_preferences_portfolio_id', table_name='portfolio_preferences')
    op.drop_index('ix_portfolio_preferences_id', table_name='portfolio_preferences')
    op.drop_table('portfolio_preferences')
