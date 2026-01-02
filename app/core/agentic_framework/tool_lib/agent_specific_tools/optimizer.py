from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.db.core.models.user_data_models import Portfolio
from app.db.core.models.market_data_models import Ticker
from app.utils.decorators.database import with_sessions
from sqlalchemy.orm import joinedload
import uuid


@with_sessions(user_session='user', market_session='market')
def get_user_portfolio(portfolio_id: str, user_session=None, market_session=None):
    """
    Retrieve portfolio positions from database by portfolio_id.

    Args:
        portfolio_id: UUID of the portfolio to retrieve
        user_session: User database session (injected by decorator)
        market_session: Market database session (injected by decorator)

    Returns:
        YAML string with portfolio positions
    """
    try:
        # Query portfolio with items eagerly loaded
        portfolio = user_session.query(Portfolio).options(
            joinedload(Portfolio.items)
        ).filter(Portfolio.id == uuid.UUID(portfolio_id)).first()

        if not portfolio:
            return error_response(f"No portfolio found with id: {portfolio_id}")

        # Batch fetch ticker metadata
        tickers_in_portfolio = [item.ticker for item in portfolio.items]
        ticker_data = market_session.query(Ticker).filter(
            Ticker.ticker.in_(tickers_in_portfolio)
        ).all()
        ticker_map = {t.ticker: t for t in ticker_data}

        # Build positions dict
        positions = {}
        for item in portfolio.items:
            ticker_info = ticker_map.get(item.ticker)
            positions[item.ticker] = {
                "ticker": item.ticker,
                "sector": ticker_info.sector if ticker_info else None,
                "industry": ticker_info.industry if ticker_info else None,
                "sub_industry": ticker_info.sub_industry if ticker_info else None,
                "allocation": item.allocation,  # Already decimal (0.25 = 25%)
                "portfolio": portfolio.name,
                "supporting_metrics": item.supporting_metrics,
                "reason_for_rec": item.reason_for_rec,
                "position": "long"  # Default to long
            }

        return success_response(positions)
    except Exception as e:
        return error_response(e)


# Tool Schema Constants
GET_USER_PORTFOLIO_DESCRIPTION = (
    "Retrieve user portfolio data from the database by portfolio_id. "
    "Returns a dictionary with ticker symbols as keys and position details including "
    "ticker, sector, industry, sub_industry, allocation (as decimal), portfolio name, "
    "supporting_metrics, and reason_for_rec. "
    "REQUIRED PARAMETERS: portfolio_id (string) - UUID of the portfolio to retrieve. "
    "WHEN TO USE: (1) Portfolio analysis - get current user holdings, (2) Optimization input - use as base for portfolio optimization, (3) Allocation review - understand current position sizes and sectors."
)

GET_USER_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_id": {
            "type": "string",
            "description": "UUID of the portfolio to retrieve from the database"
        }
    },
    "required": ["portfolio_id"],
    "additionalProperties": False
}

GET_USER_PORTFOLIO_TOOL = {
    "name": "get_user_portfolio",
    "description": GET_USER_PORTFOLIO_DESCRIPTION,
    "parameters": GET_USER_PORTFOLIO_PARAMETERS,
    "function": get_user_portfolio,
}
