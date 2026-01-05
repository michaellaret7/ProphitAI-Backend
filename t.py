from app.db.core.db_config import MarketSession, ProphitAltsSession, UserSession
from app.db.core.models.market_data_models import Ticker, BalanceSheet, Price, DailyPrices
from app.db.core.models.user_data_models import Company, User, PortfolioItem, Portfolio
from app.utils.serialize_output import serialize_sqlalchemy_obj
import uuid
from sqlalchemy.orm import selectinload
import time
import pandas as pd

with UserSession() as session:
    portfolio = session.query(Portfolio).filter(Portfolio.id == 'd3445586-64bd-45dd-b696-82c3e90efe63').first()

    print(serialize_sqlalchemy_obj(portfolio))

    positions = []
    for item in portfolio.items:
        print(serialize_sqlalchemy_obj(item))

with MarketSession() as session:
    ticker = session.query(Ticker).filter(Ticker.ticker == 'BN').first()
    print(serialize_sqlalchemy_obj(ticker))