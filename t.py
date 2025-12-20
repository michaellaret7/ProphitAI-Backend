from app.db.core.db_config import MarketSession, ProphitAltsSession, UserSession
from app.db.core.models.market_data_models import Ticker, BalanceSheet
from app.db.core.models.user_data_models import Company, User, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj

with MarketSession() as session:
    tickers = session.query(Ticker).filter(Ticker.ticker == 'NVDA').first()
    balance_sheets = session.query(BalanceSheet).filter(BalanceSheet.ticker_id == tickers.id).order_by(BalanceSheet.date.desc()).first()
    print(serialize_sqlalchemy_obj(balance_sheets))


with UserSession() as session:
    company = session.query(Company).all()
    for c in company:
        print(serialize_sqlalchemy_obj(c))
