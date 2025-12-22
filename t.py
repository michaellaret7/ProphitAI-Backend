from app.db.core.db_config import MarketSession, ProphitAltsSession, UserSession
from app.db.core.models.market_data_models import Ticker, BalanceSheet, Price
from app.db.core.models.user_data_models import Company, User, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj

with MarketSession() as session:
    results = session.query(Ticker.industry, Ticker.sub_industry).filter(
        Ticker.sector == 'equity_sector_materials'
    ).distinct().all()
    
    print("Technology Sector - Industries & Sub-Industries:\n")
    for industry, sub_industry in sorted(results, key=lambda x: (x[0] or '', x[1] or '')):
        print(f"Industry: {industry} | Sub-Industry: {sub_industry}")

    tickers = session.query(Ticker).filter(Ticker.ticker == 'AEM').first()
    print(serialize_sqlalchemy_obj(tickers))
