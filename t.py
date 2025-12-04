from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

with MarketSession() as session:
    valid_industries = {row[0] for row in session.query(Ticker.industry).distinct().filter(Ticker.is_etf == True).all()}
    valid_sub_industries = {row[0] for row in session.query(Ticker.sub_industry).distinct().filter(Ticker.is_etf == True).all()}

print(valid_industries)
print(valid_sub_industries)