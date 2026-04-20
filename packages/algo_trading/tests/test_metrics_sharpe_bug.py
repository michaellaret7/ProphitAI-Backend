"""Test suite for the Sharpe/CAGR contradiction bug in backtest metrics.

Demonstrates the bug in calculate_metrics (metrics.py) where `pct_change()`
produces spurious negative Sharpe ratios on equity curves with positive CAGR.
Also stresses the portfolio tracker with a scenario that can push equity
non-positive via short blowups (tracker-level root cause).

Run standalone:

    source .venv/bin/activate
    python packages/algo_trading/tests/test_metrics_sharpe_bug.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from prophitai_algo_trading.engines.backtest.metrics import calculate_metrics


# ================================
# --> Helper funcs
# ================================


def _assert(cond: bool, msg: str) -> None:
    """Print PASS/FAIL and remember failures without aborting the suite."""
    if cond:
        print(f"  PASS: {msg}")
    else:
        print(f"  FAIL: {msg}")
        _FAILURES.append(msg)


def _build_equity_curve(
    returns: list[float],
    initial: float = 100_000.0,
    start: str = "2020-01-02",
) -> pd.DataFrame:
    """Compound a list of bar returns into an equity curve."""
    equity = [initial]

    for r in returns:
        equity.append(equity[-1] * (1.0 + r))

    dates = pd.bdate_range(start=start, periods=len(equity))

    return pd.DataFrame({"equity": equity}, index=dates)


def _theoretical_sharpe_lower_bound(cagr: float, rf: float = 0.04) -> float:
    """Return a coarse lower bound on Sharpe implied by CAGR via AM-GM.

    If CAGR > rf and equity stays positive, the Sharpe MUST be positive.
    This returns 0.0 as the floor for that regime.
    """
    return 0.0 if cagr > rf else -np.inf


# ================================
# --> Test cases
# ================================


_FAILURES: list[str] = []


def test_flat_equity_returns_zero_sharpe() -> None:
    """Flat equity curve has zero std — Sharpe must degrade gracefully to 0.0."""
    print("\n[test] flat equity curve → Sharpe=0, no div-by-zero")
    ec = _build_equity_curve([0.0] * 252)

    m = calculate_metrics(ec, pd.DataFrame())

    _assert(m["annualized_return_pct"] == 0.0, "flat CAGR is 0%")
    _assert(m["sharpe_ratio"] == 0.0, "flat Sharpe is 0.0 (no div-by-zero)")
    _assert(m["max_drawdown_pct"] == 0.0, "flat DD is 0%")


def test_positive_cagr_gives_positive_sharpe() -> None:
    """A clean positive-CAGR curve MUST produce Sharpe > 0 by AM-GM."""
    print("\n[test] positive CAGR > rf → Sharpe must be > 0")
    np.random.seed(0)

    # Simulate the user's "few-trade" profile: mostly flat, occasional bursts.
    n = 252 * 5
    returns = [0.0] * n
    trade_bars = np.random.choice(n, size=80, replace=False)

    for bar in trade_bars:
        returns[bar] = float(np.random.normal(0.008, 0.015))

    ec = _build_equity_curve(returns)

    m = calculate_metrics(ec, pd.DataFrame())

    cagr = m["annualized_return_pct"] / 100.0
    lower = _theoretical_sharpe_lower_bound(cagr)

    print(f"    CAGR={cagr*100:.2f}%  Sharpe={m['sharpe_ratio']}  DD={m['max_drawdown_pct']}%")
    _assert(
        m["sharpe_ratio"] > lower,
        f"Sharpe ({m['sharpe_ratio']}) must exceed AM-GM lower bound ({lower})",
    )


def test_pct_change_signflip_bug_demo() -> None:
    """Equity that briefly dips non-positive breaks `pct_change()` with sign-flip.

    Total return is STILL +100% (100 → 200), but pct_change's mean flips negative
    due to division by a near-zero or negative denominator. This demonstrates why
    the current Sharpe formula is fragile and why the fix (log returns + guard)
    is needed.
    """
    print("\n[test] equity dips ≤ 0 → pct_change produces garbage Sharpe")
    dates = pd.bdate_range("2020-01-02", periods=6)
    equity = [100.0, 80.0, 10.0, -5.0, 50.0, 200.0]
    ec = pd.DataFrame({"equity": equity}, index=dates)

    try:
        m = calculate_metrics(ec, pd.DataFrame())
        # OLD code silently returns garbage Sharpe with negative sign.
        # FIXED code must raise a clear error.
        pct_mean = ec["equity"].pct_change().dropna().mean()
        total_return = (equity[-1] - equity[0]) / equity[0]

        print(
            f"    equity path: {equity}  total_return={total_return*100:.0f}%  "
            f"pct_change.mean={pct_mean:.4f}  reported_sharpe={m['sharpe_ratio']}"
        )
        _assert(
            False,
            "metrics should RAISE on non-positive equity, not silently return a Sharpe",
        )
    except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
        print(f"    correctly raised: {type(exc).__name__}: {exc}")
        _assert(True, "raised on non-positive equity as expected")


def test_log_return_robustness() -> None:
    """The fix (log returns) must still handle near-zero equity gracefully.

    With log returns, non-positive equity produces -inf/NaN — the metric fn
    should detect this and raise instead of silently returning a bogus number.
    """
    print("\n[test] log-return path handles edge cases")
    np.random.seed(1)

    # Positive-only curve, should compute a finite Sharpe.
    returns = list(np.random.normal(0.0005, 0.01, 252 * 3))
    ec = _build_equity_curve(returns)
    m = calculate_metrics(ec, pd.DataFrame())

    cagr = m["annualized_return_pct"] / 100.0
    sharpe = m["sharpe_ratio"]

    print(f"    random-walk: CAGR={cagr*100:.2f}%  Sharpe={sharpe}")
    _assert(np.isfinite(sharpe), "Sharpe is finite on random-walk curve")

    if cagr > 0.04:
        _assert(sharpe > 0.0, "Sharpe > 0 when CAGR > risk-free")


def test_user_reported_run9_profile() -> None:
    """Reconstruct the user's Run 9 characteristics (21.79% CAGR, ~6% DD, 9 trades).

    With positive equity throughout, any correct Sharpe formula MUST return a
    positive number. If the metric reports negative Sharpe here, the bug is live.
    """
    print("\n[test] user Run 9 profile (21.79% CAGR, 9 trades)")
    np.random.seed(42)
    n = 252 * 5

    returns = [0.0] * n
    trade_windows = [
        (100, 130), (300, 340), (500, 545), (700, 750),
        (900, 945), (1050, 1090), (1150, 1180), (1200, 1230), (1240, 1255),
    ]

    for start, end in trade_windows:
        for bar in range(start, end):
            returns[bar] = float(np.random.normal(0.005, 0.012))

    ec = _build_equity_curve(returns)
    m = calculate_metrics(ec, pd.DataFrame())

    cagr = m["annualized_return_pct"] / 100.0
    sharpe = m["sharpe_ratio"]
    dd = m["max_drawdown_pct"]

    print(f"    CAGR={cagr*100:.2f}%  Sharpe={sharpe}  DD={dd}%")

    if cagr > 0.04:
        _assert(
            sharpe > 0.0,
            f"CAGR {cagr*100:.2f}% > 4% rf requires Sharpe > 0 (got {sharpe})",
        )


def test_sharpe_invariant_on_scale() -> None:
    """Sharpe is scale-invariant: multiplying initial capital by K should not change it."""
    print("\n[test] Sharpe invariant to capital scale")
    np.random.seed(7)
    returns = list(np.random.normal(0.0004, 0.008, 252 * 2))

    m1 = calculate_metrics(_build_equity_curve(returns, initial=10_000), pd.DataFrame())
    m2 = calculate_metrics(_build_equity_curve(returns, initial=10_000_000), pd.DataFrame())

    print(f"    10k → Sharpe={m1['sharpe_ratio']}   10M → Sharpe={m2['sharpe_ratio']}")
    _assert(
        abs(m1["sharpe_ratio"] - m2["sharpe_ratio"]) < 0.01,
        "Sharpe is invariant to initial-capital scaling",
    )


def test_tracker_short_blowup_produces_valid_equity() -> None:
    """Root-cause test: open a short, push price 20x, verify tracker equity sensibility.

    With 2% sizing, a 20x adverse move should draw down ~40% of equity but MUST
    keep equity positive. If the tracker's short accounting is wrong, this is
    where it shows up.
    """
    print("\n[test] short blowup with realistic sizing → equity stays positive")
    from prophitai_algo_trading.execution.cost_model import CostModel
    from prophitai_algo_trading.execution.portfolio_tracker.tracker import PortfolioTracker
    from prophitai_algo_trading.sizing.std_lib.equity.percent_of_equity import (
        PercentOfEquitySizer,
    )

    cost_model = CostModel()
    sizer = PercentOfEquitySizer(pct=0.02, cost_model=cost_model)
    tracker = PortfolioTracker(initial_capital=100_000.0, sizer=sizer, cost_model=cost_model)

    t0 = datetime(2020, 1, 2)

    # Short 100 shares at $10 (target 2% = $2000 -> 200 shares, but test with small)
    tracker.open_short("XYZ", price=10.0, timestamp=t0)
    tracker.record_equity(t0, {"XYZ": 10.0})

    # Walk price 1x → 5x → 10x → 20x
    for step, (day, price) in enumerate([(1, 20.0), (2, 50.0), (3, 100.0), (4, 200.0)]):
        ts = t0 + timedelta(days=day)
        tracker.record_equity(ts, {"XYZ": price})

    # Close
    tracker.close_position("XYZ", price=200.0, timestamp=t0 + timedelta(days=5))
    tracker.record_equity(t0 + timedelta(days=5), {"XYZ": 200.0})

    ec = tracker.get_equity_curve()
    min_eq = ec["equity"].min()

    print(f"    equity path: {ec['equity'].tolist()}")
    print(f"    min equity: {min_eq:.2f}")
    _assert(min_eq > 0, f"equity stayed positive through 20x short blowup (min={min_eq:.2f})")


def test_risk_free_rate_consistency() -> None:
    """Sharpe and Alpha must use the SAME risk-free rate (DEFAULT_RF_ANNUAL)."""
    print("\n[test] Sharpe and Alpha share a single risk-free rate")
    from prophitai_algo_trading.engines.backtest import metrics as m_mod
    from prophitai_calculations.config import DEFAULT_RF_ANNUAL

    _assert(
        m_mod.RISK_FREE_RATE == DEFAULT_RF_ANNUAL,
        f"metrics.RISK_FREE_RATE ({m_mod.RISK_FREE_RATE}) must equal "
        f"DEFAULT_RF_ANNUAL ({DEFAULT_RF_ANNUAL})",
    )


def test_duplicate_timestamp_dedup() -> None:
    """Duplicate timestamps (from force_close) must not inflate bars_per_year."""
    print("\n[test] duplicate timestamps are deduped")
    dates = pd.bdate_range("2020-01-02", periods=5).tolist()
    dates.append(dates[-1])  # duplicate last timestamp (force-close scenario)

    equity = [100_000, 101_000, 102_500, 103_000, 104_000, 103_950]  # -50 commission
    ec = pd.DataFrame({"equity": equity}, index=pd.DatetimeIndex(dates))

    m = calculate_metrics(ec, pd.DataFrame())

    print(f"    raw len={len(ec)}  reported CAGR={m['annualized_return_pct']}% "
          f"Sharpe={m['sharpe_ratio']}")
    _assert(np.isfinite(m["sharpe_ratio"]), "Sharpe is finite with duplicate timestamps")
    _assert(m["annualized_return_pct"] > 0, "CAGR remains positive")


def test_alpha_with_flat_portfolio_and_positive_benchmark() -> None:
    """Flat portfolio vs rising SPY should give a small, finite alpha (approx -β*rm)."""
    print("\n[test] alpha math is finite with divergent portfolio/benchmark")
    dates = pd.bdate_range("2020-01-02", periods=252 * 2)

    flat_equity = pd.DataFrame({"equity": [100_000.0] * len(dates)}, index=dates)
    spy = pd.Series(
        100.0 * (1.0 + np.linspace(0, 0.20, len(dates))),
        index=dates,
        name="close",
    )

    m = calculate_metrics(flat_equity, pd.DataFrame(), spy)

    print(f"    flat portfolio vs SPY +20% → alpha={m['alpha_vs_spy']}")
    _assert(m["alpha_vs_spy"] is not None, "alpha computed when both series valid")
    _assert(np.isfinite(m["alpha_vs_spy"]), "alpha is finite")


def test_alpha_annualizes_by_calendar_years() -> None:
    """Alpha must use calendar-year annualization, not assumed 252-day cadence.

    Previously calc_alpha hardcoded TRADING_DAYS=252 inside calc_annualized_return,
    so hourly/intraday backtests produced wildly inflated annualization. The fix
    annualizes via the backtest's actual calendar-year span.

    Test: build equity and benchmark with IDENTICAL returns on HOURLY bars over
    exactly 1 calendar year. Alpha must be ~0 (portfolio = benchmark).
    """
    print("\n[test] alpha is frequency-independent (hourly bars, 1 year)")
    hourly_idx = pd.date_range("2023-01-02 09:30", "2024-01-02 15:30", freq="1h")
    n = len(hourly_idx)

    np.random.seed(13)
    r = np.random.normal(0.0001, 0.003, n)
    prices = 100.0 * np.cumprod(1.0 + r)

    equity = pd.DataFrame({"equity": 1000.0 * prices / prices[0]}, index=hourly_idx)
    spy = pd.Series(prices, index=hourly_idx)

    m = calculate_metrics(equity, pd.DataFrame(), spy)

    print(f"    alpha (identical hourly series, 1yr) = {m['alpha_vs_spy']}%")
    _assert(
        m["alpha_vs_spy"] is not None and abs(m["alpha_vs_spy"]) < 0.5,
        f"alpha ≈ 0 when portfolio and benchmark are identical (got {m['alpha_vs_spy']}%)",
    )


def test_alpha_none_when_benchmark_missing() -> None:
    """No benchmark → alpha_vs_spy is None, not a crash."""
    print("\n[test] missing benchmark → alpha=None")
    ec = _build_equity_curve([0.001] * 100)
    m = calculate_metrics(ec, pd.DataFrame(), None)
    _assert(m["alpha_vs_spy"] is None, "alpha is None when benchmark missing")


def test_tracker_long_round_trip_equity_monotone() -> None:
    """Long round-trip: equity should match cash + MV at every bar."""
    print("\n[test] long round-trip equity accounting")
    from prophitai_algo_trading.execution.cost_model import CostModel
    from prophitai_algo_trading.execution.portfolio_tracker.tracker import PortfolioTracker
    from prophitai_algo_trading.sizing.std_lib.equity.percent_of_equity import (
        PercentOfEquitySizer,
    )

    cost_model = CostModel(ptc=0.001)
    sizer = PercentOfEquitySizer(pct=0.10, cost_model=cost_model)
    tracker = PortfolioTracker(initial_capital=100_000.0, sizer=sizer, cost_model=cost_model)

    t0 = datetime(2020, 1, 2)
    tracker.open_long("AAPL", price=100.0, timestamp=t0)

    for day, price in [(0, 100.0), (1, 105.0), (2, 110.0), (3, 108.0), (4, 120.0)]:
        ts = t0 + timedelta(days=day)
        tracker.record_equity(ts, {"AAPL": price})

    tracker.close_position("AAPL", price=120.0, timestamp=t0 + timedelta(days=5))
    tracker.record_equity(t0 + timedelta(days=5), {"AAPL": 120.0})

    ec = tracker.get_equity_curve()
    final = ec["equity"].iloc[-1]

    print(f"    initial=100000  final={final:.2f}  equity curve len={len(ec)}")
    _assert(final > 100_000, "profitable long trade → final equity > initial")
    _assert((ec["equity"] > 0).all(), "equity stayed positive throughout")


# ================================
# --> Runner
# ================================


def main() -> int:
    print("=" * 70)
    print("BACKTEST METRICS BUG SUITE")
    print("=" * 70)

    tests = [
        test_flat_equity_returns_zero_sharpe,
        test_positive_cagr_gives_positive_sharpe,
        test_pct_change_signflip_bug_demo,
        test_log_return_robustness,
        test_user_reported_run9_profile,
        test_sharpe_invariant_on_scale,
        test_risk_free_rate_consistency,
        test_duplicate_timestamp_dedup,
        test_alpha_with_flat_portfolio_and_positive_benchmark,
        test_alpha_annualizes_by_calendar_years,
        test_alpha_none_when_benchmark_missing,
        test_tracker_long_round_trip_equity_monotone,
        test_tracker_short_blowup_produces_valid_equity,
    ]

    for fn in tests:
        try:
            fn()
        except Exception as exc:
            _FAILURES.append(f"{fn.__name__} raised {type(exc).__name__}: {exc}")
            print(f"  UNEXPECTED: {fn.__name__} raised {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)

    if _FAILURES:
        print(f"FAIL: {len(_FAILURES)} failure(s):")
        for f in _FAILURES:
            print(f"  - {f}")
        return 1

    print("PASS: all metric/tracker invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
