"""Ticker and ETF information tools.

Provides tools for retrieving comprehensive ticker and ETF metadata
and characteristics from the database. Supports batched multi-ticker calls.
"""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Ticker
from prophitai_data.db.utils import serialize_sqlalchemy_obj
from prophitai_data.repositories.etf import get_etf_info as _get_etf_info_repo


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ticker_info", category="ticker_info")
def get_ticker_info(
    tickers: list[str],
) -> str:
    """
    Retrieve comprehensive ticker information including company metadata
    and characteristics for one or more tickers.

    Returns detailed stock profile data from the database for fundamental analysis.

    **Data Returned:**
    - ticker, ticker_name: Symbol and full company name
    - ticker_description: Business description and company overview
    - sector, industry, sub_industry: GICS classification hierarchy
    - market_cap: Market capitalization
    - price, beta, eps, pe: Current price and key valuation metrics
    - dollar_volume, avg_volume: Liquidity metrics
    - is_etf: Whether the ticker is an ETF
    - exchange, currency, country: Trading venue and geography

    **Use Cases:**
    - Company Overview: Get a quick snapshot of a stock's profile
    - Classification Lookup: Identify sector/industry for peer comparison
    - Eligibility Check: Verify if ticker is actively traded and meets criteria
    - Pre-Analysis: Gather context before deeper fundamental analysis
    - Portfolio Mapping: Determine sector/industry exposure for holdings

    Args:
        tickers: List of stock ticker symbols (e.g., ['AAPL', 'MSFT', 'JPM'])

    Returns:
        Comprehensive ticker profiles including company name, description,
        sector/industry classification, valuation metrics, and liquidity data

    Examples:
        get_ticker_info(tickers=['AAPL', 'JPM'])
        >>> {"success": True, "data": {"results": {"AAPL": {...}, "JPM": {...}}, "errors": {}}}

    Raises:
        Exception: If database query fails
    """
    tickers = [t.upper().strip() for t in tickers]

    results: dict = {}
    errors: dict = {}

    try:
        with MarketSession() as session:
            rows = (
                session.query(Ticker)
                .filter(Ticker.ticker.in_(tickers))
                .all()
            )

            # Reason: build lookup by ticker symbol for O(1) access
            row_map = {r.ticker: r for r in rows}

            for t in tickers:
                if t not in row_map:
                    errors[t] = f"Ticker {t} not found"
                    continue
                results[t] = serialize_sqlalchemy_obj(row_map[t])

    except Exception as e:
        return error_response(f"Failed to retrieve ticker info: {str(e)}")

    return success_response({"results": results, "errors": errors})


@agent_tool(name="get_etf_info", category="ticker_info")
def get_etf_info(
    tickers: list[str],
) -> str:
    """
    Retrieve comprehensive ETF information including metadata, characteristics,
    and investment focus for one or more ETFs.

    Returns detailed information about the ETF's structure, costs, and
    investment strategy.

    **Data Returned:**
    - Basic info: name, description, issuer/provider
    - Characteristics: expense ratio, AUM (assets under management), inception date
    - Investment focus: sector focus, asset class, geographic region
    - Trading info: exchange, currency

    **Use Cases:**
    - Compare ETF expense ratios and costs
    - Understand ETF investment strategy and focus
    - Research ETF providers and fund size
    - Validate ETF characteristics before portfolio inclusion

    Args:
        tickers: List of ETF ticker symbols (e.g., ['SPY', 'QQQ', 'VTI'])

    Returns:
        ETF profiles including name, description, issuer, expense ratio,
        AUM, inception date, sector focus, and asset class

    Examples:
        get_etf_info(tickers=['SPY', 'QQQ'])
        >>> {"success": True, "data": {"results": {"SPY": {...}, "QQQ": {...}}, "errors": {}}}

    Raises:
        Exception: If database query fails
    """
    tickers = [t.upper().strip() for t in tickers]

    results: dict = {}
    errors: dict = {}

    try:
        etf_map = _get_etf_info_repo(tickers)

        for t in tickers:
            data = etf_map.get(t, {"ticker": t, "found": False})
            if not data.get("found", False):
                errors[t] = f"ETF {t} not found"
                continue
            results[t] = data

    except Exception as e:
        return error_response(f"Failed to retrieve ETF info: {str(e)}")

    return success_response({"results": results, "errors": errors})
