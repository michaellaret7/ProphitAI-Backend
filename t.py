from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Price, Ticker, DailyPrices
from prophitai_data.db.utils import serialize_sqlalchemy_obj

session = MarketSession()

prices = session.query(Ticker).filter(Ticker.ticker == "AAPL").first()

session.close()

print(serialize_sqlalchemy_obj(prices))