"""Equity screener query builder."""

from sqlalchemy import or_
from typing import List

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, EquityScreener
from app.core.atlas.tools_v2.screener.find_similar_section import (
    find_similar_sections,
    format_invalid_sections_error,
)

TICKER_FIELDS = {'sectors', 'industries', 'sub_industries', 'price', 'market_cap', 'avg_volume', 'eps', 'pe', 'dollar_volume'}
LIST_TO_COLUMN = {'sectors': 'sector', 'industries': 'industry', 'sub_industries': 'sub_industry'}
DOMAIN_FILTERS = {'sectors', 'industries', 'sub_industries'}


def build_query(
    # Ticker table filters
    sectors: List[str] | None = None,
    industries: List[str] | None = None,
    sub_industries: List[str] | None = None,
    price: tuple[float | None, float | None] | None = None,
    market_cap: tuple[float | None, float | None] | None = None,
    avg_volume: tuple[float | None, float | None] | None = None,
    eps: tuple[float | None, float | None] | None = None,
    dollar_volume: tuple[float | None, float | None] | None = None,
    # Momentum & Performance metrics (EquityScreener)
    momentum_1m: tuple[float | None, float | None] | None = None,
    momentum_3m: tuple[float | None, float | None] | None = None,
    momentum_6m: tuple[float | None, float | None] | None = None,
    ann_return: tuple[float | None, float | None] | None = None,
    ann_vol: tuple[float | None, float | None] | None = None,
    beta_vs_spy: tuple[float | None, float | None] | None = None,
    beta_vs_sector: tuple[float | None, float | None] | None = None,
    alpha_vs_spy: tuple[float | None, float | None] | None = None,
    alpha_vs_sector: tuple[float | None, float | None] | None = None,
    ebit_cagr_5yr: tuple[float | None, float | None] | None = None,
    ebit_cagr_3yr: tuple[float | None, float | None] | None = None,
    # Calculated growth metrics
    information_ratio: tuple[float | None, float | None] | None = None,
    revenue_cagr_3yr: tuple[float | None, float | None] | None = None,
    ebit_growth_yoy: tuple[float | None, float | None] | None = None,
    eps_growth_yoy: tuple[float | None, float | None] | None = None,
    fcf_growth_yoy: tuple[float | None, float | None] | None = None,
    operating_margin_change_yoy: tuple[float | None, float | None] | None = None,
    roce_change_5yr: tuple[float | None, float | None] | None = None,
    # Valuation ratios
    dividend_yield_ttm: tuple[float | None, float | None] | None = None,
    pe_ratio_ttm: tuple[float | None, float | None] | None = None,
    peg_ratio_ttm: tuple[float | None, float | None] | None = None,
    price_to_book_ratio_ttm: tuple[float | None, float | None] | None = None,
    price_to_sales_ratio_ttm: tuple[float | None, float | None] | None = None,
    price_to_free_cash_flows_ratio_ttm: tuple[float | None, float | None] | None = None,
    price_to_operating_cash_flows_ratio_ttm: tuple[float | None, float | None] | None = None,
    enterprise_value_multiple_ttm: tuple[float | None, float | None] | None = None,
    # Profitability ratios
    payout_ratio_ttm: tuple[float | None, float | None] | None = None,
    gross_profit_margin_ttm: tuple[float | None, float | None] | None = None,
    operating_profit_margin_ttm: tuple[float | None, float | None] | None = None,
    pretax_profit_margin_ttm: tuple[float | None, float | None] | None = None,
    net_profit_margin_ttm: tuple[float | None, float | None] | None = None,
    return_on_assets_ttm: tuple[float | None, float | None] | None = None,
    return_on_equity_ttm: tuple[float | None, float | None] | None = None,
    return_on_capital_employed_ttm: tuple[float | None, float | None] | None = None,
    # Cash flow ratios
    operating_cash_flow_sales_ratio_ttm: tuple[float | None, float | None] | None = None,
    free_cash_flow_operating_cash_flow_ratio_ttm: tuple[float | None, float | None] | None = None,
    capital_expenditure_coverage_ratio_ttm: tuple[float | None, float | None] | None = None,
    dividend_paid_and_capex_coverage_ratio_ttm: tuple[float | None, float | None] | None = None,
    # Debt ratios
    debt_ratio_ttm: tuple[float | None, float | None] | None = None,
    debt_equity_ratio_ttm: tuple[float | None, float | None] | None = None,
    long_term_debt_to_capitalization_ttm: tuple[float | None, float | None] | None = None,
    total_debt_to_capitalization_ttm: tuple[float | None, float | None] | None = None,
    interest_coverage_ttm: tuple[float | None, float | None] | None = None,
    cash_flow_to_debt_ratio_ttm: tuple[float | None, float | None] | None = None,
    short_term_coverage_ratios_ttm: tuple[float | None, float | None] | None = None,
    company_equity_multiplier_ttm: tuple[float | None, float | None] | None = None,
    # Liquidity ratios
    quick_ratio_ttm: tuple[float | None, float | None] | None = None,
    cash_ratio_ttm: tuple[float | None, float | None] | None = None,
    # Efficiency ratios
    cash_conversion_cycle_ttm: tuple[float | None, float | None] | None = None,
    receivables_turnover_ttm: tuple[float | None, float | None] | None = None,
    payables_turnover_ttm: tuple[float | None, float | None] | None = None,
    inventory_turnover_ttm: tuple[float | None, float | None] | None = None,
    asset_turnover_ttm: tuple[float | None, float | None] | None = None,
):
    """Build a screener query with optional filters from Ticker and EquityScreener tables."""

    with MarketSession() as session:
        valid_sectors = {row[0] for row in session.query(Ticker.sector).distinct().filter(Ticker.sector != 'etf').all()}
        valid_industries = {row[0] for row in session.query(Ticker.industry).distinct().filter(Ticker.sector != 'etf').all()}
        valid_sub_industries = {row[0] for row in session.query(Ticker.sub_industry).distinct().filter(Ticker.sector != 'etf').all()}

    # Validate list inputs
    errors = []
    if sectors:
        invalid_sectors = set(sectors) - valid_sectors
        if invalid_sectors:
            similar_sectors = find_similar_sections(invalid_sectors, valid_sectors)
            errors.append(format_invalid_sections_error("sectors", invalid_sectors, similar_sectors))
    if industries:
        invalid_industries = set(industries) - valid_industries
        if invalid_industries:
            similar_industries = find_similar_sections(invalid_industries, valid_industries)
            errors.append(format_invalid_sections_error("industries", invalid_industries, similar_industries))
    if sub_industries:
        invalid_sub_industries = set(sub_industries) - valid_sub_industries
        if invalid_sub_industries:
            similar_sub_industries = find_similar_sections(invalid_sub_industries, valid_sub_industries)
            errors.append(format_invalid_sections_error("sub_industries", invalid_sub_industries, similar_sub_industries))
    if errors:
        return "\n".join(errors)

    # All Tickers must have a price of at least 5, we do not want any penny stocks
    params = [Ticker.price >= 5]
    # Reason: Domain filters (sectors, industries, sub_industries) use OR logic
    # so that users can select stocks from multiple domains
    domain_conditions = []

    for key, value in locals().items():
        if value is None:
            continue

        model = Ticker if key in TICKER_FIELDS else EquityScreener

        # Map plural param names to singular column names for list fields
        column_name = LIST_TO_COLUMN.get(key, key)
        column = getattr(model, column_name, None)

        # Skip if column doesn't exist on model (internal variables from locals())
        if column is None:
            continue

        # If the value is a list, use IN clause
        if isinstance(value, list):
            condition = column.in_(value)
            # Domain filters (sectors, industries, sub_industries) use OR logic
            if key in DOMAIN_FILTERS:
                domain_conditions.append(condition)
            else:
                params.append(condition)
        # If the instance is a tuple this is the min, max range
        elif isinstance(value, tuple):
            min_val, max_val = value
            if min_val is not None and max_val is not None and min_val > max_val:
                return f"Invalid range for {key}: min ({min_val}) cannot be greater than max ({max_val})"
            if min_val is not None:
                params.append(column >= min_val)
            if max_val is not None:
                params.append(column <= max_val)

    # Combine domain conditions with OR logic
    if domain_conditions:
        params.append(or_(*domain_conditions))

    return params
