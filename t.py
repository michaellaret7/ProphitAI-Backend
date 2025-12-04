from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
from app.core.calculations.performance.calculator import PerformanceCalculator

ticker = 'QQQ'

data = fetch_bulk_ohlcv_data_for_tickers([ticker, 'SPY'], '2024-11-29', '2025-12-04', frequency='daily', returns=True)
ticker_returns = data[ticker]['returns'].dropna()
benchmark_returns = data['SPY']['returns'].dropna()

print(round(PerformanceCalculator.alpha(ticker_returns, benchmark_returns), 4)*100)
