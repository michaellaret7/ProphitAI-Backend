"""Real-data tests for the new quant screener calculation functions.

Each function is verified against synthetic data with known mathematical
properties. Run this as a script (no pytest framework) per project convention.

Functions tested:
    - calc_hurst_exponent
    - calc_ou_half_life
    - calc_frog_in_pan
    - calc_roll_spread
    - calc_rolling_beta
    (calc_upside_capture / calc_downside_capture already existed)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from prophitai_calculations.risk.benchmark import (
    calc_downside_capture,
    calc_rolling_beta,
    calc_upside_capture,
)
from prophitai_calculations.technicals.momentum import calc_frog_in_pan
from prophitai_calculations.technicals.statistical import (
    calc_hurst_exponent,
    calc_ou_half_life,
)
from prophitai_calculations.technicals.volume import calc_roll_spread


# ================================
# --> Helper funcs
# ================================

def _make_date_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range(end='2026-01-01', periods=n, freq='B')


def _expect(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        raise AssertionError(f"{label} failed: {detail}")


# ================================
# --> Hurst exponent
# ================================

def test_hurst_exponent() -> None:
    print("\n=== calc_hurst_exponent ===")
    rng = np.random.default_rng(seed=42)
    n = 400

    # --- Mean-reverting: Ornstein-Uhlenbeck process on log-prices ---
    # Log-prices revert strongly to a mean, so cumulative log-returns stay bounded.
    # R/S grows slower than sqrt(n) → H < 0.5.
    theta = 0.15  # mean-reversion speed
    sigma = 0.02
    mean_log = np.log(100.0)
    log_prices = np.zeros(n)
    log_prices[0] = mean_log
    for i in range(1, n):
        log_prices[i] = log_prices[i - 1] + theta * (mean_log - log_prices[i - 1]) + rng.normal(0, sigma)
    mr_series = pd.Series(np.exp(log_prices), index=_make_date_index(n))
    h_mr = calc_hurst_exponent(mr_series, window=252)
    print(f"  Mean-reverting (OU) H = {h_mr:.3f}")
    _expect("mean-reverting returns H < 0.5",
            h_mr is not None and h_mr < 0.5,
            f"expected <0.5, got {h_mr}")

    # --- Random walk: i.i.d. log-returns → H ~= 0.5 ---
    rw_returns = rng.normal(0, 0.01, n)
    rw_prices = 100 * np.exp(np.cumsum(rw_returns))
    rw_series = pd.Series(rw_prices, index=_make_date_index(n))
    h_rw = calc_hurst_exponent(rw_series, window=252)
    print(f"  Random walk H = {h_rw:.3f}")
    _expect("random walk near 0.5",
            h_rw is not None and 0.35 < h_rw < 0.65,
            f"expected ~0.5, got {h_rw}")

    # --- Persistent: smoothed i.i.d. (moving-average of returns) → H > 0.5 ---
    # Smoothing induces positive lag-1 autocorrelation, so H should be > 0.5.
    raw = rng.normal(0, 0.01, n)
    smoothed_returns = pd.Series(raw).rolling(window=5, min_periods=1).mean().to_numpy()
    persist_prices = 100 * np.exp(np.cumsum(smoothed_returns))
    persist_series = pd.Series(persist_prices, index=_make_date_index(n))
    h_persist = calc_hurst_exponent(persist_series, window=252)
    print(f"  Persistent (smoothed) H = {h_persist:.3f}")
    _expect("persistent series H > 0.5",
            h_persist is not None and h_persist > 0.5,
            f"expected >0.5, got {h_persist}")


# ================================
# --> OU half-life
# ================================

def test_ou_half_life() -> None:
    print("\n=== calc_ou_half_life ===")
    rng = np.random.default_rng(seed=7)

    # Build an AR(1) process: x_t = phi * x_{t-1} + eps
    # Half-life = -ln(2) / ln(phi)
    phi = 0.9
    true_half_life = -np.log(2) / np.log(phi)  # ~= 6.58 days
    n = 400
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = phi * x[i - 1] + rng.normal(0, 1)
    ar1_series = pd.Series(x, index=_make_date_index(n))

    estimated = calc_ou_half_life(ar1_series, window=252)
    print(f"  True half-life = {true_half_life:.2f}, estimated = {estimated}")
    _expect("AR(1) half-life recovered within ±30%",
            estimated is not None and abs(estimated - true_half_life) / true_half_life < 0.3,
            f"expected ~{true_half_life:.2f}, got {estimated}")

    # Strongly persistent (phi close to 1): very slow reversion → either huge half-life or None
    phi_persist = 0.99
    x_persist = np.zeros(n)
    for i in range(1, n):
        x_persist[i] = phi_persist * x_persist[i - 1] + rng.normal(0, 1)
    hl_persist = calc_ou_half_life(pd.Series(x_persist, index=_make_date_index(n)), window=252)
    print(f"  Persistent (phi=0.99) half-life = {hl_persist}")
    _expect("persistent series half-life >> AR(1) half-life or None",
            hl_persist is None or hl_persist > 2 * true_half_life,
            f"expected >> {true_half_life:.1f}, got {hl_persist}")


# ================================
# --> Frog in the Pan
# ================================

def test_frog_in_pan() -> None:
    print("\n=== calc_frog_in_pan ===")
    n = 300
    idx = _make_date_index(n)

    # Continuous: many small positive moves — starts at 100, ends higher
    rng = np.random.default_rng(42)
    continuous_returns = rng.normal(0.001, 0.005, n)  # mostly small positives
    continuous_prices = 100 * np.exp(np.cumsum(continuous_returns))
    continuous = pd.Series(continuous_prices, index=idx)

    # Discrete: mostly zeros/tiny negatives but a few large positive jumps
    discrete_returns = np.full(n, -0.0005)
    # Inject 10 large positive jumps that dominate the cumulative return
    jump_idx = rng.choice(n, size=10, replace=False)
    discrete_returns[jump_idx] = 0.05
    discrete_prices = 100 * np.exp(np.cumsum(discrete_returns))
    discrete = pd.Series(discrete_prices, index=idx)

    id_continuous = calc_frog_in_pan(continuous, window=252, skip_recent=0)
    id_discrete = calc_frog_in_pan(discrete, window=252, skip_recent=0)

    print(f"  Continuous ID = {id_continuous:.3f}")
    print(f"  Discrete ID   = {id_discrete:.3f}")
    _expect("continuous ID < discrete ID (better momentum quality)",
            id_continuous is not None and id_discrete is not None and id_continuous < id_discrete,
            f"{id_continuous} vs {id_discrete}")


# ================================
# --> Roll spread
# ================================

def test_roll_spread() -> None:
    print("\n=== calc_roll_spread ===")
    rng = np.random.default_rng(42)

    # Simulate bid-ask bounce: true price random walk + alternating buy/sell
    n = 400
    true_price = 100 + rng.normal(0, 0.1, n).cumsum()
    true_spread = 0.10  # 10 cent spread
    # Each observation is at bid or ask randomly
    bid_ask_sign = rng.choice([-1, 1], size=n)
    observed = true_price + bid_ask_sign * true_spread / 2

    prices = pd.Series(observed, index=_make_date_index(n))
    estimated_spread = calc_roll_spread(prices, window=252)

    print(f"  True spread = {true_spread:.3f}, estimated = {estimated_spread}")
    _expect("Roll spread within ±50% of true spread",
            estimated_spread is not None
            and 0.5 * true_spread < estimated_spread < 1.5 * true_spread,
            f"expected ~{true_spread}, got {estimated_spread}")

    # Clean random walk (no bounce) → covariance >= 0 → None
    clean_prices = pd.Series(100 + rng.normal(0, 0.5, n).cumsum(), index=_make_date_index(n))
    clean_estimate = calc_roll_spread(clean_prices, window=252)
    print(f"  Clean random walk estimate = {clean_estimate}")
    # Note: random walk can sometimes produce tiny negative cov by chance, not asserting strict None


# ================================
# --> Up / Down capture (existing, verify behavior)
# ================================

def test_up_down_capture() -> None:
    print("\n=== calc_upside_capture / calc_downside_capture ===")
    rng = np.random.default_rng(42)
    n = 252
    idx = _make_date_index(n)

    # Identical returns → both captures = 100%
    bench = pd.Series(rng.normal(0.0005, 0.01, n), index=idx)
    port = bench.copy()

    up = calc_upside_capture(port, bench)
    down = calc_downside_capture(port, bench)
    print(f"  Perfect tracking: up = {up:.2f}, down = {down:.2f}")
    _expect("perfect tracking up capture ~= 100",
            up is not None and abs(up - 100) < 1, f"got {up}")
    _expect("perfect tracking down capture ~= 100",
            down is not None and abs(down - 100) < 1, f"got {down}")


# ================================
# --> Rolling beta
# ================================

def test_rolling_beta() -> None:
    print("\n=== calc_rolling_beta ===")
    rng = np.random.default_rng(42)
    n = 252
    idx = _make_date_index(n)

    bench = pd.Series(rng.normal(0.0005, 0.01, n), index=idx)
    # Portfolio with true beta = 1.5
    port = 1.5 * bench + pd.Series(rng.normal(0, 0.002, n), index=idx)

    rolling = calc_rolling_beta(port, bench, window=60)
    print(f"  Rolling beta mean = {rolling.mean():.3f}, std = {rolling.std():.3f}")
    _expect("rolling beta length > 0", len(rolling) > 0,
            f"got {len(rolling)}")
    _expect("rolling beta mean near 1.5",
            abs(rolling.mean() - 1.5) < 0.3, f"got {rolling.mean():.3f}")


# ================================
# --> Main
# ================================

def main() -> None:
    print("Running real-data tests for quant screener calculations...")
    test_hurst_exponent()
    test_ou_half_life()
    test_frog_in_pan()
    test_roll_spread()
    test_up_down_capture()
    test_rolling_beta()
    print("\nAll tests passed.")


if __name__ == '__main__':
    main()
