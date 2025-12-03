from sqlalchemy.orm import query
from sqlalchemy import or_
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, ETFScreener
from app.utils.serialize_output import serialize_sqlalchemy_obj
from typing import List

TICKER_FIELDS = {'industries', 'sub_industries', 'price', 'market_cap', 'avg_volume', 'dollar_volume'}
LIST_TO_COLUMN = {'industries': 'industry', 'sub_industries': 'sub_industry'}
DOMAIN_FILTERS = {'industries', 'sub_industries'}

def build_query(
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
):
    """Build a screener query with optional filters from Ticker and ETFScreener tables."""

    with MarketSession() as session:
        valid_industries = {row[0] for row in session.query(Ticker.industry).distinct().filter(Ticker.is_etf == True).all()}
        valid_sub_industries = {row[0] for row in session.query(Ticker.sub_industry).distinct().filter(Ticker.is_etf == True).all()}

    if industries:
        invalid = set(industries) - valid_industries
        if invalid:
            return f"Invalid industries: {invalid}"
    if sub_industries:
        invalid = set(sub_industries) - valid_sub_industries
        if invalid:
            return f"Invalid sub_industries: {invalid}"

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


    