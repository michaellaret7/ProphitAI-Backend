"""Ticker information tools."""

from app.core.atlas.tools.responses import success_response, error_response
from app.utils.decorators.tool_validation import validate_ticker_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.token_count import get_token_count
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from typing import Optional
from datetime import datetime
import warnings
from app.utils.serialize_output import serialize_sqlalchemy_obj
warnings.filterwarnings("ignore", category=RuntimeWarning)

@validate_ticker_arg()
@log_simulation_data_range()
def get_ticker_info(ticker: str, _simulation_date: Optional[datetime] = None) -> str:
    """Get comprehensive ticker information including metadata and characteristics."""
    try:
        with MarketSession() as session:
            ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
            if not ticker_obj:
                return error_response(f"Ticker {ticker.upper()} not found")
            return success_response(serialize_sqlalchemy_obj(ticker_obj))
    except Exception as e:
        return error_response(f"Failed to retrieve ticker info for {ticker}: {str(e)}")


# Tool Schema Constants
GET_TICKER_INFO_DESCRIPTION = (
    "Retrieve comprehensive ticker information including company metadata and characteristics. "
    "Returns detailed stock profile data from the database for fundamental analysis.\n\n"
    "**Data Returned:**\n"
    "  - **ticker, ticker_name**: Symbol and full company name\n"
    "  - **ticker_description**: Business description and company overview\n"
    "  - **sector, industry, sub_industry**: GICS classification hierarchy\n"
    "  - **market_cap**: Market capitalization\n"
    "  - **price, beta, eps, pe**: Current price and key valuation metrics\n"
    "  - **dollar_volume, avg_volume**: Liquidity metrics\n"
    "  - **is_etf**: Whether the ticker is an ETF\n"
    "  - **exchange, currency, country**: Trading venue and geography\n\n"
    "**Use Cases:**\n"
    "  - **Company Overview**: Get a quick snapshot of a stock's profile\n"
    "  - **Classification Lookup**: Identify sector/industry for peer comparison\n"
    "  - **Eligibility Check**: Verify if ticker is actively traded and meets criteria\n"
    "  - **Pre-Analysis**: Gather context before deeper fundamental analysis\n"
    "  - **Portfolio Mapping**: Determine sector/industry exposure for holdings\n\n"
    "**Examples:**\n"
    "  get_ticker_info(ticker='AAPL')   # Apple Inc. profile\n"
    "  get_ticker_info(ticker='MSFT')   # Microsoft Corp. profile\n"
    "  get_ticker_info(ticker='JPM')    # JPMorgan Chase profile"
)

GET_TICKER_INFO_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "Stock ticker symbol to retrieve information for. "
                "Must be a valid US equity ticker. "
                "Examples: 'AAPL', 'MSFT', 'GOOGL', 'TSLA', 'JPM'"
            ),
        },
    },
    "required": ["ticker"],
    "additionalProperties": False
}

GET_TICKER_INFO_TOOL = {
    "name": "get_ticker_info",
    "description": GET_TICKER_INFO_DESCRIPTION,
    "parameters": GET_TICKER_INFO_PARAMETERS,
    "function": get_ticker_info,
}
