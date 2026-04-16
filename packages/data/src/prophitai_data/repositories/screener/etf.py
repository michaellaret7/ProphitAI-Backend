"""ETF screener query builder and executor."""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import or_

from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Ticker, ETFScreener
from prophitai_data.repositories.screener.validation import (
    find_similar_sections,
    format_invalid_sections_error,
)


# ================================
# --> Constants
# ================================

TICKER_FIELDS = {'industries', 'sub_industries', 'price', 'market_cap', 'avg_volume', 'dollar_volume'}
LIST_TO_COLUMN = {'industries': 'industry', 'sub_industries': 'sub_industry'}
DOMAIN_FILTERS = {'industries', 'sub_industries'}


# ================================
# --> Result Model
# ================================

class ETFScreenerResult(BaseModel):
    model_config = ConfigDict(extra='allow')

    ticker: str
    industry: Optional[str] = None
    sub_industry: Optional[str] = None
    expense_ratio: Optional[float] = None
    nav: Optional[float] = None
    ann_vol: Optional[float] = None
    ann_ret: Optional[float] = None
    information_ratio: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None
    market_cap: Optional[float] = None
    dollar_volume: Optional[float] = None
    dividend_yield_ttm: Optional[float] = None

    # Quant screener — key fields surfaced by default
    hurst_exponent: Optional[float] = None
    adx_14d: Optional[float] = None
    atr_pct: Optional[float] = None
    momentum_12m_1m_skip: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    sharpe_ratio: Optional[float] = None


# ================================
# --> Helper funcs
# ================================

def _build_query(
    # Ticker table filters
    industries: List[str] | None = None,
    sub_industries: List[str] | None = None,
    market_cap: tuple[float | None, float | None] | None = None,
    dollar_volume: tuple[float | None, float | None] | None = None,
    # ETFScreener table filters
    expense_ratio: tuple[float | None, float | None] | None = None,
    nav: tuple[float | None, float | None] | None = None,
    ann_vol: tuple[float | None, float | None] | None = None,
    ann_ret: tuple[float | None, float | None] | None = None,
    information_ratio: tuple[float | None, float | None] | None = None,
    beta: tuple[float | None, float | None] | None = None,
    alpha: tuple[float | None, float | None] | None = None,
    dividend_yield_ttm: tuple[float | None, float | None] | None = None,
    # ================================================================
    # Quant screener filters (20 columns)
    # ================================================================
    # Volatility
    atr_pct: tuple[float | None, float | None] | None = None,
    bb_width: tuple[float | None, float | None] | None = None,
    vol_regime_pctile: tuple[float | None, float | None] | None = None,
    yang_zhang_vol: tuple[float | None, float | None] | None = None,
    vol_ratio_short_long: tuple[float | None, float | None] | None = None,
    # Momentum quality
    momentum_12m_1m_skip: tuple[float | None, float | None] | None = None,
    risk_adj_momentum: tuple[float | None, float | None] | None = None,
    rsi_14d: tuple[float | None, float | None] | None = None,
    tsmom: tuple[float | None, float | None] | None = None,
    # Mean-reversion
    hurst_exponent: tuple[float | None, float | None] | None = None,
    autocorrelation_1d: tuple[float | None, float | None] | None = None,
    # Trend
    adx_14d: tuple[float | None, float | None] | None = None,
    # Risk & performance
    max_drawdown_1y: tuple[float | None, float | None] | None = None,
    sharpe_ratio: tuple[float | None, float | None] | None = None,
    sortino_ratio: tuple[float | None, float | None] | None = None,
    cvar_95: tuple[float | None, float | None] | None = None,
    # Distribution
    return_skewness: tuple[float | None, float | None] | None = None,
    return_kurtosis: tuple[float | None, float | None] | None = None,
    positive_return_ratio: tuple[float | None, float | None] | None = None,
    # Return quality
    equity_curve_r2: tuple[float | None, float | None] | None = None,
):
    """Build a screener query with optional filters from Ticker and ETFScreener tables."""

    with MarketSession() as session:
        valid_industries = {row[0] for row in session.query(Ticker.industry).distinct().filter(Ticker.is_etf == True).all()}
        valid_sub_industries = {row[0] for row in session.query(Ticker.sub_industry).distinct().filter(Ticker.is_etf == True).all()}

    # Validate list inputs
    errors = []
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

        model = Ticker if key in TICKER_FIELDS else ETFScreener

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


# ================================
# --> Public API
# ================================

def screen_etfs(**kwargs) -> tuple[List[ETFScreenerResult] | None, str | None]:
    """Screen ETFs with optional filters. Returns (results, None) on success or (None, error_message) on error."""

    query_params = _build_query(**kwargs)
    if isinstance(query_params, str):
        return None, f"Error: {query_params}"

    results = []

    with MarketSession() as session:
        result = session.query(ETFScreener, Ticker).join(Ticker, ETFScreener.ticker_id == Ticker.id).filter(*query_params).all()

        if len(result) == 0:
            return None, "No results found, please try again with different or more lenient filters"

        for etf_screener, ticker in result:
            # Base fields
            data = {
                'ticker': ticker.ticker,
                'ticker_name': ticker.ticker_name,
                'ticker_description': ticker.ticker_description,
                'industry': ticker.industry,
                'sub_industry': ticker.sub_industry,
                'expense_ratio': etf_screener.expense_ratio/100 if etf_screener.expense_ratio is not None else None,
                'nav': etf_screener.nav,
                'ann_vol': etf_screener.ann_vol,
                'ann_ret': etf_screener.ann_ret,
                'information_ratio': etf_screener.information_ratio,
                'beta': etf_screener.beta,
                'alpha': etf_screener.alpha,
                'market_cap': ticker.market_cap,
                'dollar_volume': ticker.dollar_volume,
                'dividend_yield_ttm': etf_screener.dividend_yield_ttm,
            }

            # Add dynamic fields from kwargs (excluding list filters like sectors/industries)
            for key in kwargs:
                if key in LIST_TO_COLUMN:
                    continue  # Skip list filters, already have sector/industry/sub_industry
                # Skip parameters that have no actual filter values (e.g., [None, None])
                param_value = kwargs[key]
                if isinstance(param_value, (list, tuple)) and all(v is None for v in param_value):
                    continue
                # Get value from appropriate model
                if key in TICKER_FIELDS:
                    raw_value = getattr(ticker, key, None)
                else:
                    raw_value = getattr(etf_screener, key, None)
                if raw_value is not None:
                    data[key] = float(raw_value)

            results.append(ETFScreenerResult(**data))

    return results, None
