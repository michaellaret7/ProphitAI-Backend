# pyportfolioopt_real_data_test.py
"""
Single-file: PyPortfolioOpt tests + runnable main block.

Requirements implemented:
- 15-position universe (9 equities, 6 bonds)
- Long-only
- 60/40 bucket constraint enforced for BOTH min-vol and max-sharpe
- No zero allocations: enforce a strictly-positive floor weight for every asset
  (via weight_bounds=(min_w, max_w))

Run as script:
  python t.py
"""

import numpy as np
import pandas as pd

from pypfopt import EfficientFrontier, expected_returns, risk_models
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

import warnings 
warnings.filterwarnings("ignore", category=RuntimeWarning)

# 9 equity tickers (60% allocation)
EQUITY_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "JNJ", "V"]

# 6 bond ETF tickers (40% allocation)
BOND_TICKERS = ["AGG", "BND", "TLT", "IEF", "LQD", "VCIT"]


def fetch_prices(tickers: list, lookback_days: int = 504) -> pd.DataFrame:
    """Fetch real price data from database and return as DataFrame."""
    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(lookback_days).strftime('%Y-%m-%d')

    price_map = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date, frequency='daily')

    prices_df = pd.DataFrame(price_map)
    prices_df = prices_df.dropna()

    return prices_df


def assert_weights_ok(
    cleaned: dict,
    tickers,
    min_w: float,
    max_w: float,
    tol: float = 1e-6,
):
    assert set(cleaned.keys()) == set(tickers)
    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    assert np.isfinite(ws).all()
    assert abs(ws.sum() - 1.0) <= 1e-4

    # enforce strictly positive allocations (within tolerance)
    assert (ws >= (min_w - 1e-4)).all(), f"Found weight below min_w={min_w}: {cleaned}"

    # enforce max position cap
    assert (ws <= (max_w + 1e-4)).all(), f"Found weight above max_w={max_w}: {cleaned}"


def suggested_max_weight(n_assets: int, multiple: float = 1.5) -> float:
    """
    Rule-of-thumb:
      max_weight = multiple * equal_weight
    For 15 assets: 1.5 * (1/15) = 0.10 (10%)
    """
    return float(multiple / n_assets)


def build_inputs():
    """Build inputs using real price data from database."""
    all_tickers = EQUITY_TICKERS + BOND_TICKERS
    prices = fetch_prices(all_tickers, lookback_days=504)

    # Use actual column order from prices DataFrame
    tickers = list(prices.columns)

    mu = expected_returns.mean_historical_return(prices, frequency=252)
    S = risk_models.sample_cov(prices, frequency=252)

    equities = set(EQUITY_TICKERS)
    bonds = set(BOND_TICKERS)

    return tickers, prices, mu, S, equities, bonds


def solve_min_vol_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w):
    eq_idx = [tickers.index(t) for t in tickers if t in equities]
    bnd_idx = [tickers.index(t) for t in tickers if t in bonds]

    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
    ef.add_constraint(lambda w: w[eq_idx].sum() == 0.60)
    ef.add_constraint(lambda w: w[bnd_idx].sum() == 0.40)

    ef.min_volatility()
    cleaned = ef.clean_weights()
    return ef, cleaned


def solve_max_sharpe_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, rf=0.02):
    eq_idx = [tickers.index(t) for t in tickers if t in equities]
    bnd_idx = [tickers.index(t) for t in tickers if t in bonds]

    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
    ef.add_constraint(lambda w: w[eq_idx].sum() == 0.60)
    ef.add_constraint(lambda w: w[bnd_idx].sum() == 0.40)

    ef.max_sharpe(risk_free_rate=rf)
    cleaned = ef.clean_weights()
    return ef, cleaned


def solve_max_utility_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, risk_aversion=5.0):
    eq_idx = [tickers.index(t) for t in tickers if t in equities]
    bnd_idx = [tickers.index(t) for t in tickers if t in bonds]

    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
    ef.add_constraint(lambda w: w[eq_idx].sum() == 0.60)
    ef.add_constraint(lambda w: w[bnd_idx].sum() == 0.40)

    ef.max_quadratic_utility(risk_aversion=risk_aversion)
    cleaned = ef.clean_weights()
    return ef, cleaned


def solve_efficient_risk_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, target_volatility=0.10):
    eq_idx = [tickers.index(t) for t in tickers if t in equities]
    bnd_idx = [tickers.index(t) for t in tickers if t in bonds]

    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
    ef.add_constraint(lambda w: w[eq_idx].sum() == 0.60)
    ef.add_constraint(lambda w: w[bnd_idx].sum() == 0.40)

    ef.efficient_risk(target_volatility=target_volatility)
    cleaned = ef.clean_weights()
    return ef, cleaned


def solve_efficient_return_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, target_return=0.08):
    eq_idx = [tickers.index(t) for t in tickers if t in equities]
    bnd_idx = [tickers.index(t) for t in tickers if t in bonds]

    ef = EfficientFrontier(mu, S, weight_bounds=(min_w, max_w))
    ef.add_constraint(lambda w: w[eq_idx].sum() == 0.60)
    ef.add_constraint(lambda w: w[bnd_idx].sum() == 0.40)

    ef.efficient_return(target_return=target_return)
    cleaned = ef.clean_weights()
    return ef, cleaned


def bucket_weights(cleaned, equities, bonds):
    eq_w = sum(cleaned[t] for t in equities)
    bnd_w = sum(cleaned[t] for t in bonds)
    return float(eq_w), float(bnd_w)


# ------------------------
# Pytest-style tests
# ------------------------

def test_min_vol_enforces_60_40_and_no_zeros():
    tickers, prices, mu, S, equities, bonds = build_inputs()

    n = len(tickers)
    max_w = suggested_max_weight(n, multiple=1.5)  # ~10%
    min_w = 0.005  # 0.5% floor so nothing is zero

    ef, w = solve_min_vol_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)

    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    assert abs(eq_w - 0.60) <= 1e-3
    assert abs(bnd_w - 0.40) <= 1e-3

    ret, vol, sharpe = ef.portfolio_performance(verbose=False)
    assert np.isfinite(ret) and np.isfinite(vol) and np.isfinite(sharpe)


def test_max_sharpe_enforces_60_40_and_no_zeros():
    tickers, prices, mu, S, equities, bonds = build_inputs()

    n = len(tickers)
    max_w = suggested_max_weight(n, multiple=1.5)  # ~10%
    min_w = 0.005  # 0.5% floor so nothing is zero

    ef, w = solve_max_sharpe_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, rf=0.02)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)

    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    assert abs(eq_w - 0.60) <= 1e-3
    assert abs(bnd_w - 0.40) <= 1e-3

    ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=0.02, verbose=False)
    assert np.isfinite(ret) and np.isfinite(vol) and np.isfinite(sharpe)


# ------------------------
# Runnable script logic
# ------------------------

def run_all():
    tickers, prices, mu, S, equities, bonds = build_inputs()
    n = len(tickers)

    max_w = suggested_max_weight(n, multiple=1.5)  # ~10% for 15
    min_w = 0.005  # 0.5% floor to prevent zeros

    # Feasibility check: n * min_w must be <= 1.0 and also compatible with bucket splits.
    # With 15 and 0.5% => 7.5% total minimum weight, feasible.
    print(f"\nUniverse size: {n}")
    print(f"Equal weight : {1/n:.4f}")
    print(f"Min weight   : {min_w:.4f} (no zeros)")
    print(f"Max weight   : {max_w:.4f} (1.5x equal weight)")

    print("\n=== Min Vol (60/40, no zeros) ===")
    ef, w = solve_min_vol_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)
    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    ret, vol, sharpe = ef.portfolio_performance(verbose=False)
    print("bucket :", {"equity": eq_w, "bond": bnd_w})
    print("perf   :", {"ret": ret, "vol": vol, "sharpe": sharpe})
    print("max_w  :", max(w.values()))
    print("min_w  :", min(w.values()))
    print("weights:", w)

    print("\n=== Max Sharpe (60/40, no zeros) ===")
    ef, w = solve_max_sharpe_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, rf=0.02)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)
    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=0.02, verbose=False)
    print("bucket :", {"equity": eq_w, "bond": bnd_w})
    print("perf   :", {"ret": ret, "vol": vol, "sharpe": sharpe})
    print("max_w  :", max(w.values()))
    print("min_w  :", min(w.values()))
    print("weights:", w)

    print("\n=== Max Utility (60/40, no zeros, risk_aversion=5.0) ===")
    ef, w = solve_max_utility_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, risk_aversion=5.0)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)
    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    ret, vol, sharpe = ef.portfolio_performance(verbose=False)
    print("bucket :", {"equity": eq_w, "bond": bnd_w})
    print("perf   :", {"ret": ret, "vol": vol, "sharpe": sharpe})
    print("max_w  :", max(w.values()))
    print("min_w  :", min(w.values()))
    print("weights:", w)

    print("\n=== Efficient Risk (60/40, no zeros, target_vol=0.12) ===")
    ef, w = solve_efficient_risk_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, target_volatility=0.12)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)
    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    ret, vol, sharpe = ef.portfolio_performance(verbose=False)
    print("bucket :", {"equity": eq_w, "bond": bnd_w})
    print("perf   :", {"ret": ret, "vol": vol, "sharpe": sharpe})
    print("max_w  :", max(w.values()))
    print("min_w  :", min(w.values()))
    print("weights:", w)

    print("\n=== Efficient Return (60/40, no zeros, target_ret=0.15) ===")
    ef, w = solve_efficient_return_60_40_no_zeros(mu, S, tickers, equities, bonds, min_w, max_w, target_return=0.15)
    assert_weights_ok(w, tickers, min_w=min_w, max_w=max_w)
    eq_w, bnd_w = bucket_weights(w, equities, bonds)
    ret, vol, sharpe = ef.portfolio_performance(verbose=False)
    print("bucket :", {"equity": eq_w, "bond": bnd_w})
    print("perf   :", {"ret": ret, "vol": vol, "sharpe": sharpe})
    print("max_w  :", max(w.values()))
    print("min_w  :", min(w.values()))
    print("weights:", w)

    print("\nAll checks passed ✅")


if __name__ == "__main__":
    run_all()
