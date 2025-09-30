import yaml
from app.db.core.user_data_models import Portfolio, User
from app.utils.decorators.database import with_session

@with_session('user')
def get_user_portfolio(session=None):
    try:
        email = "michaellaret7@gmail.com"
        user = session.query(User).filter(User.email == email).first().id
        portfolio = session.query(Portfolio).filter(Portfolio.user_id == user, Portfolio.name == "Auto/Tech and ETF focused Portfolio").all()

        positions = {}
        for position in portfolio:
            positions[position.ticker] = {
                "ticker": position.ticker,
                "sector": position.sector,
                "industry": position.industry,
                "sub_industry": position.sub_industry,
                "allocation": position.allocation/100,
                "portfolio": position.name,
                "supporting_metrics": position.supporting_metrics,
                "reason_for_rec": position.reason_for_rec
            }

        session.close()

        return yaml.dump({"success": True, "data": positions}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
GET_USER_PORTFOLIO_DESCRIPTION = (
    "Retrieve user portfolio data from the database for the specified user email. "
    "Returns a dictionary with ticker symbols as keys and position details including "
    "ticker, sector, industry, sub_industry, allocation (as decimal), portfolio name, "
    "supporting_metrics, and reason_for_rec. "
    "NO PARAMETERS REQUIRED: This tool takes no arguments and should be called with empty parameters '{}'. "
    "WHEN TO USE: (1) Portfolio analysis - get current user holdings, (2) Optimization input - use as base for portfolio optimization, (3) Allocation review - understand current position sizes and sectors."
)

GET_USER_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False
}

GET_USER_PORTFOLIO_TOOL = {
    "name": "get_user_portfolio",
    "description": GET_USER_PORTFOLIO_DESCRIPTION,
    "parameters": GET_USER_PORTFOLIO_PARAMETERS,
    "function": get_user_portfolio,
}
