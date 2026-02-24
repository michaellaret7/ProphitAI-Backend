"""ETF holdings tool.

Retrieves top holdings by weight for an ETF, showing portfolio composition
and position details.
"""

from typing import Annotated

import pandas as pd

from app.core.atlas.tools_v2.decorator import agent_tool, Param
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.repositories.etf_data import get_etf_holdings as _fetch_etf_holdings


# ================================
# --> Tools
# ================================

@agent_tool(name="get_etf_holdings")
def get_etf_holdings(
    ticker: str,
    limit: Annotated[int, Param(min_val=1, max_val=100)] = 25,
) -> str:
    """
    Retrieve ETF portfolio holdings showing top positions and their weights.

    Returns a detailed breakdown of what stocks/assets the ETF holds and their
    portfolio allocation, sorted by weight descending.

    **Data Returned (per holding):**
    - asset: Holding ticker symbol
    - name: Company/asset name
    - weightPercentage: Portfolio weight (%)
    - sharesNumber: Number of shares held
    - marketValue: Market value of position

    **Use Cases:**
    - Analyze ETF portfolio composition and concentration
    - Identify top holdings and concentration risk
    - Compare holdings across similar ETFs
    - Understand sector/industry exposure through holdings
    - Check for overlap with existing portfolio positions

    Args:
        ticker: ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')
        limit: Maximum number of holdings to return (1-100, default: 25)

    Returns:
        List of holding dicts sorted by weight descending

    Examples:
        get_etf_holdings(ticker='SPY', limit=10)
        >>> {"success": True, "data": [{"asset": "AAPL", "name": "Apple Inc.", "weightPercentage": 7.2, ...}, ...]}

        get_etf_holdings(ticker='QQQ')
        >>> {"success": True, "data": [{"asset": "MSFT", ...}, {"asset": "AAPL", ...}, ...]}
    """
    try:
        data = _fetch_etf_holdings(ticker.upper())
        if not data.get("items"):
            return error_response(f"No holdings found for ETF {ticker.upper()}")

        df = pd.DataFrame(data["items"])
        df = df.drop(columns=["isin", "securityCusip", "updatedAt"])
        df["sharesNumber"] = df["sharesNumber"].astype(int)
        df["marketValue"] = df["marketValue"].astype(int)
        df = df.sort_values("weightPercentage", ascending=False).head(limit)

        return success_response(df.to_dict(orient="records"))
    except Exception as e:
        return error_response(f"Failed to retrieve ETF holdings for {ticker}: {str(e)}")
