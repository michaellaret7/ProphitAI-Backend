from app.db.core.db_config import MarketSession, UserSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.user_data_models import *
from app.utils.serialize_output import serialize_sqlalchemy_obj

u_session = UserSession()
m_session = MarketSession()

portfolios = u_session.query(Portfolio).all()

for portfolio in portfolios:
    nav = sum(item.position_nav or 0 for item in portfolio.items)
    print(f"Portfolio {portfolio.name} NAV: {nav}")
    portfolio.nav = nav
    u_session.commit()
    print("--------------------------------")

u_session.close()
m_session.close()
