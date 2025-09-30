import yaml
from app.db.core.prophit_alts_models import FundInitialPosition, Fund
from app.db.core.market_data_models import Ticker
from app.utils.decorators.database import with_sessions
from app.db.core.db_config import ProphitAltsSession, MarketSession

def get_analyst_picks() -> str:
    try:
        session = ProphitAltsSession()
        initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

        initial_positions_dict = {}
        for position in initial_positions:
            initial_positions_dict[position.ticker_name] = {
                "position": position.position.value,
                "industry": position.industry,
                "conviction": position.conviction,
                "reasoning": position.reasoning
            }

        session.close()

        return yaml.dump({"success": True, "data": initial_positions_dict}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

def pull_rest_of_ticker_pool() -> str:
    try:
        session = ProphitAltsSession()
        market_session = MarketSession()

        ticker_pool = session.query(FundInitialPosition).all()

        tickers = []
        for position in ticker_pool:
            tickers.append(position.ticker_name)

        ticker_pool_list = []

        rest_of_ticker_pool = market_session.query(Ticker).filter(
            Ticker.ticker.notin_(tickers),
            Ticker.sector == "equity_sector_consumer_staples",
            Ticker.market_cap > 600_000_000
        ).all()

        for ticker in rest_of_ticker_pool:
            ticker_pool_list.append(ticker.ticker)

        session.close()
        market_session.close()

        return yaml.dump({"success": True, "data": ticker_pool_list}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
GET_ANALYST_PICKS_DESCRIPTION = (
    "Retrieve initial analyst picks for the Consumer Staples Fund. (These picks are not a portfolio, they are the analyst picks and their conviction levels)"
    "Returns a dictionary with tickers as keys and position details including position type "
    "(long/short), industry, conviction level, and reasoning.\n\n"
    "Example: get_analyst_picks()"
)

GET_ANALYST_PICKS_PARAMETERS = {
    "type": "object",
    "properties": {}
}

GET_ANALYST_PICKS_TOOL = {
    "name": "get_analyst_picks",
    "description": GET_ANALYST_PICKS_DESCRIPTION,
    "parameters": GET_ANALYST_PICKS_PARAMETERS,
    "function": get_analyst_picks,
}

# ------------------------------------------------------------- #

PULL_REST_OF_TICKER_POOL_DESCRIPTION = (
    "Return remaining consumer staples tickers not already in fund initial positions, "
    "filtered by sector and minimum market cap."
)

PULL_REST_OF_TICKER_POOL_PARAMETERS = {
    "type": "object",
    "properties": {},
}

PULL_REST_OF_TICKER_POOL_TOOL = {
    "name": "pull_rest_of_ticker_pool",
    "description": PULL_REST_OF_TICKER_POOL_DESCRIPTION,
    "parameters": PULL_REST_OF_TICKER_POOL_PARAMETERS,
    "function": pull_rest_of_ticker_pool,
}



if __name__ == "__main__":
    print(get_analyst_picks())
    print(pull_rest_of_ticker_pool())