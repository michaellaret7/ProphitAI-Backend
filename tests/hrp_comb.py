# bounded_hrp_combined.py
# MIT License
# Unified HRP implementation supporting both long-only and long/short portfolios
# Requires: numpy, pandas, scipy, cvxpy (>=1.3)
# For variance-cap and L1 (gross) constraints, install a conic solver:
#   pip install ecos scs

import sys
from pathlib import Path
from math import sqrt

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
    # --- LONG-ONLY SIMPLE PARAMS (convenience) ---
    w_min: float | None = None,             # Simple bounds for long-only mode
    w_max: float | None = None,             # Simple bounds for long-only mode
    allow_leverage: bool = False,           # For long-only: if False, sum=1; if True, sum can vary
    # --- LONG/SHORT GRANULAR PARAMS ---
    directions: list[str] | list[int] | None = None,  # "long"/"short" or +1/-1 (length N). If None => long-only.
    long_cap: float | None = None,          # ≤ cap on any long name (e.g., 0.15)
    short_cap: float | None = None,         # ≤ cap on any short name (abs value, e.g., 0.15)
    long_floor: float | None = None,        # minimum active long (default 0)
    short_floor: float | None = None,       # minimum active short (abs, default 0)
    # --- sector caps (per side, optional) ---
    group_labels: list[str] | None = None,
    group_cap_long: float | None = None,    # e.g., 0.35
    group_cap_short: float | None = None,   # e.g., 0.35
    # --- book-level constraints ---
    net_target: float | None = None,        # e.g., 0.0 for market-neutral; use sum(w)=net_target
    gross_max: float | None = None,         # 1.0 long-only; 1.5/2.0 for L/S (||w||_1 <= gross_max)
    # --- target volatility (annual) ---
    target_vol_annual: float | None = 0.08,
    trading_days: int = 252,
    use_variance_cap: bool = True,
    # --- misc ---
    diagnostics: bool = True
) -> pd.Series:
    """
    Unified HRP with per-name caps, optional sector caps, supporting both long-only and long/short portfolios.

    USAGE MODES:

    1. LONG-ONLY (simple):
       bounded_hrp(returns, w_min=0.0, w_max=0.15, target_vol_annual=0.08)

       This automatically sets:
         - directions = None (all long)
         - net_target = 1.0 (fully invested)
         - gross_max = 1.0 (no leverage, or higher if allow_leverage=True)
         - long_cap/short_cap derived from w_min/w_max

    2. LONG/SHORT (granular):
       bounded_hrp(returns,
                   directions=["long", "short", ...],
                   long_cap=0.15, short_cap=0.15,
                   long_floor=0.0, short_floor=0.0,
                   net_target=0.0, gross_max=2.0,
                   target_vol_annual=0.12)

       Explicit control over each side with separate caps/floors.

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

    # --- PARAMETER RESOLUTION: Detect mode and set defaults ---

    # Long-only mode detection
    is_long_only = directions is None

    if is_long_only:
        # LONG-ONLY MODE: Map simple params to granular ones
        if w_min is None:
            w_min = 0.0
        if w_max is None:
            w_max = 0.15

        # Set granular params for long-only
        long_cap = w_max
        short_cap = 0.0  # no shorts
        long_floor = w_min
        short_floor = 0.0
        net_target = 1.0  # fully invested
        gross_max = 1.0 if not allow_leverage else 1.5  # no leverage unless explicitly allowed

    else:
        # LONG/SHORT MODE: Use granular params with defaults
        if long_cap is None:
            long_cap = 0.15
        if short_cap is None:
            short_cap = 0.15
        if long_floor is None:
            long_floor = 0.0
        if short_floor is None:
            short_floor = 0.0
        if net_target is None:
            net_target = 0.0  # market-neutral default
        if gross_max is None:
            gross_max = 2.0  # typical L/S gross

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
    if is_long_only:
        # Long-only case: w in [long_floor, long_cap], sum(w)=net_target, gross=net_target
        lb = np.zeros(n_assets) + float(long_floor)
        ub = np.zeros(n_assets) + float(long_cap)
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

    # --- 5) Target volatility setup ---
    sigma_target_daily = None
    if target_vol_annual is not None:
        sigma_target_daily = float(target_vol_annual) / sqrt(trading_days)

    # --- 6) Projection stage ---
    # Choose projection depending on whether directions were set (L/S) or long-only.
    if is_long_only:
        # Long-only: box + sum=net_target first
        w_box = _project_box_sum(w_target, lb=lb, ub=ub, sum_to=float(net_target))

        if use_variance_cap and sigma_target_daily is not None:
            try:
                # For long-only with variance cap
                w_cap = _project_box_net_gross_var(
                    w_target=w_box,
                    cov=cov,
                    lb=lb,
                    ub=ub,
                    net_target=float(net_target),
                    gross_max=float(gross_max),
                    vol_cap=sigma_target_daily
                )
                w_proj = w_cap
            except RuntimeError:
                # Fallback beta-scaling to hit vol with implicit cash reduction
                pre_vol = _portfolio_vol(w_box, cov)
                if pre_vol > 0 and sigma_target_daily is not None:
                    beta = min(1.0, sigma_target_daily / pre_vol)
                    w_scaled = _project_box_sum(beta * w_box, lb=lb, ub=ub, sum_to=beta)
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
                    lb=lb,
                    ub=ub,
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
                    net_target=float(net_target),
                    gross_max=float(gross_max),
                    vol_cap=sigma_target_daily
                )
            except RuntimeError:
                # Retry without variance cap
                w_ls = _project_box_net_gross_var(
                    w_target=w_target,
                    cov=cov,
                    lb=lb,
                    ub=ub,
                    net_target=float(net_target),
                    gross_max=float(gross_max),
                    vol_cap=None
                )
        else:
            w_ls = _project_box_net_gross_var(
                w_target=w_target,
                cov=cov,
                lb=lb,
                ub=ub,
                net_target=float(net_target),
                gross_max=float(gross_max),
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
                    net_target=float(net_target),
                    gross_max=float(gross_max),
                    cov=cov,
                    vol_cap=sigma_target_daily if use_variance_cap else None
                )
            except RuntimeError:
                # keep w_proj as is if sector-capped problem is infeasible
                pass

    # --- 7) Diagnostics ---
    w_series = pd.Series(w_proj, index=returns.columns, name="weight")
    if diagnostics:
        vol_ann = _portfolio_vol(w_series.values, cov) * sqrt(trading_days)
        mode_str = "LONG-ONLY" if is_long_only else "LONG/SHORT"
        print(f"\n[Diagnostics - {mode_str}]")
        print(f"  Net target: {net_target:.3f} | Net actual: {w_series.sum():.3f}")
        print(f"  Gross cap:  {gross_max:.3f} | Gross actual: {np.abs(w_series).sum():.3f}")
        print(f"  Realized annual vol: {vol_ann:.2%}")
        # cap hits
        if is_long_only:
            hits = (np.isclose(w_series.values, long_cap, atol=1e-6)).sum()
            print(f"  Names at cap ({long_cap:.0%}): {hits}")
        else:
            long_mask = w_series.values > 1e-12
            short_mask = w_series.values < -1e-12
            hitsL = (np.isclose(w_series.values, long_cap, atol=1e-6) & long_mask).sum()
            hitsS = (np.isclose(np.abs(w_series.values), short_cap, atol=1e-6) & short_mask).sum()
            print(f"  Names at caps -> long: {hitsL}, short: {hitsS}")

    return w_series

# ==================================================
# -------- Usage Examples --------------------------
# ==================================================
if __name__ == "__main__":
    """
    EXAMPLE 1: LONG-ONLY PORTFOLIO
    Simple interface using w_min/w_max parameters
    """
    # Setup
    from app.db.core.db_config import MarketSession, UserSession
    from app.db.core.models.user_data_models import Portfolio
    from app.utils.serialize_output import serialize_sqlalchemy_obj

    tickers = ["IGSB", "ARCC", "IVZ", "AVGO", "NVDA", "BSX", "VWO", "KLAC", "COST", "WMT", "GLD", "IAU"]

    directions_dict = {"IGSB": 0.1, "ARCC": 0.1, "IVZ": 0.1, "AVGO": 0.1, "NVDA": 0.1, "BSX": 0.1, "VWO": 0.1, "KLAC": 0.1, "COST": 0.1, "WMT": 0.1, "GLD": 0.1, "IAU": 0.1}
    
    start_date = '2022-10-09'
    end_date = '2025-10-09'

    # Fetch data
    price_data = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date, frequency='daily')
    prices_df = pd.DataFrame(price_data)

    # Check for sufficient data (60% coverage)
    min_required_points = len(prices_df) * 0.6
    insufficient_data_tickers = []
    sufficient_data_tickers = []

    for col in prices_df.columns:
        if prices_df[col].notna().sum() < min_required_points:
            insufficient_data_tickers.append(col)
        else:
            sufficient_data_tickers.append(col)

    # Process tickers with sufficient data through HRP
    if sufficient_data_tickers:
        prices_sufficient = prices_df[sufficient_data_tickers].copy()
        prices_sufficient = prices_sufficient.ffill(limit=5).dropna(how='all')
        returns = prices_sufficient.pct_change(fill_method=None).dropna(how='all')
        returns = returns.dropna(axis=1, thresh=len(returns) * 0.95)

        # Run HRP - Long-only
        weights_long = bounded_hrp(
            returns,
            w_min=0.0,
            w_max=0.20,
            target_vol_annual=0.15,
            diagnostics=False
        )
    else:
        weights_long = pd.Series(dtype=float)

    # Add 3% weight for tickers with insufficient data
    for ticker in insufficient_data_tickers:
        weights_long[ticker] = 0.03

    sum_weights_long = weights_long.sum()
    print(f"Sum of weights: {sum_weights_long}")
    print(f"Insufficient data tickers (defaulted to 3%): {insufficient_data_tickers}")

    print("Long-only portfolio:")
    print(weights_long)

    # Calculate portfolio returns
    portfolio_returns_long = (returns * weights_long).sum(axis=1)
    cumulative_returns_long = (1 + portfolio_returns_long).cumprod()

    # Calculate original portfolio returns from directions_dict allocations
    # Align to filtered returns columns and normalize weights
    original_weights = pd.Series(directions_dict, dtype=float)
    original_weights = original_weights.reindex(returns.columns).dropna()
    if (original_weights < 0).any():
        denom = original_weights.abs().sum()
    else:
        denom = original_weights.sum()
    if denom != 0:
        original_weights = original_weights / denom
    original_portfolio_returns = (returns * original_weights).sum(axis=1)
    cumulative_returns_original = (1 + original_portfolio_returns).cumprod()


    """
    EXAMPLE 2: LONG/SHORT PORTFOLIO
    Granular interface with explicit directions and constraints
    """
    # Setup
    from app.db.core.db_config import MarketSession, ProphitAltsSession
    from app.db.core.models.prophit_alts_models import *
    from app.utils.serialize_output import serialize_sqlalchemy_obj

    ProphitAltsSession = ProphitAltsSession()
    portfolio = ProphitAltsSession.query(FundFinalPosition).filter(FundFinalPosition.fund_name == "consumer_staples_fund").all()
    portfolio = [serialize_sqlalchemy_obj(p) for p in portfolio]
    ProphitAltsSession.close()


    tickers = [p["ticker_name"] for p in portfolio]
    directions_dict = {p["ticker_name"]: p["position"].value for p in portfolio}

    # Fetch data
    price_data = fetch_bulk_price_data_for_tickers(tickers, start_date, end_date, frequency='daily')
    prices_df = pd.DataFrame(price_data)

    # Check for sufficient data (60% coverage)
    min_required_points = len(prices_df) * 0.6
    insufficient_data_tickers = []
    sufficient_data_tickers = []

    for col in prices_df.columns:
        if prices_df[col].notna().sum() < min_required_points:
            insufficient_data_tickers.append(col)
        else:
            sufficient_data_tickers.append(col)

    # Process tickers with sufficient data through HRP
    if sufficient_data_tickers:
        prices_sufficient = prices_df[sufficient_data_tickers].copy()
        prices_sufficient = prices_sufficient.ffill(limit=5).dropna(how='all')
        returns_ls = prices_sufficient.pct_change(fill_method=None).dropna(how='all')
        returns_ls = returns_ls.dropna(axis=1, thresh=len(returns_ls) * 0.95)

        # Match directions to final tickers after filtering
        final_tickers = returns_ls.columns.tolist()
        directions = [directions_dict[ticker] for ticker in final_tickers]

        # Run HRP - Long/Short
        weights_ls = bounded_hrp(
            returns_ls,
            directions=directions,
            long_cap=0.15,
            short_cap=0.8,
            net_target=0.3,
            gross_max=2.0,
            target_vol_annual=0.15,
            diagnostics=False
        )
    else:
        weights_ls = pd.Series(dtype=float)

    # Add 3% weight for tickers with insufficient data (respecting long/short direction)
    for ticker in insufficient_data_tickers:
        direction = directions_dict[ticker]
        if direction in ('long', 'l', '1', 1):
            weights_ls[ticker] = 0.03
        else:  # short
            weights_ls[ticker] = -0.03

    print(f"\nInsufficient data tickers (defaulted to ±3%): {insufficient_data_tickers}")
    print("\nLong/short portfolio:")
    print(weights_ls)

    # Calculate portfolio returns
    portfolio_returns_ls = (returns_ls * weights_ls).sum(axis=1)
    cumulative_returns_ls = (1 + portfolio_returns_ls).cumprod()

    # Plot both
    plt.figure(figsize=(12, 6))
    plt.plot(cumulative_returns_long.index, cumulative_returns_long.values, label='Long-only HRP', linewidth=2)
    plt.plot(cumulative_returns_ls.index, cumulative_returns_ls.values, label='Long/Short HRP', linewidth=2)
    if 'cumulative_returns_original' in locals() and cumulative_returns_original is not None:
        plt.plot(cumulative_returns_original.index, cumulative_returns_original.values, label='Original Portfolio', linewidth=2, linestyle='--')
    plt.title('HRP Portfolio Comparison - Cumulative Returns')
    plt.xlabel('Date')
    plt.ylabel('Cumulative Return')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()
