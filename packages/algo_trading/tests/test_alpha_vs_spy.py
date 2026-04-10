"""Test that alpha_vs_spy is automatically computed in backtest results.

Runs a real backtest with the vectorized engine using real SPY data
fetched from the database. Verifies the alpha metric appears in results.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from prophitai_algo_trading.engines import VectorizedBacktestEngine
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.signals.base import BaseSignalModel
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


# ================================
# --> Minimal SMA crossover strategy
# ================================


@dataclass(frozen=True)
class SmaCrossoverConfig:
    fast_period: int = 10
    slow_period: int = 30


class SmaCrossoverSuite(BaseIndicatorSuite):
    def __init__(self, config: SmaCrossoverConfig) -> None:
        self._config = config
        super().__init__()

    def indicator_specs(self):
        return [
            IndicatorSpec("sma", params={"window": self._config.fast_period, "output_column": "sma_fast"}),
            IndicatorSpec("sma", params={"window": self._config.slow_period, "output_column": "sma_slow"}),
        ]


class SmaCrossoverSignalModel(BaseSignalModel):
    required_columns = ("sma_fast", "sma_slow")

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        return (df["sma_fast"] > df["sma_slow"]) & (df["sma_fast"].shift(1) <= df["sma_slow"].shift(1))

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["sma_fast"] < df["sma_slow"]

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        return (df["sma_fast"] < df["sma_slow"]) & (df["sma_fast"].shift(1) >= df["sma_slow"].shift(1))

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["sma_fast"] > df["sma_slow"]


class SmaCrossoverStrategy(BaseComposableStrategy):
    def __init__(self, config: SmaCrossoverConfig | None = None) -> None:
        self._config = config or SmaCrossoverConfig()

        super().__init__(
            indicator_suite=SmaCrossoverSuite(self._config),
            signal_model=SmaCrossoverSignalModel(),
        )

    @property
    def min_bars_required(self) -> int:
        return self._config.slow_period


# ================================
# --> Test
# ================================


def main():
    """Run a vectorized backtest with real AAPL data — SPY fetched automatically."""

    start = "2024-01-01"
    end = "2025-01-01"

    ohlcv = fetch_bulk_ohlcv_data_for_tickers(["AAPL"], start, end)
    data = {"AAPL": ohlcv["AAPL"]}

    engine = VectorizedBacktestEngine(
        strategy=SmaCrossoverStrategy(),
        initial_capital=100_000.0,
        max_positions=1,
    )

    result = engine.run(data, verbose=True)

    print("\n=== Backtest Metrics ===")
    for k, v in result.metrics.items():
        print(f"  {k}: {v}")

    assert "alpha_vs_spy" in result.metrics, "alpha_vs_spy key missing from metrics!"
    assert result.metrics["alpha_vs_spy"] is not None, "alpha_vs_spy should not be None when DB is available"
    assert isinstance(result.metrics["alpha_vs_spy"], float), "alpha_vs_spy should be a float"

    print(f"\n--> alpha_vs_spy = {result.metrics['alpha_vs_spy']}%")
    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
