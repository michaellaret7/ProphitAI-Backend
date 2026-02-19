"""Volatility / low-risk factor calculations (price-based).

All functions are pure — they take return/price series and return float | None.
"""

import numpy as np
import pandas as pd

from app.core.calc_v2.factors.config import (
    VOL_1Y_WINDOW,
    VOL_3M_WINDOW,
    BETA_LOOKBACK,
    TRADING_DAYS,
    MIN_OBSERVATIONS,
)
from app.core.calc_v2.models.factors import VolatilityFactors


# ================================
# --> Individual factor funcs
# ================================

def calc_realized_vol(daily_returns: pd.Series, window: int) -> float | None:
    """Annualized realized volatility: std(r, window) × √252."""
    tail = daily_returns.iloc[-window:] if len(daily_returns) > window else daily_returns
    if len(tail) < MIN_OBSERVATIONS:
        return None
    vol = float(tail.std()) * np.sqrt(TRADING_DAYS)
    return None if np.isnan(vol) else vol


def calc_beta(daily_returns: pd.Series, bench_returns: pd.Series) -> float | None:
    """Market beta: cov(r, m) / var(m) over BETA_LOOKBACK window."""
    n = min(len(daily_returns), len(bench_returns), BETA_LOOKBACK)
    if n < MIN_OBSERVATIONS:
        return None

    r = daily_returns.iloc[-n:]
    m = bench_returns.iloc[-n:]

    # Reason: align on common dates to avoid index mismatch
    aligned = pd.concat([r.rename('r'), m.rename('m')], axis=1).dropna()
    if len(aligned) < MIN_OBSERVATIONS:
        return None

    r_arr = aligned['r'].to_numpy(dtype=float)
    m_arr = aligned['m'].to_numpy(dtype=float)
    cov = float(np.cov(r_arr, m_arr, ddof=1)[0, 1])
    var_m = float(np.var(m_arr, ddof=1))
    if var_m == 0 or np.isnan(var_m):
        return None
    beta = cov / var_m
    return None if np.isnan(beta) else beta


def calc_idiosyncratic_vol(daily_returns: pd.Series, bench_returns: pd.Series) -> float | None:
    """Idiosyncratic volatility: std(residuals) × √252 from OLS r = α + β×m + ε.

    Ang et al. (2006) — stocks with high idiosyncratic vol earn lower returns.
    """
    n = min(len(daily_returns), len(bench_returns), BETA_LOOKBACK)
    if n < MIN_OBSERVATIONS:
        return None

    r = daily_returns.iloc[-n:]
    m = bench_returns.iloc[-n:]
    aligned = pd.concat([r.rename('r'), m.rename('m')], axis=1).dropna()
    if len(aligned) < MIN_OBSERVATIONS:
        return None

    y = aligned['r'].to_numpy(dtype=float)
    x = aligned['m'].to_numpy(dtype=float)

    # Reason: simple OLS via numpy for speed (no statsmodels dependency)
    X = np.column_stack([np.ones(len(x)), x])
    try:
        beta_vec, *_ = np.linalg.lstsq(X, y, rcond=None)
        residuals = y - X @ beta_vec
        ivol = float(np.std(residuals, ddof=1)) * np.sqrt(TRADING_DAYS)
        return None if np.isnan(ivol) else ivol
    except np.linalg.LinAlgError:
        return None


def calc_max_drawdown(prices: pd.Series, window: int) -> float | None:
    """Maximum drawdown over trailing window: max(1 - P / cummax(P))."""
    tail = prices.iloc[-window:] if len(prices) > window else prices
    if len(tail) < MIN_OBSERVATIONS:
        return None
    cummax = tail.cummax()
    drawdowns = 1.0 - tail / cummax
    dd = float(drawdowns.max())
    return None if np.isnan(dd) else dd


# ================================
# --> Orchestrator
# ================================

def calc_volatility_factors(
    prices: pd.Series,
    daily_returns: pd.Series,
    bench_returns: pd.Series | None = None,
) -> VolatilityFactors:
    """Calculate all volatility factor exposures for a single ticker."""
    beta = None
    ivol = None
    if bench_returns is not None:
        beta = calc_beta(daily_returns, bench_returns)
        ivol = calc_idiosyncratic_vol(daily_returns, bench_returns)

    return VolatilityFactors(
        realized_vol_1y=calc_realized_vol(daily_returns, VOL_1Y_WINDOW),
        realized_vol_3m=calc_realized_vol(daily_returns, VOL_3M_WINDOW),
        beta=beta,
        idiosyncratic_vol=ivol,
        max_drawdown_1y=calc_max_drawdown(prices, VOL_1Y_WINDOW),
    )
