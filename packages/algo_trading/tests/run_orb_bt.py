"""Run vectorized backtest with ORB Breakout on a liquid equity universe.

Strategy: Opening Range Breakout (15-minute bars)
- Entry: first 15-min bar defines the day's opening range (OR)
- Long when close breaks above OR high + VWAP above + volume > 1.2x avg
- Short when close breaks below OR low + VWAP below + volume > 1.2x avg
- Exit: profit target at 2x OR range, chandelier stop at 4.5x ATR, hard stop at OR low/high
- Morning-only entries (bars 1-10), no time exit (positions persist)
"""

from datetime import datetime
import numpy as np

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.sizing import PercentOfEquitySizer
from prophitai_algo_trading.strategies.orb_breakout import ORBBreakout
from prophitai_algo_trading.engines import VectorizedBacktestEngine

TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM", "XOM", "PG", "UNH", "HD", "CAT"]
START = datetime(2024, 1, 1)
END = datetime(2026, 1, 1)
INTERVAL = "15min"
MAX_POSITIONS = 5


print("Fetching data...")
data = {}
for ticker in TICKERS:
    df = get_price_data_df(ticker, START, END, INTERVAL)
    if not df.empty:
        data[ticker] = df
        print(f"  {ticker}: {len(df)} bars")

print(f"\nLoaded {len(data)}/{len(TICKERS)} tickers")

cost_model = CostModel(ptc=0.00005)
sizer = PercentOfEquitySizer(pct=1 / MAX_POSITIONS, cost_model=cost_model)

strategy = ORBBreakout()
engine = VectorizedBacktestEngine(
    strategy=strategy,
    max_positions=MAX_POSITIONS,
    cost_model=cost_model,
    sizer=sizer,
)
result = engine.run(data, verbose=True)

print("\n=== METRICS ===")
for k, v in result.metrics.items():
    print(f"  {k}: {v}")
