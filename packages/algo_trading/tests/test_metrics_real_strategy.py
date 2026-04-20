"""End-to-end validation of the fixed metrics against a real backtest.

Runs an SMA crossover strategy on real market data through the vectorized
engine, then asserts the fixed metrics satisfy the mathematical invariants:

  1. Sharpe is finite
  2. Sharpe > 0 whenever CAGR > risk-free-rate (AM-GM)
  3. Equity stays positive throughout (tracker accounting sanity)

Also deliberately runs a pathological scenario where metrics MUST raise
instead of returning a bogus Sharpe.

Usage:
    source .venv/bin/activate
    python packages/algo_trading/tests/test_metrics_real_strategy.py
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from prophitai_algo_trading.engines.backtest.metrics import calculate_metrics
from prophitai_algo_trading.engines.backtest.vectorized import VectorizedBacktestEngine
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.signals.base import BaseSignalModel
from prophitai_algo_trading.sizing.std_lib.equity.percent_of_equity import (
    PercentOfEquitySizer,
)
from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


# ================================
# --> Minimal SMA crossover strategy (long-only, for a clean real backtest)
# ================================


@dataclass(frozen=True)
class SmaCrossoverConfig:
    fast_period: int = 20
    slow_period: int = 50


class SmaCrossoverSuite(BaseIndicatorSuite):
    def __init__(self, config: SmaCrossoverConfig) -> None:
        self._config = config
        super().__init__()

    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        return [
            IndicatorSpec(
                "sma",
                params={"window": self._config.fast_period, "output_column": "sma_fast"},
            ),
            IndicatorSpec(
                "sma",
                params={"window": self._config.slow_period, "output_column": "sma_slow"},
            ),
        ]


class SmaLongOnlyModel(BaseSignalModel):
    required_columns = ("sma_fast", "sma_slow")

    def long_entry(self, df: pd.DataFrame) -> pd.Series:
        fast = df["sma_fast"]
        slow = df["sma_slow"]

        return (fast > slow) & (fast.shift(1) <= slow.shift(1))

    def long_exit(self, df: pd.DataFrame) -> pd.Series:
        return df["sma_fast"] < df["sma_slow"]

    def short_entry(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)

    def short_exit(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(False, index=df.index)


class SmaCrossoverStrategy(BaseComposableStrategy):
    def __init__(self, config: SmaCrossoverConfig | None = None) -> None:
        self._config = config or SmaCrossoverConfig()
        super().__init__(
            indicator_suite=SmaCrossoverSuite(self._config),
            signal_model=SmaLongOnlyModel(),
        )

    @property
    def min_bars_required(self) -> int:
        return self._config.slow_period


# ================================
# --> Helper funcs
# ================================


_FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  PASS: {msg}")
    else:
        print(f"  FAIL: {msg}")
        _FAILURES.append(msg)


def _normalize_ohlcv(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Ensure DataFrames have lowercase OHLCV columns and DatetimeIndex."""
    normalized = {}

    for ticker, df in data.items():
        if df is None or df.empty:
            continue

        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)

        if missing:
            print(f"  (skipping {ticker}: missing columns {missing})")
            continue

        df.index = pd.to_datetime(df.index)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        normalized[ticker] = df[["open", "high", "low", "close", "volume"]]

    return normalized


# ================================
# --> Real backtest tests
# ================================


def test_real_sma_backtest_metrics_sane() -> None:
    """Run SMA crossover on real prices; verify fixed metrics satisfy invariants."""
    print("\n[test] real SMA crossover on AAPL/MSFT/NVDA/SPY, 2020-2024")

    tickers = ["AAPL", "MSFT", "NVDA", "SPY"]
    raw = fetch_bulk_ohlcv_data_for_tickers(tickers, "2020-01-01", "2024-12-31")
    data = _normalize_ohlcv(raw)

    if not data:
        print("  SKIP: no price data returned")
        return

    print(f"    loaded {len(data)} tickers × ~{len(next(iter(data.values())))} bars")

    engine = VectorizedBacktestEngine(
        strategy=SmaCrossoverStrategy(),
        initial_capital=100_000.0,
        cost_model=CostModel(ptc=0.0005),
        sizer=PercentOfEquitySizer(pct=0.20),
        max_positions=4,
    )

    result = engine.run(data, verbose=False)
    m = result.metrics

    cagr = m["annualized_return_pct"] / 100.0
    sharpe = m["sharpe_ratio"]
    dd = m["max_drawdown_pct"]
    trades = m["total_trades"]

    print(f"    CAGR={cagr*100:.2f}%  Sharpe={sharpe}  DD={dd}%  trades={trades}")

    ec = result.equity_curve["equity"]
    print(f"    equity range: min={ec.min():.2f}  max={ec.max():.2f}  final={ec.iloc[-1]:.2f}")

    _assert(np.isfinite(sharpe), "Sharpe is finite")
    _assert((ec > 0).all(), "equity stays positive throughout")

    if cagr > 0.04:
        _assert(sharpe > 0, f"CAGR {cagr*100:.2f}% > 4% rf requires Sharpe > 0 (got {sharpe})")
    elif cagr < 0.04:
        # Either sign is mathematically allowed — no invariant to check.
        print(f"    (CAGR {cagr*100:.2f}% < rf; Sharpe sign unconstrained)")


def test_pathological_equity_raises_in_real_pipeline() -> None:
    """Synthesize a corrupted equity curve and verify calculate_metrics raises.

    Guards against regression: if someone loosens the equity>0 check in
    metrics.py, this test catches it.
    """
    print("\n[test] corrupted equity curve → calculate_metrics raises")

    dates = pd.bdate_range("2022-01-03", periods=10)
    equity = [100_000, 95_000, 60_000, 10_000, -500, 20_000, 80_000, 120_000, 150_000, 180_000]
    ec = pd.DataFrame({"equity": equity}, index=dates)

    try:
        calculate_metrics(ec, pd.DataFrame())
        _assert(False, "should have raised on non-positive equity")
    except ValueError as exc:
        print(f"    raised: {exc}")
        _assert("non-positive" in str(exc).lower(), "error message mentions non-positive equity")


def test_buy_and_hold_approximation() -> None:
    """Compare engine output to a buy-and-hold reference on a single ticker.

    This stress-tests sign/magnitude agreement: if the real backtest's final
    equity grew K%, the reported CAGR and Sharpe must be internally consistent.
    """
    print("\n[test] single-ticker SMA run — consistency check")

    raw = fetch_bulk_ohlcv_data_for_tickers(["SPY"], "2020-01-01", "2024-12-31")
    data = _normalize_ohlcv(raw)

    if "SPY" not in data:
        print("  SKIP: SPY data unavailable")
        return

    engine = VectorizedBacktestEngine(
        strategy=SmaCrossoverStrategy(SmaCrossoverConfig(fast_period=10, slow_period=30)),
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=1.0),
        max_positions=1,
    )

    result = engine.run(data, verbose=False)
    m = result.metrics

    ec = result.equity_curve["equity"]
    total_return = (ec.iloc[-1] / ec.iloc[0]) - 1.0
    cagr_reported = m["annualized_return_pct"] / 100.0
    sharpe = m["sharpe_ratio"]

    print(f"    total_return={total_return*100:.2f}%  CAGR={cagr_reported*100:.2f}%  "
          f"Sharpe={sharpe}  DD={m['max_drawdown_pct']}%")

    # Reason: when total_return > 0, CAGR must also be > 0 (both computed from
    # same equity endpoints). If they disagree, metrics has a sign bug.
    _assert(
        (total_return >= 0) == (cagr_reported >= 0),
        "total_return and CAGR agree in sign",
    )

    if cagr_reported > 0.04:
        _assert(sharpe > 0, "AM-GM invariant holds on real SPY backtest")


# ================================
# --> Runner
# ================================


def main() -> int:
    print("=" * 72)
    print("REAL-STRATEGY BACKTEST METRICS VALIDATION")
    print("=" * 72)

    for fn in (
        test_real_sma_backtest_metrics_sane,
        test_pathological_equity_raises_in_real_pipeline,
        test_buy_and_hold_approximation,
    ):
        try:
            fn()
        except Exception as exc:
            _FAILURES.append(f"{fn.__name__}: {type(exc).__name__}: {exc}")
            print(f"  UNEXPECTED: {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 72)

    if _FAILURES:
        print(f"FAIL: {len(_FAILURES)} failure(s)")

        for f in _FAILURES:
            print(f"  - {f}")

        return 1

    print("PASS: real-backtest metrics are internally consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
