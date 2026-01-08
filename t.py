"""Quick script to print all ETF industries and their unique sub-industries"""
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import ETFScreener, Ticker
from sqlalchemy import distinct
from collections import defaultdict

session = MarketSession()

etfs = session.query(Ticker).filter(Ticker.ticker == "QQQM").all()

print(etfs[0].ticker)