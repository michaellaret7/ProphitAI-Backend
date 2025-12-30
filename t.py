from app.db.core.db_config import MarketSession, ProphitAltsSession, UserSession
from app.db.core.models.market_data_models import Ticker, BalanceSheet, Price, DailyPrices
from app.db.core.models.user_data_models import Company, User, PortfolioItem, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj
import uuid
from sqlalchemy.orm import selectinload
import time
import pandas as pd

# start_time = time.time()
# m_session = MarketSession()

# tickers = ["AAPL","MSFT","NVDA","TSLA","GOOG","AMZN","META","IBM","ORCL"]

# ticker_ids = [
#     t[0] for t in (
#         m_session.query(Ticker.id)
#         .filter(Ticker.ticker.in_(tickers))
#         .all()
#     )
# ]

# rows = (
#     m_session.query(DailyPrices)
#     .filter(DailyPrices.ticker_id.in_(ticker_ids))
#     .order_by(DailyPrices.ticker_id, DailyPrices.datetime)
#     .all()
# )




# m_session.close()
# end_time = time.time()
# print(f"Time taken: {end_time - start_time} seconds")
# print(len(rows))


from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, DailyPrices


m_session = MarketSession()

df = pd.read_sql(
    m_session.query(DailyPrices)
    .join(Ticker)
    .filter(Ticker.ticker == "APP")
    .order_by(DailyPrices.datetime.desc())
    .statement,
    m_session.bind
)

m_session.close()

print(df)