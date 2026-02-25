"""Ticker and ETF information tools.

Provides tools for retrieving comprehensive ticker and ETF metadata
and characteristics from the database.
"""

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.repositories.etf_data import get_etf_info as _get_etf_info


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ticker_info")
def get_ticker_info(
    ticker: str,
) -> str:
    """
    Retrieve comprehensive ticker information including company metadata
    and characteristics.

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
        ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'JPM')

    Returns:
        Comprehensive ticker profile including company name, description,
        sector/industry classification, valuation metrics, and liquidity data

    Examples:
        get_ticker_info(ticker='AAPL')
        >>> {"success": True, "data": {"ticker": "AAPL", "ticker_name": "Apple Inc.", ...}}

        get_ticker_info(ticker='JPM')
        >>> {"success": True, "data": {"ticker": "JPM", "ticker_name": "JPMorgan Chase & Co.", ...}}

    Raises:
        Exception: If ticker is not found in the database
    """
    try:
        with MarketSession() as session:
            ticker_obj = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
            if not ticker_obj:
                return error_response(f"Ticker {ticker.upper()} not found")
            return success_response(serialize_sqlalchemy_obj(ticker_obj))
    except Exception as e:
        return error_response(f"Failed to retrieve ticker info for {ticker}: {str(e)}")



@agent_tool(name="get_etf_info")
def get_etf_info(
    ticker: str,
) -> str:
    """
    Retrieve comprehensive ETF information including metadata, characteristics,
    and investment focus.

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
        ticker: ETF ticker symbol (e.g., 'SPY', 'QQQ', 'VTI')

    Returns:
        ETF profile including name, description, issuer, expense ratio,
        AUM, inception date, sector focus, and asset class

    Examples:
        get_etf_info(ticker='SPY')
        >>> {"success": True, "data": {"name": "SPDR S&P 500 ETF Trust", "expenseRatio": 0.0945, ...}}

        get_etf_info(ticker='QQQ')
        >>> {"success": True, "data": {"name": "Invesco QQQ Trust", ...}}

    Raises:
        Exception: If ETF ticker is not found
    """
    try:
        data = _get_etf_info(ticker.upper())
        return success_response(data)
    except Exception as e:
        return error_response(f"Failed to retrieve ETF info for {ticker}: {str(e)}")



