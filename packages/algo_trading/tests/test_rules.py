"""Backtest with all trading rules applied."""

from datetime import datetime

from prophitai_algo_trading.data.repository.price_data import get_price_data_df
from prophitai_algo_trading.engines import BacktestEngine
from prophitai_algo_trading.rules import (
    CooldownRule,
    EarningsProximityRule,
    StopLossRule,
    TakeProfitRule,
    TrailingStopRule,
)
from prophitai_algo_trading.strategies.rsi_mean_reversion import RSIMeanReversion

TICKERS = ["AAPL", "NVDA", "MSFT", "GOOGL", "JPM", "XOM", "PG", "UNH", "HD", "CAT"]
START = datetime(2021, 1, 1)
END = datetime(2026, 3, 1)

def main() -> None:
    print("Fetching data...")
    data = {}
    for t in TICKERS:
        df = get_price_data_df(t, START, END, "15min")
        if not df.empty:
            data[t] = df
            print(f"  {t}: {len(df)} bars")

    engine = BacktestEngine(
        strategy=RSIMeanReversion(),
        initial_capital=100_000,
        max_positions=len(data),
        rules=[
            CooldownRule(bars=6),
            TakeProfitRule(pct=0.1),
            TrailingStopRule(pct=0.07),
            EarningsProximityRule(days=5),
        ],
    )

    result = engine.run(data, verbose=True)

    print("\n=== METRICS ===")
    for k, v in result.metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
