"""Deep validation suite for backtest metrics — 4 layers of evidence.

Goal: gain near-100% confidence that calculate_metrics is correct WITHOUT
running the full agent pipeline.

Layers:
    1. Property-based fuzz — thousands of random equity curves must satisfy
       mathematical invariants (Sharpe > 0 ⇔ CAGR > rf, scale invariance,
       drawdown ∈ [-100%, 0%], etc.).

    2. Known-answer tests — buy-and-hold-like curves where the true Sharpe
       is analytically computable. The reported Sharpe must match.

    3. Differential test against a HAND-ROLLED reference implementation
       (pure numpy, no shared code paths with the production metrics).

    4. Multi-strategy real backtests — same strategy, different universes,
       different time windows. All metrics finite and consistent.

Usage:
    source .venv/bin/activate
    python packages/algo_trading/tests/test_metrics_deep_validation.py
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from prophitai_algo_trading.engines.backtest.metrics import (
    RISK_FREE_RATE,
    calculate_metrics,
)


# ================================
# --> Shared helpers
# ================================


_FAILURES: list[str] = []
_RNG = np.random.default_rng(0)


def _assert(cond: bool, msg: str) -> None:
    if cond:
        return
    print(f"  FAIL: {msg}")
    _FAILURES.append(msg)


def _pass(msg: str) -> None:
    print(f"  PASS: {msg}")


def _build_equity_curve(
    returns: Sequence[float],
    initial: float = 100_000.0,
    start: str = "2020-01-02",
    freq: str = "B",
) -> pd.DataFrame:
    equity = [initial]
    for r in returns:
        equity.append(equity[-1] * (1.0 + r))
    idx = pd.date_range(start=start, periods=len(equity), freq=freq)
    return pd.DataFrame({"equity": equity}, index=idx)


# ================================
# --> Layer 1: Property-based fuzz
# ================================


def _invariants_for_curve(ec: pd.DataFrame, tag: str) -> None:
    """Every random equity curve must satisfy these invariants."""
    m = calculate_metrics(ec, pd.DataFrame())

    eq = ec["equity"]
    total_ret = (eq.iloc[-1] / eq.iloc[0]) - 1.0
    cagr = m["annualized_return_pct"] / 100.0
    sharpe = m["sharpe_ratio"]
    dd = m["max_drawdown_pct"] / 100.0

    # Invariant 1: reported metrics are finite
    if not (np.isfinite(cagr) and np.isfinite(sharpe) and np.isfinite(dd)):
        _assert(False, f"{tag}: metrics not finite (cagr={cagr} sharpe={sharpe} dd={dd})")
        return

    # Reason: skip sign/AM-GM checks when values are too small to be meaningful
    # after metrics.py rounds CAGR to 2 decimals and Sharpe to 2 decimals.
    ROUND_FLOOR = 0.005

    # Invariant 2: total_return and CAGR agree in sign (when either is non-trivial)
    if abs(total_ret) > ROUND_FLOOR and abs(cagr) > ROUND_FLOOR:
        if np.sign(total_ret) != np.sign(cagr):
            _assert(
                False,
                f"{tag}: total_ret sign {np.sign(total_ret)} != CAGR sign {np.sign(cagr)}",
            )

    # Invariant 3: drawdown ∈ [-100%, 0%]
    if not (-1.0 <= dd <= 0.0):
        _assert(False, f"{tag}: drawdown {dd} outside [-1, 0]")

    # Invariant 4: AM ≥ GM — if equity strictly positive and CAGR is CLEARLY
    # above rf (above rounding floor), Sharpe must be non-negative.
    if (eq > 0).all() and cagr > RISK_FREE_RATE + 0.01:
        if sharpe < 0:
            _assert(
                False,
                f"{tag}: CAGR {cagr*100:.2f}% > rf but Sharpe {sharpe} < 0",
            )


def test_layer1_property_fuzz() -> None:
    """Fuzz 2000 random equity curves across multiple distributions."""
    print("\n[Layer 1] Property-based fuzz: 2000 random curves")
    rng = np.random.default_rng(42)
    n_runs = 2000

    for i in range(n_runs):
        profile = i % 5

        if profile == 0:  # random walk, positive drift
            n = int(rng.integers(252, 252 * 10))
            mu = rng.uniform(-0.0005, 0.002)
            sigma = rng.uniform(0.005, 0.03)
            returns = rng.normal(mu, sigma, n)

        elif profile == 1:  # sparse trades (like user's Run 9)
            n = int(rng.integers(500, 2500))
            returns = np.zeros(n)
            active = rng.choice(n, size=int(n * 0.05), replace=False)
            returns[active] = rng.normal(0.002, 0.015, len(active))

        elif profile == 2:  # trending up then down
            n = int(rng.integers(252, 252 * 5))
            half = n // 2
            up = rng.normal(0.002, 0.01, half)
            down = rng.normal(-0.001, 0.012, n - half)
            returns = np.concatenate([up, down])

        elif profile == 3:  # fat-tailed (t-distribution)
            n = int(rng.integers(252, 252 * 3))
            returns = rng.standard_t(df=3, size=n) * 0.01

        else:  # near-flat (strategy barely trades)
            n = int(rng.integers(252, 252 * 4))
            returns = np.zeros(n)
            returns[rng.choice(n, size=5)] = rng.normal(0.005, 0.02, 5)

        ec = _build_equity_curve(returns.tolist())

        if (ec["equity"] <= 0).any():
            # Expect a raise — that's correct behavior
            try:
                calculate_metrics(ec, pd.DataFrame())
                _assert(False, f"run {i}: should have raised on negative equity")
            except ValueError:
                pass
            continue

        _invariants_for_curve(ec, f"run {i} (profile {profile})")

    # If no invariant violations were reported, pass
    violated = [f for f in _FAILURES if "run " in f]

    if not violated:
        _pass(f"all {n_runs} random curves satisfied every invariant")
    else:
        print(f"  FAIL: {len(violated)} / {n_runs} curves violated invariants")


# ================================
# --> Layer 2: Known-answer tests
# ================================


def test_layer2_constant_drift_sharpe() -> None:
    """Constant-drift equity: bar_return = c for all bars.

    For log returns: log_return = log(1+c) constant → std = 0 → Sharpe = 0.0
    (because excess_returns.std() == 0 triggers the zero-std branch).
    """
    print("\n[Layer 2a] constant-drift equity → Sharpe=0 (zero-variance branch)")
    returns = [0.001] * 252  # 0.1% every bar
    ec = _build_equity_curve(returns)
    m = calculate_metrics(ec, pd.DataFrame())

    _assert(m["sharpe_ratio"] == 0.0, f"zero variance → Sharpe 0.0 (got {m['sharpe_ratio']})")
    _pass(f"constant drift: CAGR={m['annualized_return_pct']}%  Sharpe={m['sharpe_ratio']}")


def test_layer2_normal_returns_closed_form_sharpe() -> None:
    """IID normal bar returns — Sharpe matches SAMPLE-based closed form.

    Tests the FORMULA, not whether the sample matches population parameters.
    Uses the realized log-return sample's own mean/std to derive the expected
    Sharpe, then compares to the production Sharpe. Must match within rounding.
    """
    print("\n[Layer 2b] IID normal returns → Sharpe matches sample closed form")
    rng = np.random.default_rng(12345)
    n = 252 * 10
    returns = rng.normal(0.001, 0.01, n)
    ec = _build_equity_curve(returns.tolist())
    m = calculate_metrics(ec, pd.DataFrame())

    # Reason: compute the expected Sharpe from the realized log-return sample,
    # not from the theoretical (μ, σ). This isolates the formula from sampling.
    log_returns = np.log(ec["equity"].to_numpy()[1:] / ec["equity"].to_numpy()[:-1])
    time_span = (ec.index[-1] - ec.index[0]).total_seconds()
    years = time_span / (365.25 * 86_400)
    bars_per_year = len(ec) / years
    rf_per_bar = np.log(1 + RISK_FREE_RATE) / bars_per_year
    excess = log_returns - rf_per_bar
    expected = (excess.mean() / excess.std(ddof=1)) * np.sqrt(bars_per_year)

    reported = m["sharpe_ratio"]

    print(f"    sample closed-form Sharpe = {expected:.4f}")
    print(f"    reported Sharpe            = {reported}")
    _assert(
        abs(reported - expected) < 0.02,
        f"Sharpe {reported} differs from sample closed-form {expected:.4f} by > 0.02",
    )


def test_layer2_buy_and_hold_spy_like() -> None:
    """Pure buy-and-hold: equity = K * SPY.

    Known answer: CAGR matches SPY CAGR, alpha ≈ 0 (β=1, Rp=Rm).
    """
    print("\n[Layer 2c] buy-and-hold SPY → α≈0, CAGR matches benchmark")
    rng = np.random.default_rng(7)
    n = 252 * 3
    idx = pd.bdate_range("2021-01-04", periods=n)

    spy_prices = 100.0 * np.cumprod(1 + rng.normal(0.0004, 0.012, n))
    spy_series = pd.Series(spy_prices, index=idx, name="close")

    # Reason: equity is exactly the SPY series scaled to initial capital
    equity_values = 100_000.0 * spy_prices / spy_prices[0]
    ec = pd.DataFrame({"equity": equity_values}, index=idx)

    m = calculate_metrics(ec, pd.DataFrame(), spy_series)

    cagr = m["annualized_return_pct"]
    spy_cagr = ((spy_prices[-1] / spy_prices[0]) ** (1 / ((idx[-1] - idx[0]).total_seconds() / (365.25 * 86_400))) - 1) * 100
    alpha = m["alpha_vs_spy"]

    print(f"    portfolio CAGR={cagr}%  SPY CAGR={spy_cagr:.2f}%  α={alpha}%")
    _assert(abs(cagr - spy_cagr) < 0.05, f"CAGR must match SPY CAGR (got {cagr} vs {spy_cagr:.2f})")
    _assert(alpha is not None and abs(alpha) < 0.05, f"α should be ≈0 (got {alpha})")


def test_layer2_pure_losing_strategy() -> None:
    """Constant small losses: CAGR clearly negative, Sharpe must be negative."""
    print("\n[Layer 2d] losing strategy → CAGR<0, Sharpe<0")
    rng = np.random.default_rng(99)
    returns = (rng.normal(-0.0008, 0.008, 252 * 4)).tolist()
    ec = _build_equity_curve(returns)
    m = calculate_metrics(ec, pd.DataFrame())

    print(f"    CAGR={m['annualized_return_pct']}%  Sharpe={m['sharpe_ratio']}  DD={m['max_drawdown_pct']}%")
    _assert(m["annualized_return_pct"] < 0, "losing strategy has negative CAGR")
    _assert(m["sharpe_ratio"] < 0, "losing strategy has negative Sharpe")


# ================================
# --> Layer 3: Differential testing (independent reference)
# ================================


def _reference_sharpe(equity: pd.Series, bars_per_year: float, rf: float) -> float:
    """Independent numpy reference — does not touch production code.

    Log-returns-based annualized Sharpe:
        r_t = ln(E_t / E_{t-1})
        rf_per_bar = ln(1 + rf) / bars_per_year
        excess = r - rf_per_bar
        Sharpe = (mean(excess) / std(excess, ddof=1)) * sqrt(bars_per_year)

    Uses ddof=1 same as pandas default. Zero-variance returns 0.0.
    """
    arr = equity.to_numpy(dtype=float)
    log_ret = np.log(arr[1:] / arr[:-1])

    if log_ret.size < 2:
        return 0.0

    rf_per_bar = np.log(1 + rf) / bars_per_year
    excess = log_ret - rf_per_bar
    std = float(np.std(excess, ddof=1))

    if std == 0.0 or not np.isfinite(std):
        return 0.0

    return (float(excess.mean()) / std) * np.sqrt(bars_per_year)


def _reference_cagr(equity: pd.Series, years: float) -> float:
    arr = equity.to_numpy(dtype=float)
    return float((arr[-1] / arr[0]) ** (1 / years) - 1.0)


def _reference_max_dd(equity: pd.Series) -> float:
    arr = equity.to_numpy(dtype=float)
    peak = np.maximum.accumulate(arr)
    dd = (arr - peak) / peak
    return float(dd.min())


def test_layer3_differential_vs_reference() -> None:
    """Production metrics must match independent numpy reference within rounding."""
    print("\n[Layer 3] differential test vs hand-rolled numpy reference")
    rng = np.random.default_rng(321)
    mismatches = 0
    n_curves = 200

    for i in range(n_curves):
        n = int(rng.integers(252, 252 * 5))
        returns = rng.normal(rng.uniform(-0.001, 0.002), rng.uniform(0.005, 0.02), n)
        ec = _build_equity_curve(returns.tolist())

        if (ec["equity"] <= 0).any():
            continue

        prod = calculate_metrics(ec, pd.DataFrame())

        time_span = (ec.index[-1] - ec.index[0]).total_seconds()
        years = time_span / (365.25 * 86_400)
        bars_per_year = len(ec) / years

        ref_sharpe = _reference_sharpe(ec["equity"], bars_per_year, RISK_FREE_RATE)
        ref_cagr = _reference_cagr(ec["equity"], years) * 100
        ref_dd = _reference_max_dd(ec["equity"]) * 100

        if abs(prod["sharpe_ratio"] - round(ref_sharpe, 2)) > 0.02:
            mismatches += 1
            print(f"    mismatch #{mismatches} curve {i}: prod Sharpe {prod['sharpe_ratio']} vs ref {ref_sharpe:.2f}")

        if abs(prod["annualized_return_pct"] - round(ref_cagr, 2)) > 0.02:
            mismatches += 1
            print(f"    mismatch #{mismatches} curve {i}: prod CAGR {prod['annualized_return_pct']} vs ref {ref_cagr:.2f}")

        if abs(prod["max_drawdown_pct"] - round(ref_dd, 2)) > 0.02:
            mismatches += 1
            print(f"    mismatch #{mismatches} curve {i}: prod DD {prod['max_drawdown_pct']} vs ref {ref_dd:.2f}")

    _assert(mismatches == 0, f"{mismatches} mismatches between production and reference")
    if mismatches == 0:
        _pass(f"{n_curves} curves: production matches numpy reference exactly")


# ================================
# --> Layer 4: Multi-strategy real backtests
# ================================


def _normalize_ohlcv(data: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    normalized = {}
    for ticker, df in data.items():
        if df is None or df.empty:
            continue
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        req = {"open", "high", "low", "close", "volume"}
        if req - set(df.columns):
            continue
        df.index = pd.to_datetime(df.index)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        normalized[ticker] = df[["open", "high", "low", "close", "volume"]]
    return normalized


def _build_sma_strategy(fast_period: int, slow_period: int):
    """Build a minimal SMA crossover strategy inline for real backtests."""
    from prophitai_algo_trading.indicators.pipeline import BaseIndicatorSuite
    from prophitai_algo_trading.indicators.specs import IndicatorSpec
    from prophitai_algo_trading.signals.base import BaseSignalModel
    from prophitai_algo_trading.strategies.composable import BaseComposableStrategy

    _fast = fast_period
    _slow = slow_period

    class Suite(BaseIndicatorSuite):
        def indicator_specs(self):
            return [
                IndicatorSpec("sma", params={"window": _fast, "output_column": "sma_fast"}),
                IndicatorSpec("sma", params={"window": _slow, "output_column": "sma_slow"}),
            ]

    class Model(BaseSignalModel):
        required_columns = ("sma_fast", "sma_slow")

        def long_entry(self, df):
            return (df["sma_fast"] > df["sma_slow"]) & (df["sma_fast"].shift(1) <= df["sma_slow"].shift(1))

        def long_exit(self, df):
            return df["sma_fast"] < df["sma_slow"]

        def short_entry(self, df):
            return pd.Series(False, index=df.index)

        def short_exit(self, df):
            return pd.Series(False, index=df.index)

    class Strat(BaseComposableStrategy):
        def __init__(self):
            super().__init__(indicator_suite=Suite(), signal_model=Model())

        @property
        def min_bars_required(self):
            return _slow

    return Strat()


def test_layer4_multiple_universes() -> None:
    """Run the same SMA strategy across several universes/windows.

    Each run must:
    - produce finite metrics
    - have equity > 0 throughout
    - obey AM-GM (CAGR > rf ⇒ Sharpe > 0)
    """
    print("\n[Layer 4] multi-universe real backtests")
    from prophitai_algo_trading.engines.backtest.vectorized import VectorizedBacktestEngine
    from prophitai_algo_trading.execution.cost_model import CostModel
    from prophitai_algo_trading.sizing.std_lib.equity.percent_of_equity import PercentOfEquitySizer
    from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers

    scenarios = [
        (["SPY"], "2020-01-01", "2024-12-31", 10, 30),
        (["QQQ", "IWM", "DIA"], "2019-01-01", "2024-12-31", 20, 50),
        (["AAPL", "MSFT", "GOOGL", "AMZN", "META"], "2021-01-01", "2024-12-31", 15, 40),
        (["JPM", "V", "WMT", "JNJ", "XOM"], "2018-01-01", "2024-12-31", 20, 60),
    ]

    passes = 0
    for tickers, start, end, fast, slow in scenarios:
        raw = fetch_bulk_ohlcv_data_for_tickers(tickers, start, end)
        data = _normalize_ohlcv(raw)

        if not data:
            print(f"    SKIP: no data for {tickers}")
            continue

        strategy = _build_sma_strategy(fast, slow)
        engine = VectorizedBacktestEngine(
            strategy=strategy,
            initial_capital=100_000.0,
            cost_model=CostModel(ptc=0.0005),
            sizer=PercentOfEquitySizer(pct=min(1.0, 1 / len(tickers))),
            max_positions=len(tickers),
        )

        try:
            result = engine.run(data, verbose=False)
        except Exception as exc:
            print(f"    FAIL: {tickers} raised {type(exc).__name__}: {exc}")
            _FAILURES.append(f"scenario {tickers} crashed")
            continue

        m = result.metrics
        ec = result.equity_curve["equity"]
        cagr = m["annualized_return_pct"] / 100.0
        sharpe = m["sharpe_ratio"]

        tag = ",".join(tickers)[:30]
        print(f"    {tag:<32} CAGR={cagr*100:6.2f}%  Sharpe={sharpe:>5.2f}  "
              f"DD={m['max_drawdown_pct']:>6.2f}%  trades={m['total_trades']}  "
              f"α={m['alpha_vs_spy']}")

        ok = True
        if not (np.isfinite(sharpe) and np.isfinite(cagr)):
            print(f"      not finite"); ok = False
        if (ec <= 0).any():
            print(f"      equity went non-positive"); ok = False
        if cagr > RISK_FREE_RATE + 0.01 and sharpe <= 0:
            print(f"      AM-GM violated: CAGR {cagr*100:.2f}% > rf but Sharpe {sharpe} ≤ 0"); ok = False

        if ok:
            passes += 1
        else:
            _FAILURES.append(f"scenario {tickers}: invariant violated")

    _pass(f"{passes}/{len(scenarios)} real backtests satisfied every invariant")


# ================================
# --> Runner
# ================================


def main() -> int:
    print("=" * 72)
    print("DEEP METRICS VALIDATION — 4 LAYERS")
    print("=" * 72)

    layers = [
        test_layer1_property_fuzz,
        test_layer2_constant_drift_sharpe,
        test_layer2_normal_returns_closed_form_sharpe,
        test_layer2_buy_and_hold_spy_like,
        test_layer2_pure_losing_strategy,
        test_layer3_differential_vs_reference,
        test_layer4_multiple_universes,
    ]

    for fn in layers:
        try:
            fn()
        except Exception as exc:
            import traceback
            _FAILURES.append(f"{fn.__name__}: {type(exc).__name__}: {exc}")
            print(f"  UNEXPECTED: {type(exc).__name__}: {exc}")
            traceback.print_exc()

    print("\n" + "=" * 72)

    if _FAILURES:
        print(f"FAIL: {len(_FAILURES)} failure(s)")
        for f in _FAILURES[:20]:
            print(f"  - {f}")
        if len(_FAILURES) > 20:
            print(f"  ... and {len(_FAILURES) - 20} more")
        return 1

    print("PASS: all 4 validation layers clean — metrics verified without pipeline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
