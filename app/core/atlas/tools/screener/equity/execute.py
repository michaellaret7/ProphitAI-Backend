"""Equity screener query executor."""

from typing import List

from pydantic import BaseModel, ConfigDict

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import EquityScreener, Ticker
from app.core.atlas.tools.screener.equity.build import build_query, LIST_TO_COLUMN, TICKER_FIELDS


class EquityScreenerResult(BaseModel):
    model_config = ConfigDict(extra='allow')

    ticker: str
    sector: str
    industry: str
    sub_industry: str
    market_cap: float
    price: float
    anualized_volatility: float
    anualized_return: float


def execute_query(**kwargs) -> tuple[List[EquityScreenerResult] | None, str | None]:
    """Returns (results, None) on success or (None, error_message) on error."""
    query_params = build_query(**kwargs)
    if isinstance(query_params, str):
        return None, f"Error: {query_params}"

    results = []

    with MarketSession() as session:
        result = session.query(EquityScreener, Ticker).join(Ticker, EquityScreener.ticker_id == Ticker.id).filter(*query_params).all()

        if len(result) == 0:
            return None, "No results found, please try again with different or more lenient filters"

        for equity_screener, ticker in result:
            # Base fields
            data = {
                'ticker': ticker.ticker,
                'ticker_name': ticker.ticker_name,
                'ticker_description': ticker.ticker_description,
                'sector': ticker.sector,
                'industry': ticker.industry,
                'sub_industry': ticker.sub_industry,
                'price': ticker.price,
                'market_cap': ticker.market_cap,
                'anualized_volatility': equity_screener.ann_vol,
                'anualized_return': equity_screener.ann_return,
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
                    raw_value = getattr(equity_screener, key, None)
                if raw_value is not None:
                    data[key] = float(raw_value)

            results.append(EquityScreenerResult(**data))

    return results, None
