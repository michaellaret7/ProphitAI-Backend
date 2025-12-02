from sqlalchemy.orm import query
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, EquityScreener
from app.utils.serialize_output import serialize_sqlalchemy_obj

TICKER_FIELDS = {'sector', 'industry', 'sub_industry', 'price', 'market_cap', 'avg_volume', 'eps', 'pe', 'dollar_volume'}

def build_query(
    # Ticker table filters
    sector: str | None = None,
    industry: str | None = None,
    sub_industry: str | None = None,
    price: tuple[float | None, float | None] | None = None,
    market_cap: tuple[float | None, float | None] | None = None,
    avg_volume: tuple[float | None, float | None] | None = None,
    eps: tuple[float | None, float | None] | None = None,
    pe: tuple[float | None, float | None] | None = None,
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

    params = [Ticker.price >= 5]
    for key, value in locals().items():
        if value is None:
            continue

        model = Ticker if key in TICKER_FIELDS else EquityScreener
        column = getattr(model, key, None)

        # if the instance is a string set it equal to the Ticker obj
        if isinstance(value, str):
            params.append(column == value)
        # if the instance is a tuple this is the min, max range
        elif isinstance(value, tuple):
            min_val, max_val = value

            if min_val is not None:
                params.append(column >= min_val)
            if max_val is not None:
                params.append(column <= max_val)

    return params



        
