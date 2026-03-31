"""Run the scaffold strategy in the vectorized backtest engine."""

from __future__ import annotations

from prophitai_algo_trading.strategies.template.config import TemplateBacktestConfig
from prophitai_algo_trading.strategies.template.wiring import (
    build_vectorized_backtest_engine,
    load_backtest_data,
)


def main() -> None:
    """Load data, run the vectorized backtest, and print metrics."""
    config = TemplateBacktestConfig()
    print("Fetching data for vectorized backtest...")
    data = load_backtest_data(config)

    if not data:
        raise RuntimeError("No price data loaded for the scaffold vectorized backtest.")

    for ticker, df in data.items():
        print(f"  {ticker}: {len(df)} bars")

    print(f"\nLoaded {len(data)}/{len(config.tickers)} tickers")

    engine = build_vectorized_backtest_engine(backtest_config=config)
    result = engine.run(
        data,
        warmup_bars=config.warmup_bars,
        verbose=config.verbose,
    )

    print("\n=== METRICS ===")
    for key, value in result.metrics.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
