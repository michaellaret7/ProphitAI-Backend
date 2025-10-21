from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *

list = ['SPIB', 'STOT', 'PRIV', 'TOTL', 'HYBL']

session = MarketSession()
for ticker in list:
    x = session.query(Ticker).filter(Ticker.ticker == ticker).first()
    if x == None:
        print(f"Ticker {ticker} not found")
    else:
        print(f"Ticker {ticker} found")
session.close()