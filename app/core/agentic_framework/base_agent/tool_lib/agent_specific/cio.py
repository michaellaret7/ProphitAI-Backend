from app.db.core.prophit_alts_models import FundInitialPosition, Fund
from app.db.core.market_data_models import Ticker
from app.utils.decorators.database import with_session, with_sessions

@with_session('prophit')
def get_analyst_picks(session=None):
    initial_positions = session.query(FundInitialPosition).join(Fund).filter(Fund.fund_name == "consumer_staples_fund").all()

    initial_positions_dict = {}
    for position in initial_positions:
        initial_positions_dict[position.ticker_name] = {
            "position": position.position.value,
            "industry": position.industry,
            "conviction": position.conviction,
            "reasoning": position.reasoning
        }

    return initial_positions_dict

@with_sessions('prophit', 'market')
def pull_rest_of_ticker_pool(session=None, market_session=None):
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

    return ticker_pool_list



