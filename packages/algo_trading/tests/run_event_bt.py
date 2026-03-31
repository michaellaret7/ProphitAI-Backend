"""Run event-driven backtest with the in-repo reference strategy."""

from datetime import datetime

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.engines import EventDrivenBacktestEngine
from prophitai_algo_trading.strategies.rsi_mean_reversion import RSIMeanReversion

TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM", "XOM", "PG", "UNH", "HD", "CAT"]
START = datetime(2024, 1, 1)
END = datetime(2026, 1, 1)
INTERVAL = "15min"

print("Fetching data...")
data = {}

for ticker in TICKERS:
    df = get_price_data_df(ticker, START, END, INTERVAL)
    if not df.empty:
        data[ticker] = df
        print(f"  {ticker}: {len(df)} bars")

print(f"\nLoaded {len(data)}/{len(TICKERS)} tickers")

engine = EventDrivenBacktestEngine(strategy=RSIMeanReversion(), max_positions=len(data))
result = engine.run(data, verbose=True, plot=True)

print("\n=== METRICS ===")
for k, v in result.metrics.items():
    print(f"  {k}: {v}")
