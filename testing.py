from app.db.core.db_config import UserSession, MarketSession, ProphitAltsSession
from app.db.core.models.user_data_models import Portfolio
from app.db.core.models.market_data_models import Ticker
from app.utils.decorators.database import with_session
from app.utils.serialize_output import serialize_sqlalchemy_obj

@with_session('user')
def print_all_portfolios(session=None):
    portfolios = session.query(Portfolio).all()
    for portfolio in portfolios:
        print(serialize_sqlalchemy_obj(portfolio))

@with_session('market')
def print_all_stocks(session=None):
    stocks = session.query(Ticker).filter(Ticker.industry == 'automobiles').all()
    for stock in stocks:
        print(stock.ticker)

# print_all_portfolios()
print_all_stocks()