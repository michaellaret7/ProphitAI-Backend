from app.core.agentic_framework.tool_lib.data_tools.screeners.etf.build import build_query, LIST_TO_COLUMN, TICKER_FIELDS
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import ETFScreener, Ticker
from app.utils.serialize_output import serialize_sqlalchemy_obj
from typing import List, Any, Optional
from pydantic import BaseModel, ConfigDict
import pandas as pd
from uuid import UUID

class ETFScreenerResult(BaseModel):
    ticker: str
    industry: Optional[str] = None
    subindustry: Optional[str] = None
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

def execute_query(**kwargs) -> tuple[List[ETFScreenerResult] | None, str | None]:
    """Returns (results, None) on success or (None, error_message) on error."""

    query_params = build_query(**kwargs)
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
                'industry': ticker.industry,
                'subindustry': ticker.sub_industry,
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
                # Get value from appropriate model
                if key in TICKER_FIELDS:
                    value = float(getattr(ticker, key, None))
                else:
                    value = float(getattr(etf_screener, key, None))
                if value is not None:
                    data[key] = value

            results.append(ETFScreenerResult(**data))

    return results, None

