"""ETF holdings tools."""

from typing import Optional
from datetime import datetime
from app.repositories.etf_data import (
    get_etf_holdings as _get_etf_holdings
)
from app.utils.decorators.tool_validation import validate_ticker_arg, validate_numeric_arg
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.atlas.tools.responses import success_response, error_response
import pandas as pd
from app.utils.token_count import get_token_count
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

@validate_ticker_arg()
@validate_numeric_arg("limit", min_value=1, max_value=100)
@log_simulation_data_range()
def get_etf_holdings(ticker: str, limit: int = 125, _simulation_date: Optional[datetime] = None) -> str:
    """Get ETF holdings showing portfolio composition and top positions.

    Args:
        ticker: ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')
        limit: Maximum number of holdings to return (default: 25, max: 100)
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        YAML string with success status and holdings data including:
        - Ticker symbol of each holding
        - Company name
        - Weight in portfolio (%)
        - Number of shares held
        - Market value
    """
    try:
        # Repository function returns all holdings, we limit here
        data = _get_etf_holdings(ticker)
        df = pd.DataFrame(data['items'])
        df = df.drop(columns=['isin', 'securityCusip', 'updatedAt'])
        df['sharesNumber'] = df['sharesNumber'].astype(int)
        df['marketValue'] = df['marketValue'].astype(int)

        # Sort by weight descending and get top limit values
        df = df.sort_values('weightPercentage', ascending=False).head(limit)

        data = df.to_dict(orient='records')

        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to retrieve ETF holdings for {ticker}: {str(e)}")


GET_ETF_HOLDINGS_DESCRIPTION = (
    "Retrieve ETF portfolio holdings showing top positions and their weights. "
    "Returns detailed breakdown of what stocks/assets the ETF holds and their portfolio allocation.\n\n"
    "**Data Returned (for each holding):**\n"
    "  - Ticker symbol\n"
    "  - Company/asset name\n"
    "  - Portfolio weight (%)\n"
    "  - Number of shares held\n"
    "  - Market value of position\n\n"
    "**Use Cases:**\n"
    "  - Analyze ETF portfolio composition\n"
    "  - Identify top holdings and concentration risk\n"
    "  - Compare holdings across similar ETFs\n"
    "  - Understand sector/industry exposure through holdings\n"
    "  - Check for overlap with existing portfolio positions\n\n"
    "**Examples:**\n"
    "  get_etf_holdings(ticker='SPY', limit=10)  # Top 10 holdings of S&P 500 ETF\n"
    "  get_etf_holdings(ticker='QQQ', limit=25)  # Top 25 holdings of Nasdaq-100 ETF\n"
    "  get_etf_holdings(ticker='XLF')            # Default 25 holdings of Financial sector ETF"
)

GET_ETF_HOLDINGS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "The ETF ticker symbol. For example, 'SPY', 'QQQ', 'VTI', etc.",
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of holdings to return. Default is 25. Maximum is 100.",
            "default": 25,
            "minimum": 1,
            "maximum": 100
        }
    },
    "required": ["ticker"],
}

GET_ETF_HOLDINGS_TOOL = {
    "name": "get_etf_holdings",
    "description": GET_ETF_HOLDINGS_DESCRIPTION,
    "parameters": GET_ETF_HOLDINGS_PARAMETERS,
    "function": get_etf_holdings,
}
