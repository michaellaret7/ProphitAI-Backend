from backend.src.db.core.market_data_models import *
from backend.src.db.core.db_config import MarketSession
from backend.src.repositories.price_data import fetch_bulk_price_data_for_tickers

def get_sub_industry_tickers(sub_industry: str):
    session = MarketSession()
    tickers = session.query(Ticker).filter(Ticker.sub_industry == sub_industry).all()
    session.close()

    tickers_list = []
    for ticker in tickers:
        tickers_list.append(ticker.ticker)
    
    price_dict = fetch_bulk_price_data_for_tickers(tickers_list, "2023-01-01", "2025-01-01")

    return price_dict

if __name__ == "__main__":
    print(get_sub_industry_tickers("systems_software"))

