from app.db.core.db_config import MarketSession, ProphitAltsSession, UserSession
from app.db.core.models.market_data_models import Ticker, BalanceSheet, Price
from app.db.core.models.user_data_models import Company, User, PortfolioItem, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj
import uuid
# with MarketSession() as session:
#     for sector in ['equity_sector_information_technology', 'equity_sector_health_care', 'equity_sector_financials', 'equity_sector_consumer_discretionary', 'equity_sector_consumer_staples', 'equity_sector_industrials', 'equity_sector_communication_services', 'equity_sector_energy', 'equity_sector_materials', 'equity_sector_utilities', 'equity_sector_real_estate']:
#         results = session.query(Ticker.industry, Ticker.sub_industry).filter(
#             Ticker.sector == sector
#         ).distinct().all()
        
#         print(f"\n{sector} Sector - Industries & Sub-Industries:\n")
#         for industry, sub_industry in sorted(results, key=lambda x: (x[0] or '', x[1] or '')):
#             print(f"  Industry: {industry} | Sub-Industry: {sub_industry}")


