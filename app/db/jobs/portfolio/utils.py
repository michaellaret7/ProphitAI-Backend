from typing import Dict
from sqlalchemy.orm import Session
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

def classify_and_add_tickers(positions: Dict[str, float], session: Session) -> Dict[str, float]:
    """Classify tickers into buckets. positions = {ticker: allocation}"""

    equities = {}
    fixed_income = {}
    commodities = {}
    cryptocurrencies = {}
    alternatives = {}

    ticker_objs = session.query(Ticker).filter(Ticker.ticker.in_(positions.keys())).all()
    ticker_map = {t.ticker: (t.sector, t.industry, t.sub_industry) for t in ticker_objs}

    for ticker, allocation in positions.items():
        sector, industry, sub_industry = ticker_map.get(ticker, (None, None, None))
        if sector and sector.startswith('equity_sector_'):
            equities[ticker] = allocation
        if industry == 'equity_etfs':
            equities[ticker] = allocation
        if industry == 'fixed_income_etfs':
            fixed_income[ticker] = allocation
        if industry == 'commodity_etfs':
            commodities[ticker] = allocation
        if industry == 'cryptocurrency_etfs':
            cryptocurrencies[ticker] = allocation
        if industry == 'alternative_etfs':
            alternatives[ticker] = allocation
    
    allocations = {}
    if equities:
        allocations['equities'] = sum(equities.values())
    if fixed_income:
        allocations['fixed_income'] = sum(fixed_income.values())
    if commodities:
        allocations['commodities'] = sum(commodities.values())
    if cryptocurrencies:
        allocations['cryptocurrencies'] = sum(cryptocurrencies.values())
    if alternatives:
        allocations['alternatives'] = sum(alternatives.values())

    return allocations

if __name__ == "__main__":
    with MarketSession() as session:
        fake_positions = {'BND': 0.0812153836801942, 'DUK': 0.0812153836801942, 'GOOGL': 0.08529267527087245, 'JNJ': 0.08095840367934576, 'JPM': 0.0828207422920126, 'LRCX': 0.09603618552924603, 'MSFT': 0.0825211381950795, 'MU': 0.08877121155879275, 'NEE': 0.0806410991697794, 'NVDA': 0.08019195150488809, 'TER': 0.08484535775557836, 'AAPL': 0.07828939802032579, 'ABBV': 0.0784164533438851}
        allocations = classify_and_add_tickers(fake_positions, session)
        print(allocations)
        print(f"Total Allocation: {sum(allocations.values())}")
