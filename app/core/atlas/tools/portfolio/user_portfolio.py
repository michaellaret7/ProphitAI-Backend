"""User portfolio retrieval tool.

Loads a user's simulated portfolio from the database by portfolio UUID,
enriching each position with sector/industry metadata from the market DB.
"""

import uuid

from sqlalchemy.orm import joinedload

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.user_data_models import Portfolio
from app.db.core.models.market_data_models import Ticker


# ================================
# --> Tools
# ================================

@agent_tool(name="get_user_simulated_portfolio")
def get_user_simulated_portfolio(
    portfolio_id: str,
) -> str:
    """
    Retrieve a user's simulated portfolio from the database by portfolio UUID.

    Returns a dictionary keyed by ticker symbol with position details including
    allocation, sector/industry classification, supporting metrics, and recommendation
    rationale.

    **Data Returned (per position):**
    - ticker: Stock ticker symbol
    - sector, industry, sub_industry: GICS classification hierarchy
    - allocation: Position weight as decimal (0.25 = 25%)
    - portfolio: Portfolio name
    - supporting_metrics: Key metrics supporting the position
    - reason_for_rec: Rationale for the recommendation
    - position: Position direction (always "long")

    **Use Cases:**
    - Portfolio Analysis: Load current user holdings for review
    - Optimization Input: Use as base portfolio for rebalancing or optimization
    - Allocation Review: Understand position sizes and sector exposure
    - Performance Attribution: Map holdings to sectors for attribution analysis

    Args:
        portfolio_id: UUID string of the portfolio to retrieve

    Returns:
        Dictionary keyed by ticker with position details

    Examples:
        get_user_simulated_portfolio(portfolio_id='a1b2c3d4-e5f6-...')
        >>> {"success": True, "data": {"AAPL": {"ticker": "AAPL", "allocation": 0.15, ...}, ...}}

    Raises:
        Exception: If portfolio_id is invalid or portfolio not found
    """
    try:
        portfolio_uuid = uuid.UUID(portfolio_id)

        with UserSession() as user_session:
            portfolio = user_session.query(Portfolio).options(
                joinedload(Portfolio.items)
            ).filter(Portfolio.id == portfolio_uuid).first()

            if not portfolio:
                return error_response(f"No portfolio found with id: {portfolio_id}")

            tickers_in_portfolio = [item.ticker for item in portfolio.items]

        # Reason: separate session for market data to avoid cross-DB session issues
        with MarketSession() as market_session:
            ticker_data = market_session.query(Ticker).filter(
                Ticker.ticker.in_(tickers_in_portfolio)
            ).all()
            ticker_map = {t.ticker: t for t in ticker_data}

        positions = {}
        for item in portfolio.items:
            ticker_info = ticker_map.get(item.ticker)
            positions[item.ticker] = {
                "ticker": item.ticker,
                "sector": ticker_info.sector if ticker_info else None,
                "industry": ticker_info.industry if ticker_info else None,
                "sub_industry": ticker_info.sub_industry if ticker_info else None,
                "allocation": item.allocation,
                "portfolio": portfolio.name,
                "supporting_metrics": item.supporting_metrics,
                "reason_for_rec": item.reason_for_rec,
                "position": "long",
            }

        return success_response(positions)
    except ValueError:
        return error_response(f"Invalid portfolio UUID: {portfolio_id}")
    except Exception as e:
        return error_response(f"Failed to retrieve portfolio: {str(e)}")
