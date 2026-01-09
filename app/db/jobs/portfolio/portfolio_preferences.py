from app.db.core.db_config import UserSession, MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.core.models.user_data_models import PortfolioItem, PortfolioPreference
from app.db.jobs.portfolio.utils import classify_and_add_tickers

class MonitorPortfolio:
    def __init__(self, portfolio_id: str):
        self.portfolio_id = portfolio_id
        self.user_session = UserSession()
        self.market_session = MarketSession()
        self.preferences, self.positions = self._get_data()

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.user_session.close()
        self.market_session.close()
    
    def _get_data(self):
        # Return only specific columns
        preferences = self.user_session.query(
            PortfolioPreference.equities_allocation,
            PortfolioPreference.fixed_income_allocation,
            PortfolioPreference.commodities_allocation,
            PortfolioPreference.currencies_allocation,
            PortfolioPreference.cryptocurrencies_allocation,
            PortfolioPreference.alternatives_hedge_funds_allocation,
            PortfolioPreference.alternatives_pe_vc_allocation,
            PortfolioPreference.cash_allocation,

        ).filter(
            PortfolioPreference.portfolio_id == self.portfolio_id
        ).first()

        if preferences:
            keys = ['equities', 'fixed_income', 'commodities', 'currencies', 
                    'cryptocurrencies', 'alternatives_hedge_funds', 'alternatives_pe_vc', 'cash']
            preferences = {k: float(v) for k, v in zip(keys, preferences) if v}
        else:
            raise ValueError(f"No preferences found for portfolio {self.portfolio_id}")
        
        positions = self.user_session.query(
            PortfolioItem.ticker,
            PortfolioItem.allocation
        ).filter(
            PortfolioItem.portfolio_id == self.portfolio_id
        ).all()
        
        if positions:
            positions = {p.ticker: float(p.allocation) for p in positions}
        else:
            raise ValueError(f"No positions found for portfolio {self.portfolio_id}")
        
        return preferences, positions
    
    
if __name__ == "__main__":
    with MonitorPortfolio("766f10b8-c424-49fa-92be-cff3e0ac4b27") as monitor:
        x,y=monitor._get_data()
        print(x)
        print(y)