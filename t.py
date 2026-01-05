from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

with MarketSession() as session:
    results = session.query(Ticker.industry, Ticker.sub_industry).filter(
        Ticker.sector == 'equity_sector_consumer_discretionary'
    ).distinct().all()
    
    for industry, sub_industry in results:
        print(f"Industry: {industry}, Sub-Industry: {sub_industry}")