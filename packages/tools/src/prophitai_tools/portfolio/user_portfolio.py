"""User portfolio retrieval tool.

Loads a user's simulated portfolio from the database by portfolio UUID,
enriching each position with sector/industry metadata from the market DB.
"""

import uuid

from sqlalchemy.orm import joinedload

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.db.config import UserSession, MarketSession
from prophitai_data.db.models.user import Portfolio
from prophitai_data.db.models.market import Ticker


# ================================
# --> Tools
# ================================

@agent_tool(name="get_user_simulated_portfolio", category="portfolio")
def get_user_simulated_portfolio(
    portfolio_id: str,
) -> str:
    """Retrieve a user's simulated portfolio from the database by portfolio UUID.

Returns position details including allocation, GICS classification, supporting
metrics, and recommendation rationale for each holding.

    Args:
        portfolio_id: UUID string of the portfolio to retrieve
            (e.g., 'a1b2c3d4-e5f6-7890-abcd-ef1234567890')

    Returns:
        YAML-formatted portfolio keyed by ticker:
        - ticker: Stock symbol
        - sector, industry, sub_industry: GICS classification
        - allocation: Position weight as decimal (0.25 = 25%)
        - portfolio: Portfolio name
        - supporting_metrics: Key metrics supporting the position
        - reason_for_rec: Rationale for the recommendation
        - position: Position direction (always "long")

    Examples:
        get_user_simulated_portfolio(portfolio_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    Raises:
        Exception: If portfolio_id is invalid UUID or portfolio not found
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
