"""Backtest for TTM Squeeze Breakout strategy using VectorizedBacktestEngine."""

from datetime import datetime

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.strategies.squeeze_breakout import SqueezeBreakout
from prophitai_algo_trading.engines import VectorizedBacktestEngine
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.position_sizer import PercentOfEquitySizer

# Reason: 25 liquid large-caps across sectors for diversified squeeze events
TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "META", "CRM",  # tech
    "JPM", "GS", "BAC", "V",                                    # financials
    "UNH", "LLY", "ABBV",                                       # healthcare
    "XOM", "CVX",                                                # energy
    "PG", "KO", "COST", "WMT",                                  # consumer staples
    "HD", "NKE", "TSLA",                                         # consumer discretionary
    "CAT", "BA",                                                  # industrials
]

START = datetime(2024, 8, 1)
END = datetime(2026, 3, 1)
INTERVAL = "15min"

print("Fetching data...")
data = {}
for ticker in TICKERS:
    df = get_price_data_df(ticker, START, END, INTERVAL)
    if not df.empty:
        data[ticker] = df
        print(f"  {ticker}: {len(df)} bars")
    else:
        print(f"  {ticker}: NO DATA — skipped")

print(f"\nLoaded {len(data)} tickers")

# Reason: intraday 15min params — 26 bars/session
# BB/KC 40 ≈ 1.5 sessions captures multi-hour compression
# Donchian 52 ≈ 2 sessions for breakout level
# SMA 200 ≈ ~8 trading days for trend direction
strategy = SqueezeBreakout(
    bb_period=40,
    bb_std=2.0,
    kc_period=40,
    kc_atr_mult=1.5,
    donchian_period=52,
    atr_period=26,
    momentum_period=26,
    volume_ma_period=26,
    rsi_period=14,
    chandelier_period=52,
    chandelier_mult=3.0,
    trend_sma_period=200,
)
cost_model = CostModel(ptc=0.0005)
sizer = PercentOfEquitySizer(pct=0.25, cost_model=cost_model)

engine = VectorizedBacktestEngine(
    strategy=strategy,
    initial_capital=100_000,
    cost_model=cost_model,
    sizer=sizer,
    warmup_bars=250,
    max_positions=10,
)

print("\nRunning vectorized backtest...")
result = engine.run(data, verbose=True)

print("\n=== METRICS ===")
for k, v in result.metrics.items():
    print(f"  {k}: {v}")

print(f"\n=== TRADES ({len(result.trades)} total) ===")
if not result.trades.empty:
    winners = result.trades[result.trades['pnl'] > 0]
    losers = result.trades[result.trades['pnl'] <= 0]
    print(f"  Winners: {len(winners)}")
    print(f"  Losers: {len(losers)}")
    win_rate = len(winners) / len(result.trades) * 100
    avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Win: ${avg_win:,.2f}")
    print(f"  Avg Loss: ${avg_loss:,.2f}")
    if avg_loss != 0:
        print(f"  Win/Loss Ratio: {abs(avg_win / avg_loss):.2f}x")

print(f"\n=== EQUITY CURVE ===")
eq = result.equity_curve
if not eq.empty:
    print(f"  Start: ${eq['equity'].iloc[0]:,.2f}")
    print(f"  End: ${eq['equity'].iloc[-1]:,.2f}")
    total_return = (eq['equity'].iloc[-1] / eq['equity'].iloc[0] - 1) * 100
    print(f"  Total Return: {total_return:.2f}%")
