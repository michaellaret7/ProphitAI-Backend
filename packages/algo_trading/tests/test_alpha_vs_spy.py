"""Test that alpha_vs_spy appears in backtest results.

Runs a real backtest with synthetic data and a synthetic benchmark,
then verifies the alpha metric is computed and present.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from prophitai_algo_trading.engines import VectorizedBacktestEngine
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.signals.base import BaseSignalModel
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_algo_trading.testing.fixtures import make_ohlcv, uptrend


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
    """Run a vectorized backtest with benchmark data and verify alpha_vs_spy."""

    # Strategy uptrends, benchmark is slower — should produce positive alpha
    strategy_data = uptrend(bars=300, start=100.0, drift=0.003)
    benchmark_closes = make_ohlcv(
        [100.0 * (1.0 + 0.001) ** i for i in range(300)],
    )["close"]

    data = {"FAKE": strategy_data}

    engine = VectorizedBacktestEngine(
        strategy=SmaCrossoverStrategy(),
        initial_capital=100_000.0,
        max_positions=1,
    )

    # Run WITHOUT benchmark
    result_no_bench = engine.run(data, verbose=True)

    print("\n=== Metrics WITHOUT benchmark ===")
    for k, v in result_no_bench.metrics.items():
        print(f"  {k}: {v}")

    assert "alpha_vs_spy" in result_no_bench.metrics, "alpha_vs_spy key missing from metrics!"
    assert result_no_bench.metrics["alpha_vs_spy"] is None, "alpha should be None without benchmark"

    # Run WITH benchmark
    result_with_bench = engine.run(data, verbose=True, benchmark_prices=benchmark_closes)

    print("\n=== Metrics WITH benchmark ===")
    for k, v in result_with_bench.metrics.items():
        print(f"  {k}: {v}")

    assert "alpha_vs_spy" in result_with_bench.metrics, "alpha_vs_spy key missing from metrics!"
    assert result_with_bench.metrics["alpha_vs_spy"] is not None, "alpha should not be None with benchmark"
    assert isinstance(result_with_bench.metrics["alpha_vs_spy"], float), "alpha should be a float"

    print(f"\n--> alpha_vs_spy = {result_with_bench.metrics['alpha_vs_spy']}%")
    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()
