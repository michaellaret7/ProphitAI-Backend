from app.utils.decorators.database import with_session
from app.db.core.market_data_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.token_count import get_token_count

@with_session('market')
def get_group_tickers(group_type: str, group_value: str, session=None):
    tickers = session.query(Ticker).filter(getattr(Ticker, group_type) == group_value).all()
    tickers = [serialize_sqlalchemy_obj(ticker) for ticker in tickers]
    for ticker in tickers:
        ticker.pop('id')
        ticker.pop('last_updated')
        ticker.pop('industry')
        ticker.pop('sub_industry')
        ticker.pop('is_etf')
        ticker.pop('sector')
        ticker.pop('price')
        ticker.pop('avg_volume')
        ticker.pop('dollar_volume')
    return tickers

if __name__ == "__main__":
    print(get_token_count(get_group_tickers("industry", "equity_etfs")))
    print(get_token_count(get_group_tickers("sector", "etf")))
    print(get_group_tickers("industry", "equity_etfs"))
