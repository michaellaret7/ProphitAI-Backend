"""Run vectorized backtest with MACDMomentum on a small universe."""

from datetime import datetime

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.strategies.macd_momentum import MACDMomentum
from prophitai_algo_trading.engines import VectorizedBacktestEngine

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

engine = VectorizedBacktestEngine(strategy=MACDMomentum(), max_positions=len(data))
result = engine.run(data, verbose=True)

print("\n=== METRICS ===")
for k, v in result.metrics.items():
    print(f"  {k}: {v}")


"""
Fetching data...
  AAPL: 13282 bars
  MSFT: 13282 bars
  GOOGL: 13282 bars
  NVDA: 13282 bars
  JPM: 13282 bars
  XOM: 13282 bars
  PG: 13282 bars
  UNH: 13282 bars
  HD: 13282 bars
  CAT: 13282 bars

Loaded 10/10 tickers
[Phase 1] Computing signals for 10 tickers (vectorized)...
[Phase 2] Simulating portfolio across 13282 bars...

Done: 4409 trades across 10 tickers, final equity=$88,425.70

=== METRICS ===
  total_return_pct: -11.57
  annualized_return_pct: -5.97
  max_drawdown_pct: -16.37
  sharpe_ratio: -1.06
  total_trades: 4409
  win_rate_pct: 35.45
  profit_factor: 0.94
  avg_trade_return_pct: -0.03
  avg_win_pct: 1.27
  avg_loss_pct: -0.74
  largest_win: 1724.25
  largest_loss: -1700.78
  long_trades: 1927
  short_trades: 2482
(venv) michaellaret@Michaels-MacBook-Air algorithmicTrading % 
"""