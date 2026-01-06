from app.db.core.db_config import MarketSession, UserSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.user_data_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj

u_session = UserSession()
m_session = MarketSession()

portfolio = u_session.query(Portfolio).filter(Portfolio.id == "30b60287-c277-4437-a539-660bf2d27ba4").first()

print(f"Portfolio {portfolio.name} NAV: {portfolio.nav}")
for pos in portfolio.items:
    print(f"Ticker: {pos.ticker} Allocation: {pos.allocation} Position NAV: {pos.position_nav}")

u_session.close()
m_session.close()
