from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

sectors = []
industries = []
sub_industries = []
with MarketSession() as session:
    valid_sectors = session.query(Ticker.sector).distinct().filter(Ticker.sector != 'etf').all()
    for sector in valid_sectors:
        sectors.append(sector[0])

    valid_industries = session.query(Ticker.industry).distinct().filter(Ticker.sector != 'etf').all()
    for industry in valid_industries:
        industries.append(industry[0])

    valid_sub_industries = session.query(Ticker.sub_industry).distinct().filter(Ticker.sector != 'etf').all()
    for sub_industry in valid_sub_industries:
        sub_industries.append(sub_industry[0])


