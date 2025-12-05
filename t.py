from concurrent.futures import ThreadPoolExecutor, as_completed
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.serialize_output import serialize_sqlalchemy_obj

with MarketSession() as session:
    sectors = {row[0] for row in session.query(Ticker.sector).distinct().filter(Ticker.is_etf == False).all()}
    print(sectors)

    industries = {row[0] for row in session.query(Ticker.industry).distinct().filter(Ticker.is_etf == False).all()}
    print(industries)

    sub_industries = {row[0] for row in session.query(Ticker.sub_industry).distinct().filter(Ticker.is_etf == False).all()}
    print(sub_industries)


