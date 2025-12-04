from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj


with MarketSession() as session:
    tickers = session.query(Ticker).filter(Ticker.is_etf == False).all()

    for ticker in tickers:
        ticker = serialize_sqlalchemy_obj(ticker)
        print(ticker['ticker'])
        print(ticker['ticker_name'])
        print(ticker['ticker_description'])
        print('--------------------------------')
