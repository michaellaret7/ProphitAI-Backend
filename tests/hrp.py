# bounded_hrp.py
# MIT License
# Requires: numpy, pandas, scipy, cvxpy (>=1.3)
import sys
from pathlib import Path
from math import sqrt, isclose

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from scipy.spatial.distance import squareform
import cvxpy as cp
import matplotlib.pyplot as plt
from app.repositories.price_data import fetch_bulk_price_data_for_tickers

# =========================
# ------- Utilities -------
# =========================

def _cov_corr(returns: pd.DataFrame):
    """Sample covariance and correlation matrices with stability jitter."""
    cov = returns.cov()
    # Add tiny jitter for numerical stability
    cov += np.eye(cov.shape[0]) * 1e-8
    std = np.sqrt(np.diag(cov))
    corr = cov / np.outer(std, std)
    corr.values[range(len(std)), range(len(std))] = 1.0
    return cov, corr

def _distance_from_corr(corr: pd.DataFrame) -> pd.DataFrame:
    """L2 distance used in HRP: d_ij = sqrt(0.5*(1 - rho_ij))."""
    d = np.sqrt(0.5 * (1.0 - corr))
    np.fill_diagonal(d.values, 0.0)
    return d

def _quasi_diag(order_link):
    """
    Return the ordering (seriation) implied by the hierarchical tree.
    Based on recursive unpacking of scipy linkage output.
    """
    n = order_link['n']
    Z = order_link['Z']
    sort_ix = [int(Z[-1, 0]), int(Z[-1, 1])]
    def _recurse(idx):
        if idx < n:
            return [idx]
        else:
            left = int(Z[idx - n, 0])
            right = int(Z[idx - n, 1])
            return _recurse(left) + _recurse(right)
    return _recurse(sort_ix[0]) + _recurse(sort_ix[1])

def _cluster_var(cov: pd.DataFrame, cluster_items: list) -> float:
    """Variance of a cluster assuming inverse-variance weights internally."""
    subcov = cov.iloc[cluster_items, cluster_items].values
    ivp = 1.0 / np.diag(subcov)
    w = ivp / ivp.sum()
    return float(w @ subcov @ w)

def _hrp_weights(cov: pd.DataFrame, sort_ix: list) -> pd.Series:
    """Recursive bisection to allocate risk across ordered assets."""
    w = pd.Series(1.0, index=sort_ix, dtype=float)
    clusters = [sort_ix]
    while len(clusters) > 0:
        new_clusters = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]
            var_left = _cluster_var(cov, left)
            var_right = _cluster_var(cov, right)
            # lower-variance cluster gets more weight
            alpha = 1.0 - var_left / (var_left + var_right)
            w[left] *= alpha
            w[right] *= (1.0 - alpha)
            new_clusters += [left, right]
        clusters = new_clusters
    w.index = cov.index[w.index]   # map to original labels
    w = w.reindex(cov.index)       # reorder to original asset order
    return w

def _portfolio_vol(w: np.ndarray, cov: pd.DataFrame) -> float:
    """Portfolio stdev given weights and covariance."""
    return float(np.sqrt(w @ cov.values @ w))

# ================================
# ---- Convex Projections -------
# ================================

def _project_to_bounds(w_target: np.ndarray, w_min: float, w_max: float, sum_to: float = 1.0) -> np.ndarray:
    """
    Project w_target onto simplex with box constraints:
        minimize ||w - w_target||_2^2
        s.t. sum(w)=sum_to, w_min <= w_i <= w_max
    """
    n = len(w_target)
    w = cp.Variable(n)
    obj = cp.Minimize(cp.sum_squares(w - w_target))
    constraints = [cp.sum(w) == sum_to, w >= w_min, w <= w_max]
    prob = cp.Problem(obj, constraints)
    prob.solve(solver=cp.OSQP, verbose=False)
    if w.value is None:
        raise RuntimeError("Projection failed (infeasible bounds?). Try relaxing w_min/w_max.")
    return np.asarray(w.value).ravel()

def _project_with_var_cap(w_target: np.ndarray,
                          cov: pd.DataFrame,
                          w_min: float,
                          w_max: float,
                          vol_cap: float,
                          sum_to: float = 1.0) -> np.ndarray:
    """
    Minimize ||w - w_target||^2 subject to:
      sum(w) = sum_to, w_min <= w_i <= w_max, and w'Σw <= vol_cap^2

    Uses conic solvers (ECOS/SCS) for quadratic inequality constraint.
    """
    n = len(w_target)
    w = cp.Variable(n)
    obj = cp.Minimize(cp.sum_squares(w - w_target))
    cons = [cp.sum(w) == sum_to, w >= w_min, w <= w_max,
            cp.quad_form(w, cov.values) <= vol_cap**2]
    prob = cp.Problem(obj, cons)

    # Try conic solvers (QCQP requires conic solver, not QP-only OSQP)
    for solver_name in ("ECOS", "SCS"):
        try:
            solver = getattr(cp, solver_name, None)
            if solver is not None:
                prob.solve(solver=solver, verbose=False)
                if w.value is not None:
                    break
        except Exception:
            pass

    if w.value is None:
        raise RuntimeError(
            "Infeasible or no conic solver available. "
            "Install ecos/scs via 'pip install ecos scs' or relax target_vol."
        )
    return np.asarray(w.value).ravel()

def _apply_group_caps(w0: np.ndarray, groups: list[str], group_max: float, w_min: float, w_max: float, sum_to: float = 1.0) -> np.ndarray:
    """
    Project with sector caps:
        sum_{i in g} w_i <= group_max for each group g
    """
    labels = pd.Series(groups)
    unique_groups = labels.unique().tolist()
    n = len(w0)
    w = cp.Variable(n)
    obj = cp.Minimize(cp.sum_squares(w - w0))
    constraints = [cp.sum(w) == sum_to, w >= w_min, w <= w_max]
    for g in unique_groups:
        idx = np.where(labels.values == g)[0]
        constraints.append(cp.sum(w[idx]) <= group_max)
    prob = cp.Problem(obj, constraints)
    prob.solve(solver=cp.OSQP, verbose=False)
    if w.value is None:
        raise RuntimeError("Projection with group caps failed. Relax caps or check group labels.")
    return np.asarray(w.value).ravel()

# =======================================
# ------------- Public API --------------
# =======================================

def bounded_hrp(
    returns: pd.DataFrame,
    w_min: float = 0.0,                  # per-name min (0 for long-only)
    w_max: float = 0.15,                 # per-name max (e.g., 15%)
    linkage_method: str = "single",
    codependence: str = "pearson",
    group_labels: list[str] | None = None,
    group_max: float | None = None,      # e.g., 0.35 means ≤35% per sector
    target_vol_annual: float | None = 0.08,  # 8% annual vol by default (your preference)
    trading_days: int = 252,             # annualization convention
    use_variance_cap: bool = True,       # convex projection to hit vol
    allow_leverage: bool = False,        # your preference: no leverage
    diagnostics: bool = True
) -> pd.Series:
    """
    HRP with per-asset bounds, optional sector caps, and optional target volatility.

    If target_vol_annual is set:
      - If use_variance_cap=True: project to satisfy w'Σw <= σ_target^2 (no leverage, sum=1).
      - If variance-cap is infeasible: fallback to beta scaling toward target and implicit cash.
    """
    assert 0 <= w_min <= w_max <= 1.0, "Bounds must satisfy 0 ≤ w_min ≤ w_max ≤ 1"
    n_assets = returns.shape[1]
    assert n_assets == len(returns.columns), "Columns must be unique asset names"
    if group_labels is not None:
        assert len(group_labels) == n_assets, "group_labels length must match number of assets"

    # 1) Covariance / Correlation
    if codependence == "spearman":
        corr = returns.rank(pct=True).corr(method="pearson")
        cov = returns.cov()
    else:
        cov, corr = _cov_corr(returns)

    # 2) Distance matrix & clustering
    dist = _distance_from_corr(corr)
    Z = linkage(squareform(dist.values, checks=False), method=linkage_method)
    order_link = {"Z": Z, "n": n_assets}
    order = _quasi_diag(order_link)

    # 3) HRP recursive bisection (target vector)
    w_hrp_ordered = _hrp_weights(cov.iloc[order, order], order)
    w_hrp = w_hrp_ordered.reindex(returns.columns)
    w_hrp = (w_hrp / w_hrp.sum()).fillna(0.0).values  # ensure sum=1

    # 4) Per-asset bounds
    w_bounded = _project_to_bounds(w_hrp, w_min=w_min, w_max=w_max, sum_to=1.0)

    # 5) Optional: sector caps (pre-vol targeting)
    if group_labels is not None and group_max is not None:
        w_bounded = _apply_group_caps(w_bounded, group_labels, group_max, w_min, w_max, sum_to=1.0)

    # 6) Target volatility (annual -> daily)
    if target_vol_annual is None:
        if diagnostics:
            pre_vol_ann = _portfolio_vol(w_bounded, cov) * sqrt(trading_days)
            print(f"[Diagnostics] Annualized vol (no target): {pre_vol_ann:.2%}")
        return pd.Series(w_bounded, index=returns.columns, name="weight")

    sigma_target_daily = float(target_vol_annual) / sqrt(trading_days)

    # Try convex variance-cap projection first (preferred)
    try:
        w_cap = _project_with_var_cap(
            w_target=w_bounded,
            cov=cov,
            w_min=w_min,
            w_max=w_max,
            vol_cap=sigma_target_daily,
            sum_to=1.0  # no leverage, keep fully invested in risky sleeve
        )
        post_vol = _portfolio_vol(w_cap, cov)
        if diagnostics:
            pre_vol = _portfolio_vol(w_bounded, cov)
            print(f"[Diagnostics] Vol pre-cap (ann): {pre_vol*sqrt(trading_days):.2%} | Vol post-cap (ann): {post_vol*sqrt(trading_days):.2%}")
        w_final = w_cap
    except RuntimeError:
        # Fallback: beta scale the risky sleeve; implicit cash holds the remainder (no leverage)
        pre_vol = _portfolio_vol(w_bounded, cov)
        if pre_vol <= 1e-10:
            return pd.Series(w_bounded, index=returns.columns, name="weight")
        beta = min(1.0, sigma_target_daily / pre_vol)
        risky_sum = beta
        # scale down inside the box, then re-project to sum=risky_sum
        w_scaled = beta * w_bounded
        w_scaled = _project_to_bounds(w_scaled, w_min=0.0, w_max=w_max, sum_to=risky_sum)
        # (Implicit cash = 1 - risky_sum)
        if diagnostics:
            print(f"[Diagnostics] Variance-cap infeasible. Scaled risky sleeve by β={beta:.3f}; implicit cash={1.0 - risky_sum:.2%}")
            post_vol = _portfolio_vol(w_scaled, cov)
            print(f"[Diagnostics] Vol post-scale (ann): {post_vol*sqrt(trading_days):.2%}")
        w_final = w_scaled

    # Final optional sector caps enforcement (post-vol). Usually not necessary, but kept for safety.
    if group_labels is not None and group_max is not None:
        w_final = _apply_group_caps(w_final, group_labels, group_max, w_min, w_max, sum_to=w_final.sum())

    return pd.Series(w_final, index=returns.columns, name="weight")

# ==================================================
# -------- Example using ProphitAI data ------------
# ==================================================
if __name__ == "__main__":
    # Example with real market data from ProphitAI system
    tickers = ['AEE', 'APP', 'ARM', 'AVGO', 'BSX', 'CEG', 'CMS', 'CRDO', 'DGNX', 'EIS', 'EMQQ', 'EQIX', 'EXOD', 'FITB', 'FR', 'FUFU', 'GREK', 'IGSB', 'IIPR', 'INTR', 'JPM', 'MTSI', 'MU', 'NLR', 'NRG', 'NU', 'NVDA', 'OKLO', 'PLTR', 'SGDM', 'SLVR', 'STAG', 'TRNO', 'VCSH', 'WEC']
    start_date = '2022-10-09'
    end_date = '2025-10-09'

    # Optional: sector labels if you want the 35% cap enforced.
    # Provide a list aligned with `tickers`; here we stub everything to "Unknown".
    # Replace with your real sector mapping to activate the cap.
    group_labels = ["Unknown"] * len(tickers)
    USE_SECTOR_CAP = False  # set True once you pass real labels

    print(f"Fetching price data for {len(tickers)} tickers...")
    price_data = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date, frequency='daily')

    # Convert to DataFrame and handle missing data
    prices_df = pd.DataFrame(price_data)

    # Check data availability for each ticker
    print("\nData availability:")
    for ticker in prices_df.columns:
        first_valid = prices_df[ticker].first_valid_index()
        if first_valid:
            print(f"  {ticker}: starts {first_valid.strftime('%Y-%m-%d')}")
        else:
            print(f"  {ticker}: NO DATA")

    # Drop tickers with insufficient data (less than 60% coverage)
    min_required_points = len(prices_df) * 0.6
    valid_tickers = [col for col in prices_df.columns if prices_df[col].notna().sum() >= min_required_points]
    print(f"\nKeeping {len(valid_tickers)}/{len(tickers)} tickers with sufficient data")

    prices_df = prices_df[valid_tickers]

    # Forward fill missing values (up to 5 days), then drop remaining NaNs
    prices_df = prices_df.ffill(limit=5)

    # Only drop rows where ALL remaining tickers are NaN
    prices_df = prices_df.dropna(how='all')

    # Calculate returns
    returns = prices_df.pct_change(fill_method=None).dropna(how='all')

    # Drop any tickers that still have too many NaN returns
    returns = returns.dropna(axis=1, thresh=len(returns) * 0.95)

    print(f"Final universe: {len(returns.columns)} tickers over {len(returns)} days")

    # === Your preferences ===
    PER_NAME_MAX = 0.18
    PER_SECTOR_MAX = 0.35
    TARGET_VOL_ANNUAL = 0.115   # 8%
    TRADING_DAYS = 252

    print(f"Calculating HRP weights with caps: per-name ≤ {PER_NAME_MAX:.0%}"
          f"{', per-sector ≤ ' + str(int(PER_SECTOR_MAX*100)) + '%' if USE_SECTOR_CAP else ''}"
          f", target vol {TARGET_VOL_ANNUAL:.0%} (annual), no leverage...")

    w = bounded_hrp(
        returns,
        w_min=0.00,
        w_max=PER_NAME_MAX,
        linkage_method="single",
        codependence="pearson",
        group_labels=group_labels if USE_SECTOR_CAP else None,
        group_max=PER_SECTOR_MAX if USE_SECTOR_CAP else None,
        target_vol_annual=TARGET_VOL_ANNUAL,
        trading_days=TRADING_DAYS,
        use_variance_cap=True,   # preferred
        allow_leverage=True,    # no leverage per your preference
        diagnostics=True
    )

    print("\nOptimized Portfolio Weights:")
    print("-" * 40)
    print(w.sort_values(ascending=False))
    print(f"\nSum of weights (risky sleeve): {w.sum():.4f}")
    print(f"Max weight: {w.max():.2%}")
    print(f"Min weight: {w.min():.2%}")

    # If fallback scaling occurred, sum may be < 1.0 (implicit cash).
    risky_sum = float(w.sum())
    implicit_cash = max(0.0, 1.0 - risky_sum)

    # Calculate portfolio returns using risky sleeve (cash return assumed 0)
    portfolio_returns = (returns * w).sum(axis=1)

    # Fetch SPY benchmark data
    print("\nFetching SPY benchmark data...")
    spy_data = fetch_bulk_price_data_for_tickers(['SPY'], start_date, end_date, frequency='daily')
    # spy_data is dict-like: {'SPY': Series}
    spy_prices = pd.Series(spy_data['SPY']).dropna()
    spy_returns = spy_prices.pct_change(fill_method=None).dropna()

    # Align dates
    common_dates = portfolio_returns.index.intersection(spy_returns.index)
    portfolio_returns_aligned = portfolio_returns.loc[common_dates]
    spy_returns_aligned = spy_returns.loc[common_dates]

    # Cumulative returns
    portfolio_cumulative = (1 + portfolio_returns_aligned).cumprod()
    spy_cumulative = (1 + spy_returns_aligned).cumprod()

    # Performance metrics
    portfolio_total_return = (portfolio_cumulative.iloc[-1] - 1) * 100
    spy_total_return = (spy_cumulative.iloc[-1] - 1) * 100
    portfolio_vol = portfolio_returns_aligned.std() * np.sqrt(252) * 100
    spy_vol = spy_returns_aligned.std() * np.sqrt(252) * 100
    portfolio_sharpe = (portfolio_returns_aligned.mean() * 252) / (portfolio_returns_aligned.std() * np.sqrt(252))
    spy_sharpe = (spy_returns_aligned.mean() * 252) / (spy_returns_aligned.std() * np.sqrt(252))

    # Diagnostics around target vol & cash
    print("\n" + "=" * 60)
    print("TARGET & CONSTRAINTS DIAGNOSTICS")
    print("=" * 60)
    print(f"Target Vol (annual): {TARGET_VOL_ANNUAL:.2%}")
    print(f"Realized Vol (annual): {portfolio_returns_aligned.std() * np.sqrt(252):.2%}")
    print(f"Risky Sleeve Sum: {risky_sum:.4f} | Implicit Cash: {implicit_cash:.2%}")
    if USE_SECTOR_CAP:
        # quick sector sums if labels present
        sector_sums = pd.Series(w.values, index=pd.Index(tickers, name="ticker")).groupby(pd.Series(group_labels, index=tickers)).sum()
        breached = sector_sums[sector_sums > PER_SECTOR_MAX]
        if not breached.empty:
            print("WARNING: Sector cap breaches post-optimization:")
            print(breached.sort_values(ascending=False))

    # Plot cumulative returns
    plt.figure(figsize=(12, 7))
    plt.plot(portfolio_cumulative.index, portfolio_cumulative.values, label='HRP Portfolio', linewidth=2)
    plt.plot(spy_cumulative.index, spy_cumulative.values, label='SPY Benchmark', linewidth=2, alpha=0.7)
    plt.title('HRP Portfolio vs SPY - Cumulative Returns', fontsize=14, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Cumulative Return', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    # Add performance metrics as text box
    textstr = (
        f'Portfolio: {portfolio_total_return:.2f}% | Vol: {portfolio_vol:.2f}% | Sharpe: {portfolio_sharpe:.2f}\n'
        f'SPY: {spy_total_return:.2f}% | Vol: {spy_vol:.2f}% | Sharpe: {spy_sharpe:.2f}\n'
        f'Implicit Cash: {implicit_cash:.2%} | Per-name cap: {PER_NAME_MAX:.0%}'
        f'{f" | Per-sector cap: {int(PER_SECTOR_MAX*100)}%" if USE_SECTOR_CAP else ""}'
    )
    plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.show()

    print("\n" + "=" * 60)
    print("PERFORMANCE COMPARISON")
    print("=" * 60)
    print(f"Portfolio Total Return: {portfolio_total_return:.2f}%")
    print(f"SPY Total Return: {spy_total_return:.2f}%")
    print(f"Outperformance: {portfolio_total_return - spy_total_return:.2f}%")
    print(f"\nPortfolio Volatility: {portfolio_vol:.2f}%")
    print(f"SPY Volatility: {spy_vol:.2f}%")
    print(f"\nPortfolio Sharpe Ratio: {portfolio_sharpe:.2f}")
    print(f"SPY Sharpe Ratio: {spy_sharpe:.2f}")

