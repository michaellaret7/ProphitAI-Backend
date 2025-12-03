from app.core.agentic_framework.tool_lib.data_tools.screeners.equity.build import build_query, LIST_TO_COLUMN, TICKER_FIELDS
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import EquityScreener, Ticker
from app.utils.serialize_output import serialize_sqlalchemy_obj
from typing import List, Any
from pydantic import BaseModel, ConfigDict
import pandas as pd

class EquityScreenerResult(BaseModel):
    model_config = ConfigDict(extra='allow')

    ticker: str
    sector: str
    industry: str
    sub_industry: str
    market_cap: float

def execute_query(**kwargs) -> List[EquityScreenerResult]:
    query_params = build_query(**kwargs)
    if isinstance(query_params, str):
        return f"Error: {query_params}"

    results = []

    with MarketSession() as session:
        result = session.query(EquityScreener, Ticker).join(Ticker).filter(*query_params).all() # This is the line to query the actual data from the database

        if len(result) == 0:
            return "No results found, please try again with different or more lenient filters"

        for equity_screener, ticker in result:
            # Base fields
            data = {
                'ticker': ticker.ticker,
                'sector': ticker.sector,
                'industry': ticker.industry,
                'sub_industry': ticker.sub_industry,
                'market_cap': ticker.market_cap,
                'anualized_volatility': equity_screener.ann_vol,
                'anualized_return': equity_screener.ann_return,
            }

            # Add dynamic fields from kwargs (excluding list filters like sectors/industries)
            for key in kwargs:
                if key in LIST_TO_COLUMN:
                    continue  # Skip list filters, already have sector/industry/sub_industry
                # Get value from appropriate model
                if key in TICKER_FIELDS:
                    value = getattr(ticker, key, None)
                else:
                    value = getattr(equity_screener, key, None)
                if value is not None:
                    data[key] = value

            results.append(EquityScreenerResult(**data))

    return results
