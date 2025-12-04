from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.utils.serialize_output import serialize_sqlalchemy_obj

with MarketSession() as session:
    tickers = session.query(Ticker).filter(Ticker.ticker == "NXT").first()
    print(serialize_sqlalchemy_obj(tickers))