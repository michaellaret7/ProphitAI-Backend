import yaml
from app.db.core.models.user_data_models import Portfolio
from app.utils.decorators.database import with_session

@with_session('user')
def get_user_portfolio(portfolio_id: str, session=None):
    """
    Retrieve portfolio positions from database by portfolio_id.

    Args:
        portfolio_id: UUID of the portfolio to retrieve
        session: Database session (injected by decorator)

    Returns:
        YAML string with portfolio positions
    """
    try:
        # Query portfolio positions by portfolio_id
        portfolio_positions = session.query(Portfolio).filter(
            Portfolio.portfolio_id == portfolio_id
        ).all()

        if not portfolio_positions:
            return yaml.dump({
                "success": False,
                "error": f"No portfolio found with id: {portfolio_id}"
            }, default_flow_style=False)

        positions = {}
        for position in portfolio_positions:
            positions[position.ticker] = {
                "ticker": position.ticker,
                "sector": position.sector,
                "industry": position.industry,
                "sub_industry": position.sub_industry,
                "allocation": position.allocation/100,
                "portfolio": position.name,
                "supporting_metrics": position.supporting_metrics,
                "reason_for_rec": position.reason_for_rec,
                "position": "long"  # Default to long, adjust if you have this field in DB
            }

        session.close()

        return yaml.dump({"success": True, "data": positions}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


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
