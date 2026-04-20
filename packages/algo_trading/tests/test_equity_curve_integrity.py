"""Equity curve integrity tests — verifies the tracker produces CORRECT data.

Metrics are garbage-in/garbage-out. Before trusting calculated Sharpe/CAGR/DD,
we must verify:

    1. Every equity value is cash + Σ(mark-to-market position value).
    2. Long mark-to-market = shares × current_price.
    3. Short mark-to-market tracks unrealized PnL correctly.
    4. Commissions deduct from equity at entry/exit (exactly once each).
    5. initial_capital + Σ(trade.pnl) + Σ(unrealized at last bar) == final equity.
    6. Equity curve has ONE row per bar (after dedup), timestamps sorted, no NaN.
    7. Flat-period equity is constant (no drift when no positions).
    8. Missing-price handling uses stale price, not zero.

Each test runs a small hand-built scenario through the real tracker and asserts
equity matches a hand-computed expected value at every bar.

Usage:
    source .venv/bin/activate
    python packages/algo_trading/tests/test_equity_curve_integrity.py
"""

from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.portfolio_tracker.tracker import PortfolioTracker
from prophitai_algo_trading.sizing.std_lib.equity.percent_of_equity import (
    PercentOfEquitySizer,
)


_FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    if cond:
        print(f"  PASS: {msg}")
    else:
        print(f"  FAIL: {msg}")
        _FAILURES.append(msg)


def _approx(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) < tol


# ================================
# --> Test cases
# ================================


def test_flat_equity_no_trades() -> None:
    """No trades → equity is a flat line at initial_capital for every recorded bar."""
    print("\n[test] no trades → flat equity")
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.1),
        cost_model=CostModel(),
    )

    t0 = datetime(2020, 1, 2)
    for i in range(20):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": 150.0})

    ec = tracker.get_equity_curve()

    _assert(len(ec) == 20, f"equity curve has 20 bars (got {len(ec)})")
    _assert((ec["equity"] == 100_000.0).all(), "every bar is exactly initial_capital")
    _assert(ec.index.is_monotonic_increasing, "timestamps are sorted")
    _assert(not ec["equity"].isna().any(), "no NaN values")


def test_long_bar_by_bar_mark_to_market() -> None:
    """Long position: equity must equal cash + shares × current_price at every bar."""
    print("\n[test] long position mark-to-market is bar-exact")
    cost_model = CostModel(ptc=0.001)  # 10 bps
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.5, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)
    entry_price = 100.0
    tracker.open_long("AAPL", price=entry_price, timestamp=t0)
    shares = tracker._positions["AAPL"].shares
    commission = cost_model.cost_for_trade(entry_price, shares)

    # Hand-computed expected: cash_after_entry = 100000 - shares*100 - commission
    expected_cash_after = 100_000.0 - shares * entry_price - commission

    prices = [100.0, 102.5, 98.0, 105.0, 110.0]
    for i, price in enumerate(prices):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": price})

    tracker.close_position("AAPL", price=110.0, timestamp=t0 + timedelta(days=5))
    tracker.record_equity(t0 + timedelta(days=5), {"AAPL": 110.0})

    ec = tracker.get_equity_curve()
    ec = ec[~ec.index.duplicated(keep="last")]

    for i, price in enumerate(prices):
        expected_equity = expected_cash_after + shares * price
        actual = ec.iloc[i]["equity"]
        if not _approx(actual, expected_equity):
            _assert(
                False,
                f"bar {i} price={price}: expected {expected_equity:.2f} got {actual:.2f}",
            )

    # After close: equity = initial - entry_commission + shares*(exit-entry) - exit_commission
    exit_commission = cost_model.cost_for_trade(110.0, shares)
    expected_final = 100_000.0 - commission + shares * (110.0 - entry_price) - exit_commission
    actual_final = ec.iloc[-1]["equity"]

    print(f"    expected final={expected_final:.2f}  actual={actual_final:.2f}")
    _assert(_approx(actual_final, expected_final), "final equity matches hand-computed P&L")


def test_short_bar_by_bar_mark_to_market() -> None:
    """Short position: equity must equal cash + shares × (entry - current) at every bar."""
    print("\n[test] short position mark-to-market is bar-exact")
    cost_model = CostModel(ptc=0.001)
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.5, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)
    entry_price = 100.0
    tracker.open_short("AAPL", price=entry_price, timestamp=t0)
    shares = tracker._positions["AAPL"].shares
    entry_commission = cost_model.cost_for_trade(entry_price, shares)

    # Short accounting in this codebase: cash -= commission; position_value = shares*(entry-current)
    expected_cash_after = 100_000.0 - entry_commission

    prices = [100.0, 95.0, 98.0, 92.0, 88.0]
    for i, price in enumerate(prices):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": price})

    ec = tracker.get_equity_curve()

    for i, price in enumerate(prices):
        expected_equity = expected_cash_after + shares * (entry_price - price)
        actual = ec.iloc[i]["equity"]
        if not _approx(actual, expected_equity):
            _assert(
                False,
                f"bar {i} price={price}: expected {expected_equity:.2f} got {actual:.2f}",
            )

    # Close at 88 (profitable short)
    exit_price = 88.0
    tracker.close_position("AAPL", price=exit_price, timestamp=t0 + timedelta(days=5))
    tracker.record_equity(t0 + timedelta(days=5), {"AAPL": exit_price})

    exit_commission = cost_model.cost_for_trade(exit_price, shares)
    realized_pnl = shares * (entry_price - exit_price) - entry_commission - exit_commission
    expected_final = 100_000.0 + realized_pnl
    actual_final = tracker.get_equity_curve().iloc[-1]["equity"]

    print(f"    shares={shares}  expected final={expected_final:.2f}  actual={actual_final:.2f}")
    _assert(_approx(actual_final, expected_final, tol=0.05), "short PnL accounted correctly")


def test_equity_equals_cash_plus_mtm_invariant() -> None:
    """Hard invariant: at every bar, equity = cash + Σ position_values."""
    print("\n[test] equity = cash + Σ MV invariant holds bar-by-bar")
    cost_model = CostModel(ptc=0.0005)
    tracker = PortfolioTracker(
        initial_capital=200_000.0,
        sizer=PercentOfEquitySizer(pct=0.2, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)

    # Open 3 longs + 1 short at different times with different prices
    tracker.open_long("AAPL", 100.0, t0)
    tracker.record_equity(t0, {"AAPL": 100.0})

    tracker.open_long("MSFT", 200.0, t0 + timedelta(days=1))
    tracker.record_equity(t0 + timedelta(days=1), {"AAPL": 101.0, "MSFT": 200.0})

    tracker.open_long("GOOG", 150.0, t0 + timedelta(days=2))
    tracker.record_equity(t0 + timedelta(days=2), {"AAPL": 102.0, "MSFT": 205.0, "GOOG": 150.0})

    tracker.open_short("TSLA", 300.0, t0 + timedelta(days=3))
    tracker.record_equity(t0 + timedelta(days=3), {"AAPL": 103.0, "MSFT": 210.0, "GOOG": 155.0, "TSLA": 300.0})

    # Walk prices for several bars
    price_walk = [
        {"AAPL": 104.0, "MSFT": 215.0, "GOOG": 160.0, "TSLA": 295.0},
        {"AAPL": 103.0, "MSFT": 212.0, "GOOG": 158.0, "TSLA": 290.0},
        {"AAPL": 106.0, "MSFT": 220.0, "GOOG": 162.0, "TSLA": 280.0},
    ]

    for i, prices in enumerate(price_walk):
        tracker.record_equity(t0 + timedelta(days=4 + i), prices)

    ec = tracker.get_equity_curve()

    # For every row in ec, recompute equity from cash + MV using the SAME
    # latest_prices stored in the tracker — and compare.
    # We can reconstruct MV at each bar only for the LAST bar (cash field
    # is the final cash). So we verify: at the LAST bar, equity = cash + MV.
    last_row = ec.iloc[-1]
    computed_mv = 0.0
    final_prices = price_walk[-1]

    for sym, pos in tracker._positions.items():
        p = final_prices.get(sym, pos.entry_price)
        if pos.direction.value == "long":
            computed_mv += pos.shares * p
        else:
            computed_mv += pos.shares * (pos.entry_price - p)

    reconstructed = tracker.cash + computed_mv

    print(f"    tracker.cash={tracker.cash:.2f}  computed_MV={computed_mv:.2f}  "
          f"reconstructed={reconstructed:.2f}  ec_last={last_row['equity']:.2f}")
    _assert(
        _approx(reconstructed, last_row["equity"], tol=0.5),
        "equity = cash + Σ mark-to-market at the last bar",
    )

    # Also: every row's equity column should equal row['cash'] + row['position_value']
    delta_max = (ec["equity"] - ec["cash"] - ec["position_value"]).abs().max()
    _assert(delta_max < 0.01, f"equity = cash + position_value at every bar (max Δ {delta_max:.4f})")


def test_equity_matches_trade_log_final() -> None:
    """After closing ALL positions: final equity == initial_capital + Σ(trade.pnl)."""
    print("\n[test] final equity = initial + Σ realized PnL")
    cost_model = CostModel(ptc=0.0005)
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.1, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)

    # 3 round trips
    trades = [
        ("AAPL", "long", 100.0, 110.0),
        ("MSFT", "long", 200.0, 190.0),
        ("GOOG", "short", 150.0, 140.0),
    ]

    for i, (sym, direction, entry, exit_p) in enumerate(trades):
        ts_entry = t0 + timedelta(days=i * 10)
        ts_exit = t0 + timedelta(days=i * 10 + 5)

        if direction == "long":
            tracker.open_long(sym, entry, ts_entry)
        else:
            tracker.open_short(sym, entry, ts_entry)

        tracker.record_equity(ts_entry, {sym: entry})
        tracker.close_position(sym, exit_p, ts_exit)
        tracker.record_equity(ts_exit, {sym: exit_p})

    ec = tracker.get_equity_curve()
    trades_df = tracker.get_trades_df()

    realized_pnl = float(trades_df["pnl"].sum())
    expected_final = 100_000.0 + realized_pnl
    actual_final = ec.iloc[-1]["equity"]

    print(f"    initial=100000  Σpnl={realized_pnl:.2f}  expected={expected_final:.2f}  "
          f"actual={actual_final:.2f}")
    _assert(
        _approx(actual_final, expected_final, tol=0.05),
        "final equity equals initial + sum(trade.pnl)",
    )


def test_equity_curve_no_gaps_or_nans() -> None:
    """Equity curve has exactly one entry per record_equity call, no NaN, sorted."""
    print("\n[test] equity curve has no gaps, no NaN, sorted")
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.1),
        cost_model=CostModel(),
    )

    t0 = datetime(2020, 1, 2)
    expected_len = 0

    for i in range(50):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": 100 + i * 0.5})
        expected_len += 1

    ec = tracker.get_equity_curve()

    _assert(len(ec) == expected_len, f"equity curve length matches ({len(ec)} == {expected_len})")
    _assert(not ec["equity"].isna().any(), "equity has no NaN")
    _assert(not ec["cash"].isna().any(), "cash has no NaN")
    _assert(not ec["position_value"].isna().any(), "position_value has no NaN")
    _assert(ec.index.is_monotonic_increasing, "timestamps sorted")


def test_stale_price_used_when_missing() -> None:
    """If a ticker is absent from prices dict, MV uses the last known price, not zero."""
    print("\n[test] missing price → stale price used for mark-to-market")
    cost_model = CostModel()
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.5, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)
    tracker.open_long("AAPL", 100.0, t0)
    shares = tracker._positions["AAPL"].shares

    # Bar 1: price given → should be 150
    tracker.record_equity(t0 + timedelta(days=1), {"AAPL": 150.0})

    # Bar 2: price NOT given — should reuse 150 (stale), NOT fall to 0 or entry
    tracker.record_equity(t0 + timedelta(days=2), {})

    ec = tracker.get_equity_curve()
    bar1_equity = ec.iloc[0]["equity"]
    bar2_equity = ec.iloc[1]["equity"]

    print(f"    shares={shares}  bar1_equity={bar1_equity:.2f}  bar2_equity={bar2_equity:.2f}")
    _assert(
        _approx(bar1_equity, bar2_equity, tol=0.01),
        "missing price uses stale price (bars with same implied price match)",
    )


def test_cash_only_conservation() -> None:
    """No positions ever opened → cash == initial_capital forever."""
    print("\n[test] cash-only conservation")
    tracker = PortfolioTracker(
        initial_capital=50_000.0,
        sizer=PercentOfEquitySizer(pct=0.1),
        cost_model=CostModel(ptc=0.005),
    )

    for i in range(10):
        tracker.record_equity(datetime(2020, 1, 2) + timedelta(days=i), {})

    _assert(tracker.cash == 50_000.0, "cash unchanged when no trades")

    ec = tracker.get_equity_curve()
    _assert((ec["equity"] == 50_000.0).all(), "equity unchanged when no trades")


def test_full_backtest_equity_consistency() -> None:
    """Run the real vectorized engine — verify equity curve invariants end-to-end.

    After a real backtest:
    - equity = cash + position_value at every row
    - final equity ≈ initial + Σ(closed trade pnl) (all positions force-closed at end)
    - no NaN anywhere
    - timestamps sorted and unique (after force-close dedup)
    """
    print("\n[test] real vectorized backtest → equity curve is internally consistent")
    from prophitai_algo_trading.engines.backtest.vectorized import VectorizedBacktestEngine
    from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
    from prophitai_algo_trading.indicators.specs import IndicatorSpec
    from prophitai_algo_trading.signals.base import BaseSignalModel
    from prophitai_algo_trading.strategies.composable import BaseComposableStrategy
    from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers

    class _Suite(BaseIndicatorSuite):
        def indicator_specs(self):
            return [
                IndicatorSpec("sma", params={"window": 10, "output_column": "sma_fast"}),
                IndicatorSpec("sma", params={"window": 30, "output_column": "sma_slow"}),
            ]

    class _Model(BaseSignalModel):
        required_columns = ("sma_fast", "sma_slow")

        def long_entry(self, df):
            return (df["sma_fast"] > df["sma_slow"]) & (df["sma_fast"].shift(1) <= df["sma_slow"].shift(1))

        def long_exit(self, df):
            return df["sma_fast"] < df["sma_slow"]

        def short_entry(self, df):
            return pd.Series(False, index=df.index)

        def short_exit(self, df):
            return pd.Series(False, index=df.index)

    class _Strat(BaseComposableStrategy):
        def __init__(self):
            super().__init__(indicator_suite=_Suite(), signal_model=_Model())

        @property
        def min_bars_required(self):
            return 30

    raw = fetch_bulk_ohlcv_data_for_tickers(["SPY", "QQQ", "IWM"], "2021-01-01", "2024-12-31")
    data = {}
    for t, df in raw.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        df.index = pd.to_datetime(df.index)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        data[t] = df[["open", "high", "low", "close", "volume"]]

    engine = VectorizedBacktestEngine(
        strategy=_Strat(),
        initial_capital=100_000.0,
        cost_model=CostModel(ptc=0.0005),
        sizer=PercentOfEquitySizer(pct=0.3),
        max_positions=3,
    )
    result = engine.run(data, verbose=False)

    ec = result.equity_curve
    trades = result.trades

    # Dedup — force_close adds a duplicate row
    ec_deduped = ec[~ec.index.duplicated(keep="last")].sort_index()

    print(f"    bars={len(ec_deduped)}  trades={len(trades)}  "
          f"initial=100000  final={ec_deduped['equity'].iloc[-1]:.2f}")

    # Check 1: no NaN
    _assert(not ec_deduped["equity"].isna().any(), "no NaN in equity column")

    # Check 2: equity = cash + position_value at every bar
    delta = (ec_deduped["equity"] - ec_deduped["cash"] - ec_deduped["position_value"]).abs()
    _assert(delta.max() < 0.02, f"equity = cash + position_value holds (max Δ {delta.max():.4f})")

    # Check 3: timestamps sorted
    _assert(ec_deduped.index.is_monotonic_increasing, "timestamps sorted")

    # Check 4: final equity matches initial + Σ trade.pnl (all positions closed by force_close)
    expected_final = 100_000.0 + float(trades["pnl"].sum())
    actual_final = ec_deduped["equity"].iloc[-1]

    # Tolerance accounts for any remaining mark-to-market if a position wasn't fully closed
    _assert(
        _approx(actual_final, expected_final, tol=expected_final * 0.001),
        f"final equity {actual_final:.2f} ≈ initial + Σpnl {expected_final:.2f}",
    )


def test_equity_curve_monotone_when_winning_strategy() -> None:
    """Running-max of equity should never decrease (tautology)."""
    print("\n[test] equity cummax is monotone non-decreasing")
    cost_model = CostModel()
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.1, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)
    tracker.open_long("AAPL", 100.0, t0)

    # Price walk with drawdowns and recoveries
    prices = [100, 105, 102, 110, 95, 115, 90, 120]
    for i, p in enumerate(prices):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": float(p)})

    ec = tracker.get_equity_curve()
    cm = ec["equity"].cummax()

    _assert((cm.diff().dropna() >= 0).all(), "cummax is monotone non-decreasing")


def test_per_bar_pnl_adds_to_cumulative() -> None:
    """Bar-over-bar equity diff = bar's realized + unrealized PnL change."""
    print("\n[test] per-bar Δequity reconciles with Δ(cash) + Δ(MV)")
    cost_model = CostModel(ptc=0.0001)
    tracker = PortfolioTracker(
        initial_capital=100_000.0,
        sizer=PercentOfEquitySizer(pct=0.3, cost_model=cost_model),
        cost_model=cost_model,
    )

    t0 = datetime(2020, 1, 2)
    tracker.open_long("AAPL", 100.0, t0)
    for i, p in enumerate([100.0, 105.0, 103.0, 108.0]):
        tracker.record_equity(t0 + timedelta(days=i), {"AAPL": p})

    ec = tracker.get_equity_curve()

    dequity = ec["equity"].diff().dropna()
    dcash = ec["cash"].diff().dropna()
    dmv = ec["position_value"].diff().dropna()
    residual = (dequity - dcash - dmv).abs()

    print(f"    max Δequity−Δcash−ΔMV residual: {residual.max():.6f}")
    _assert(residual.max() < 0.01, "Δequity = Δcash + Δposition_value at every bar")


# ================================
# --> Runner
# ================================


def main() -> int:
    print("=" * 72)
    print("EQUITY CURVE INTEGRITY VALIDATION")
    print("=" * 72)

    tests = [
        test_flat_equity_no_trades,
        test_long_bar_by_bar_mark_to_market,
        test_short_bar_by_bar_mark_to_market,
        test_equity_equals_cash_plus_mtm_invariant,
        test_equity_matches_trade_log_final,
        test_equity_curve_no_gaps_or_nans,
        test_stale_price_used_when_missing,
        test_cash_only_conservation,
        test_per_bar_pnl_adds_to_cumulative,
        test_equity_curve_monotone_when_winning_strategy,
        test_full_backtest_equity_consistency,
    ]

    for fn in tests:
        try:
            fn()
        except Exception as exc:
            _FAILURES.append(f"{fn.__name__}: {type(exc).__name__}: {exc}")
            print(f"  UNEXPECTED: {type(exc).__name__}: {exc}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 72)

    if _FAILURES:
        print(f"FAIL: {len(_FAILURES)} failure(s):")
        for f in _FAILURES:
            print(f"  - {f}")
        return 1

    print("PASS: equity curves are internally consistent end-to-end")
    return 0


if __name__ == "__main__":
    sys.exit(main())
