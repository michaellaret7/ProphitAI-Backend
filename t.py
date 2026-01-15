"""Script to print unique ETF industries and subindustries."""

from app.db.core.db_config import MarketSession, UserSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.user_data_models import Portfolio, PortfolioItem

with UserSession() as session:
    portfolio = session.query(Portfolio).all()
    for p in portfolio:
        if p.alert_state['drawdown']['result']['triggered'] == False:
            print(p.alert_state)
            break