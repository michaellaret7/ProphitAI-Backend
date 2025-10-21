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
    """Sample covariance and correlation matrices (jittered for stability)."""
    cov = returns.cov()
    # tiny jitter for numerical stability
    cov += np.eye(cov.shape[0]) * 1e-10
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
    """Recursive bisection to allocate risk across ordered assets (long-only template)."""
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

def _solve_with_solvers(prob: cp.Problem, preferred=("ECOS", "SCS", "OSQP")):
    """Try a sequence of solvers for robustness."""
    last_err = None
    for s in preferred:
        try:
            prob.solve(solver=getattr(cp, s), verbose=False)
            if prob.status in ("optimal", "optimal_inaccurate"):
                return True
        except Exception as e:
            last_err = e
    return False

def _project_box_sum(w_target: np.ndarray, lb: np.ndarray, ub: np.ndarray, sum_to: float) -> np.ndarray:
    """
    Project to box with exact sum:
       minimize ||w - w_target||^2
       s.t. sum(w)=sum_to, lb_i <= w_i <= ub_i
    """
    n = len(w_target)
    w = cp.Variable(n)
    obj = cp.Minimize(cp.sum_squares(w - w_target))
    cons = [cp.sum(w) == sum_to, w >= lb, w <= ub]
    prob = cp.Problem(obj, cons)
    ok = _solve_with_solvers(prob, preferred=("OSQP", "ECOS", "SCS"))
    if not ok or w.value is None:
        raise RuntimeError("Projection to box+sum infeasible. Check bounds/sum_to.")
    return np.asarray(w.value).ravel()

def _project_box_net_gross_var(w_target: np.ndarray,
                               cov: pd.DataFrame,
                               lb: np.ndarray,
                               ub: np.ndarray,
                               net_target: float,
                               gross_max: float,
                               vol_cap: float | None):
    """
    Minimize ||w - w_target||^2 s.t.:
      sum(w) = net_target                   (net exposure)
      ||w||_1 <= gross_max                  (gross cap)
      lb_i <= w_i <= ub_i                   (per-name caps by sign)
      and optionally w'Σw <= vol_cap^2      (target vol cap)
    """
    n = len(w_target)
    w = cp.Variable(n)
    cons = [
        cp.sum(w) == net_target,
        cp.norm1(w) <= gross_max,
        w >= lb,
        w <= ub
    ]
    if vol_cap is not None:
        cons.append(cp.quad_form(w, cov.values) <= vol_cap**2)
    obj = cp.Minimize(cp.sum_squares(w - w_target))
    prob = cp.Problem(obj, cons)
    ok = _solve_with_solvers(prob, preferred=("ECOS", "SCS"))  # conic due to L1 and quad_form
    if not ok or w.value is None:
        raise RuntimeError("Conic projection infeasible (net/gross/vol). Relax constraints.")
    return np.asarray(w.value).ravel()

def _apply_group_caps_sided(w0: np.ndarray,
                            groups: list[str],
                            group_max_long: float | None,
                            group_max_short: float | None,
                            lb: np.ndarray,
                            ub: np.ndarray,
                            net_target: float,
                            gross_max: float,
                            cov: pd.DataFrame,
                            vol_cap: float | None):
    """
    Enforce per-sector caps on long and short sides separately:
      sum_{i in g, w_i>0} w_i <= group_max_long
      sum_{i in g, w_i<0} |w_i| <= group_max_short
    We approximate with two linear constraints per group using positive/negative decomposition.
    """
    labels = pd.Series(groups)
    ug = labels.unique().tolist()
    n = len(w0)
    # Positive/negative decomposition: w = w_pos - w_neg, w_pos,w_neg >= 0, disjoint in optimum.
    w_pos = cp.Variable(n)
    w_neg = cp.Variable(n)
    w = w_pos - w_neg

    cons = [
        cp.sum(w) == net_target,
        cp.norm1(w) <= gross_max,
        w_pos >= 0, w_neg >= 0,
        w >= lb, w <= ub,
    ]
    if vol_cap is not None:
        cons.append(cp.quad_form(w, cov.values) <= vol_cap**2)

    for g in ug:
        idx = np.where(labels.values == g)[0]
        if group_max_long is not None:
            cons.append(cp.sum(w_pos[idx]) <= group_max_long)
        if group_max_short is not None:
            cons.append(cp.sum(w_neg[idx]) <= group_max_short)

    obj = cp.Minimize(cp.sum_squares((w_pos - w_neg) - w0))
    prob = cp.Problem(obj, cons)
    ok = _solve_with_solvers(prob, preferred=("ECOS", "SCS"))
    if not ok or w_pos.value is None or w_neg.value is None:
        raise RuntimeError("Projection with sector caps infeasible. Relax caps or check labels.")
    w_sol = np.asarray(w_pos.value).ravel() - np.asarray(w_neg.value).ravel()
    return w_sol

# =======================================
# ------------- Public API --------------
# =======================================

def bounded_hrp(
    returns: pd.DataFrame,
    # --- codependence & clustering ---
    linkage_method: str = "single",
    codependence: str = "pearson",
    # --- long/short directions ---
    directions: list[str] | list[int] | None = None,  # "long"/"short" or +1/-1 (length N). If None => long-only.
    # --- per-name caps (absolute) ---
    long_cap: float = 0.15,             # ≤ 15% on any long name
    short_cap: float = 0.15,            # ≤ 15% absolute on any short name
    long_floor: float = 0.0,            # default 0; raise if you want minimum active long
    short_floor: float = 0.0,           # default 0; raise if you want minimum active short (abs)
    # --- sector caps (per side, optional) ---
    group_labels: list[str] | None = None,
    group_cap_long: float | None = None,   # e.g., 0.35
    group_cap_short: float | None = None,  # e.g., 0.35
    # --- book-level constraints ---
    net_target: float = 0.0,            # e.g., 0.0 for market-neutral; use sum(w)=net_target
    gross_max: float = 1.0,             # 1.0 long-only; 1.5/2.0 for L/S (||w||_1 <= gross_max)
    # --- target volatility (annual) ---
    target_vol_annual: float | None = 0.08,
    trading_days: int = 252,
    use_variance_cap: bool = True,
    # --- misc ---
    diagnostics: bool = True
) -> pd.Series:
    """
    HRP with per-name caps, optional sector caps, and support for user-fixed long/short directions.
    - If `directions` is None: long-only (weights ≥ 0, sum=1, gross=1, net=1).
    - If `directions` provided as +1/-1 or "long"/"short": signs fixed by user; optimizer allocates magnitudes.

    Constraints:
      - Per-name caps/floors by side (long_cap/short_cap, long_floor/short_floor).
      - Net exposure: sum(w) = net_target
      - Gross cap: ||w||_1 <= gross_max
      - Optional variance cap: w'Σw <= σ^2
      - Optional sector caps per side.

    Returns pd.Series of weights indexed by columns of `returns`.
    """

    n_assets = returns.shape[1]
    assert n_assets == len(returns.columns), "Columns must be unique asset names"

    # --- 1) Covariance / Correlation ---
    if codependence == "spearman":
        corr = returns.rank(pct=True).corr(method="pearson")
        cov = returns.cov()
        cov += np.eye(cov.shape[0]) * 1e-10
    else:
        cov, corr = _cov_corr(returns)

    # --- 2) HRP ordering ---
    dist = _distance_from_corr(corr)
    Z = linkage(squareform(dist.values, checks=False), method=linkage_method)
    order_link = {"Z": Z, "n": n_assets}
    order = _quasi_diag(order_link)

    # --- 3) HRP "template" weights (nonnegative, sum to 1) ---
    w_hrp_ordered = _hrp_weights(cov.iloc[order, order], order)
    w_hrp = w_hrp_ordered.reindex(returns.columns)
    w_hrp = (w_hrp / w_hrp.sum()).fillna(0.0).values  # base template

    # --- 4) Build per-asset bounds according to directions ---
    if directions is None:
        # Long-only case: w in [0, long_cap], sum(w)=1, gross=1, net=1
        lb = np.zeros(n_assets) + 0.0
        ub = np.zeros(n_assets) + float(long_cap)
        net = 1.0
        gross = 1.0
        w_target = w_hrp  # target around HRP template
    else:
        # Parse directions
        dir_arr = []
        for d in directions:
            if isinstance(d, (int, float)):
                dir_arr.append(1 if d >= 0 else -1)
            else:
                s = str(d).lower().strip()
                if s in ("long", "l", "1", "+1"):
                    dir_arr.append(1)
                elif s in ("short", "s", "-1"):
                    dir_arr.append(-1)
                else:
                    raise ValueError(f"Unknown direction label: {d}")
        dir_arr = np.array(dir_arr, dtype=int)
        assert len(dir_arr) == n_assets, "directions length must match number of assets"

        # Build box bounds per name by sign
        lb = np.where(dir_arr > 0, long_floor, -short_cap)    # long side ≥ long_floor, short side ≥ -short_cap
        ub = np.where(dir_arr > 0, long_cap, -short_floor)    # long side ≤ long_cap, short side ≤ -short_floor

        # Start from HRP magnitudes but mapped to sides you specified
        # Allocate template mass to long set and short set separately
        long_mask = (dir_arr > 0)
        short_mask = ~long_mask
        eps = 1e-12
        if long_mask.any():
            wL = w_hrp[long_mask]; wL /= max(wL.sum(), eps)
        else:
            wL = np.array([])
        if short_mask.any():
            wS = w_hrp[short_mask]; wS /= max(wS.sum(), eps)
        else:
            wS = np.array([])

        w_target = np.zeros(n_assets)
        if long_mask.any():
            w_target[long_mask] = wL
        if short_mask.any():
            w_target[short_mask] = -wS  # assign negative to shorts

        # Net/gross from args
        net = float(net_target)
        gross = float(gross_max)

    # --- 5) Optional sector caps (per side) will be enforced during the final projection ---
    # --- 6) Target volatility setup ---
    sigma_target_daily = None
    if target_vol_annual is not None:
        sigma_target_daily = float(target_vol_annual) / sqrt(trading_days)

    # --- 7) Projection stage ---
    # Choose projection depending on whether directions were set (L/S) or long-only.
    if directions is None:
        # Long-only: box + sum=1 first
        w_box = _project_box_sum(w_target, lb=np.zeros(n_assets), ub=np.ones(n_assets)*long_cap, sum_to=1.0)

        if use_variance_cap and sigma_target_daily is not None:
            try:
                # For long-only, this becomes: sum=1, w in [0,long_cap], quad_form <= cap
                w_cap = _project_box_net_gross_var(
                    w_target=w_box,
                    cov=cov,
                    lb=np.zeros(n_assets),
                    ub=np.ones(n_assets)*long_cap,
                    net_target=1.0,
                    gross_max=1.0,
                    vol_cap=sigma_target_daily
                )
                w_proj = w_cap
            except RuntimeError:
                # Fallback beta-scaling to hit vol with implicit cash reduction
                pre_vol = _portfolio_vol(w_box, cov)
                if pre_vol > 0 and sigma_target_daily is not None:
                    beta = min(1.0, sigma_target_daily / pre_vol)
                    w_scaled = _project_box_sum(beta * w_box, lb=np.zeros(n_assets), ub=np.ones(n_assets)*long_cap, sum_to=beta)
                    w_proj = w_scaled  # implicit cash = 1 - beta
                else:
                    w_proj = w_box
        else:
            w_proj = w_box

        # Optional sector caps (long side only)
        if group_labels is not None and group_cap_long is not None:
            try:
                w_proj = _apply_group_caps_sided(
                    w0=w_proj,
                    groups=group_labels,
                    group_max_long=group_cap_long,
                    group_max_short=None,
                    lb=np.zeros(n_assets),
                    ub=np.ones(n_assets)*long_cap,
                    net_target=float(w_proj.sum()),     # keep current net (possibly <1 due to cash)
                    gross_max=float(np.abs(w_proj).sum()),
                    cov=cov,
                    vol_cap=sigma_target_daily if use_variance_cap else None
                )
            except RuntimeError:
                pass

    else:
        # Long/Short: conic projection with net, gross, box, and optional variance cap
        if use_variance_cap and sigma_target_daily is not None:
            try:
                w_ls = _project_box_net_gross_var(
                    w_target=w_target,
                    cov=cov,
                    lb=lb,
                    ub=ub,
                    net_target=net,
                    gross_max=gross,
                    vol_cap=sigma_target_daily
                )
            except RuntimeError:
                # Retry without variance cap
                w_ls = _project_box_net_gross_var(
                    w_target=w_target,
                    cov=cov,
                    lb=lb,
                    ub=ub,
                    net_target=net,
                    gross_max=gross,
                    vol_cap=None
                )
        else:
            w_ls = _project_box_net_gross_var(
                w_target=w_target,
                cov=cov,
                lb=lb,
                ub=ub,
                net_target=net,
                gross_max=gross,
                vol_cap=None
            )

        # Optional sector caps on both sides
        w_proj = w_ls
        if group_labels is not None and (group_cap_long is not None or group_cap_short is not None):
            try:
                w_proj = _apply_group_caps_sided(
                    w0=w_proj,
                    groups=group_labels,
                    group_max_long=group_cap_long,
                    group_max_short=group_cap_short,
                    lb=lb,
                    ub=ub,
                    net_target=net,
                    gross_max=gross,
                    cov=cov,
                    vol_cap=sigma_target_daily if use_variance_cap else None
                )
            except RuntimeError:
                # keep w_proj as is if sector-capped problem is infeasible
                pass

    # --- 8) Diagnostics ---
    w_series = pd.Series(w_proj, index=returns.columns, name="weight")
    if diagnostics:
        vol_ann = _portfolio_vol(w_series.values, cov) * sqrt(trading_days)
        print("\n[Diagnostics]")
        print(f"  Net target: {net if directions is not None else 1.0:.3f} | Net actual: {w_series.sum():.3f}")
        print(f"  Gross cap:  {gross if directions is not None else 1.0:.3f} | Gross actual: {np.abs(w_series).sum():.3f}")
        print(f"  Realized annual vol: {vol_ann:.2%}")
        # cap hits
        if directions is None:
            hits = (np.isclose(w_series.values, long_cap, atol=1e-6)).sum()
            print(f"  Names at long cap ({long_cap:.0%}): {hits}")
        else:
            long_mask = w_series.values > 1e-12
            short_mask = w_series.values < -1e-12
            hitsL = (np.isclose(w_series.values, long_cap, atol=1e-6) & long_mask).sum()
            hitsS = (np.isclose(np.abs(w_series.values), short_cap, atol=1e-6) & short_mask).sum()
            print(f"  Names at caps -> long: {hitsL}, short: {hitsS}")

    return w_series

# ==================================================
# -------- Example using ProphitAI data ------------
# ==================================================
if __name__ == "__main__":
    # Consumer Staples Long/Short Portfolio
    portfolio = [
        {"ticker": "MAMA", "position": "long"},      # Mama's Creations [web:4]
        {"ticker": "LWAY", "position": "long"},      # Lifeway Foods [web:4]
        {"ticker": "ODC", "position": "long"},       # Oil-Dri Corp [web:4]
        {"ticker": "SFM", "position": "long"},       # Sprouts Farmers Market [web:4]
        {"ticker": "CASY", "position": "long"},      # Casey's General Stores [web:12][web:4]
        {"ticker": "TPB", "position": "long"},       # Turning Point Brands [web:4]
        {"ticker": "COKE", "position": "long"},      # Coca-Cola Consolidated [web:4]
        {"ticker": "VITL", "position": "long"},      # Vital Farms [web:4]
        {"ticker": "ELF", "position": "long"},       # ELF Beauty [web:4]
        {"ticker": "NGVC", "position": "long"},      # Natural Grocers [web:4]
        {"ticker": "COCO", "position": "long"},      # Vita Coco [web:4]
        {"ticker": "USFD", "position": "long"},      # US Foods [web:4]
        {"ticker": "AKO.A", "position": "long"},     # Embotelladora Andina [web:4]
        {"ticker": "FTLF", "position": "long"},      # FitLife Brands [web:4]
        {"ticker": "KO", "position": "short"},       # Coca-Cola Co [web:29]
        {"ticker": "COST", "position": "short"},     # Costco [web:29]
        {"ticker": "CL", "position": "short"},       # Colgate-Palmolive [web:29]
        {"ticker": "PG", "position": "short"},       # Procter & Gamble [web:3][web:21]
        {"ticker": "KMB", "position": "short"},      # Kimberly-Clark (lagging defensive) [web:21]
        {"ticker": "GIS", "position": "short"},      # General Mills (weak guidance) [web:5]
        {"ticker": "CHD", "position": "short"},      # Church & Dwight (under pressure) [web:6]
        {"ticker": "HSY", "position": "short"},      # Hershey (consumer trade down) [web:21]
        {"ticker": "CLX", "position": "short"},      # Clorox (soft results) [web:24]
        {"ticker": "OLLI", "position": "short"},     # Ollie's Bargain Outlet (underperformance) [web:14]
        {"ticker": "MKC", "position": "short"},      # McCormick & Co. (flat growth) [web:5]
        {"ticker": "TGT", "position": "short"},      # Target (sector pressure) [web:16]
        {"ticker": "STZ", "position": "short"},      # Constellation Brands (sector pressure) [web:11]
        {"ticker": "LW", "position": "short"},       # Lamb Weston (sector pressure) [web:11]
    ]


    tickers = [p["ticker"] for p in portfolio]
    directions = [p["position"] for p in portfolio]

    start_date = '2022-10-09'
    end_date = '2025-10-09'

    # Optional: sector labels if you want 35% per side
    group_labels = ["Unknown"] * len(tickers)
    USE_SECTOR_CAP = False  # set True and fill real labels to enforce caps

    print(f"Fetching price data for {len(tickers)} tickers...")
    price_dict = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date, frequency='daily')

    # Convert to DataFrame
    prices_df = pd.DataFrame(price_dict)

    # Find the latest start date across all tickers (to keep all tickers)
    print("\nData availability:")
    first_valid_dates = {}
    for ticker in prices_df.columns:
        first_valid = prices_df[ticker].first_valid_index()
        if first_valid:
            first_valid_dates[ticker] = first_valid
            print(f"  {ticker}: starts {first_valid.strftime('%Y-%m-%d')}")
        else:
            print(f"  {ticker}: NO DATA - excluding")

    # Use the latest start date to ensure all tickers have data
    if first_valid_dates:
        common_start_date = max(first_valid_dates.values())
        limiting_ticker = [t for t, d in first_valid_dates.items() if d == common_start_date][0]
        print(f"\n⚠️  Common start date: {common_start_date.strftime('%Y-%m-%d')}")
        print(f"⚠️  Limited by ticker: {limiting_ticker}")
        print(f"This ensures all {len(tickers)} tickers have complete data")

        # Show how much data we're losing
        earliest_date = min(first_valid_dates.values())
        print(f"\nEarliest available data: {earliest_date.strftime('%Y-%m-%d')}")
        print(f"Data loss: {(common_start_date - earliest_date).days} days")

        # Filter to common date range
        prices_df = prices_df[prices_df.index >= common_start_date]

        # Forward fill missing values (up to 5 days for weekends/holidays)
        prices_df = prices_df.ffill(limit=5)

        # Calculate returns
        returns = prices_df.pct_change(fill_method=None).dropna(how='all')

        print(f"Final universe: {len(returns.columns)} tickers over {len(returns)} days")
        print(f"Date range: {returns.index[0].strftime('%Y-%m-%d')} to {returns.index[-1].strftime('%Y-%m-%d')}\n")
    else:
        raise ValueError("No valid price data found for any tickers")

    # Match directions and group_labels to final tickers in returns
    final_tickers = returns.columns.tolist()
    ticker_to_position = {p["ticker"]: p["position"] for p in portfolio}
    directions = [ticker_to_position[t] for t in final_tickers]
    group_labels = ["ConsumerStaples"] * len(final_tickers)

    # === Preferences ===
    LONG_CAP = 0.15
    SHORT_CAP = 0.08
    GROUP_CAP_LONG = 0.35 if USE_SECTOR_CAP else None
    GROUP_CAP_SHORT = 0.35 if USE_SECTOR_CAP else None
    TARGET_VOL_ANNUAL = 0.12  # 8%
    TRADING_DAYS = 252
    NET_TARGET = 0.3          # market-neutral
    GROSS_MAX = 2           # e.g., 150% gross (0.75/0.75) — tweak to your book

    print(f"Allocating L/S HRP with per-name caps {int(LONG_CAP*100)}% long / {int(SHORT_CAP*100)}% short,"
          f" sector caps {('ON' if USE_SECTOR_CAP else 'OFF')},"
          f" target vol {TARGET_VOL_ANNUAL:.0%}, net {NET_TARGET:+.2f}, gross ≤ {GROSS_MAX:.2f}")

    w = bounded_hrp(
        returns=returns,
        linkage_method="single",
        codependence="pearson",
        directions=directions,                 # <- fixed signs supplied by user
        long_cap=LONG_CAP,
        short_cap=SHORT_CAP,
        long_floor=0.01,
        short_floor=0.01,
        group_labels=group_labels if USE_SECTOR_CAP else None,
        group_cap_long=GROUP_CAP_LONG,
        group_cap_short=GROUP_CAP_SHORT,
        net_target=NET_TARGET,
        gross_max=GROSS_MAX,
        target_vol_annual=TARGET_VOL_ANNUAL,
        trading_days=TRADING_DAYS,
        use_variance_cap=True,                 # requires ecos/scs
        diagnostics=True
    )

    print("\nOptimized Portfolio Weights (positive=long, negative=short):")
    print("-" * 60)
    w_pct = w * 100  # Convert to percentages
    print(w_pct.sort_values(ascending=False).apply(lambda x: f"{x:+.2f}%"))
    print(f"\nNet: {w.sum():+.2%} | Gross: {np.abs(w).sum():.2%} | Max long: {w.clip(lower=0).max():.2%} | Max short: {np.abs(w.clip(upper=0)).max():.2%}")

    # Portfolio returns (cash assumed 0)
    port_rets = (returns * w).sum(axis=1)

    # SPY for context
    print("\nFetching SPY benchmark data...")
    spy_dict = fetch_bulk_price_data_for_tickers(['SPY'], start_date, end_date, frequency='daily')
    spy_prices = pd.Series(spy_dict['SPY']).dropna()
    spy_rets = spy_prices.pct_change(fill_method=None).dropna()

    common = port_rets.index.intersection(spy_rets.index)
    port_rets = port_rets.loc[common]
    spy_rets = spy_rets.loc[common]

    port_cum = (1 + port_rets).cumprod()
    spy_cum = (1 + spy_rets).cumprod()

    # Metrics (note: L/S vs long-only benchmark is just for visualization)
    port_vol = port_rets.std() * np.sqrt(252) * 100
    spy_vol = spy_rets.std() * np.sqrt(252) * 100
    port_sharpe = (port_rets.mean() * 252) / (port_rets.std() * np.sqrt(252))
    spy_sharpe = (spy_rets.mean() * 252) / (spy_rets.std() * np.sqrt(252))

    # Calculate portfolio beta to SPY
    covariance = np.cov(port_rets, spy_rets)[0, 1]
    spy_variance = np.var(spy_rets)
    portfolio_beta = covariance / spy_variance if spy_variance != 0 else 0.0

    # Plot
    plt.figure(figsize=(12, 7))
    plt.plot(port_cum.index, port_cum.values, label='HRP L/S Portfolio', linewidth=2)
    plt.plot(spy_cum.index, spy_cum.values, label='SPY (context)', linewidth=2, alpha=0.7)
    plt.title('HRP Long/Short Portfolio vs SPY - Cumulative Returns', fontsize=14, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Cumulative Return', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    textstr = (
        f'Net: {NET_TARGET:+.2f} | Gross≤{GROSS_MAX:.2f} | '
        f'Vol Target: {TARGET_VOL_ANNUAL:.0%} | Realized: {port_rets.std()*np.sqrt(252):.2%}\n'
        f'Portfolio Sharpe: {port_sharpe:.2f} | SPY Sharpe: {spy_sharpe:.2f} | Beta: {portfolio_beta:.2f}'
    )
    plt.text(0.02, 0.98, textstr, transform=plt.gca().transAxes, fontsize=10,
             verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    plt.tight_layout()
    plt.show()

    # Print performance summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    port_total_ret = (port_cum.iloc[-1] - 1) * 100
    spy_total_ret = (spy_cum.iloc[-1] - 1) * 100
    print(f"Portfolio Total Return: {port_total_ret:.2f}%")
    print(f"SPY Total Return: {spy_total_ret:.2f}%")
    print(f"Outperformance: {port_total_ret - spy_total_ret:.2f}%")
    print(f"\nPortfolio Volatility: {port_vol:.2f}%")
    print(f"SPY Volatility: {spy_vol:.2f}%")
    print(f"\nPortfolio Sharpe Ratio: {port_sharpe:.2f}")
    print(f"SPY Sharpe Ratio: {spy_sharpe:.2f}")
    print(f"\nPortfolio Beta to SPY: {portfolio_beta:.2f}")
