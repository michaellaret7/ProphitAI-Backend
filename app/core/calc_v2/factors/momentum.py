"""Momentum factor calculations (price-based).

All functions are pure — they take price/return series and return float | None.
"""

import numpy as np
import pandas as pd

from app.core.calc_v2.factors.config import (
    SKIP_RECENT,
    R12_1_SPAN,
    R6_1_SPAN,
    R3_1_SPAN,
    HIGH_52W_WINDOW,
    TRADING_DAYS,
    MIN_OBSERVATIONS,
)
from app.core.calc_v2.models.factors import MomentumFactors


# ================================
# --> Helper funcs
# ================================

def _period_return(prices: pd.Series, skip: int, span: int) -> float | None:
    """Compute return over [t-skip-span, t-skip], skipping most recent `skip` days.

    Returns None if insufficient data.
    """
    n = len(prices)
    end_idx = n - 1 - skip
    start_idx = end_idx - span
    if start_idx < 0 or end_idx < 0:
        return None
    try:
        p_end = float(prices.iloc[end_idx])
        p_start = float(prices.iloc[start_idx])
        if p_start <= 0 or np.isnan(p_start) or np.isnan(p_end):
            return None
        return (p_end / p_start) - 1.0
    except (IndexError, ValueError):
        return None


# ================================
# --> Individual factor funcs
# ================================

def calc_r12_1(prices: pd.Series) -> float | None:
    """12-month momentum skipping the most recent month (Jegadeesh & Titman)."""
    return _period_return(prices, SKIP_RECENT, R12_1_SPAN)


def calc_r6_1(prices: pd.Series) -> float | None:
    """6-month momentum skipping the most recent month."""
    return _period_return(prices, SKIP_RECENT, R6_1_SPAN)


def calc_r3_1(prices: pd.Series) -> float | None:
    """3-month momentum skipping the most recent month."""
    return _period_return(prices, SKIP_RECENT, R3_1_SPAN)


def calc_risk_adj_momentum(prices: pd.Series, daily_returns: pd.Series) -> float | None:
    """Risk-adjusted momentum: (r12_1 + r6_1) / (2 × annualized vol).

    AQR-style normalization to penalize high-volatility momentum.
    """
    r12 = calc_r12_1(prices)
    r6 = calc_r6_1(prices)
    if r12 is None or r6 is None:
        return None

    if len(daily_returns) < MIN_OBSERVATIONS:
        return None

    vol = float(daily_returns.std()) * np.sqrt(TRADING_DAYS)
    if vol <= 0 or np.isnan(vol):
        return None

    return (r12 + r6) / (2.0 * vol)


def calc_pct_from_52w_high(prices: pd.Series) -> float | None:
    """Percent below 52-week high: current_price / max(last 252 days) - 1."""
    if len(prices) < MIN_OBSERVATIONS:
        return None
    window = min(len(prices), HIGH_52W_WINDOW)
    recent = prices.iloc[-window:]
    high = float(recent.max())
    current = float(prices.iloc[-1])
    if high <= 0 or np.isnan(high) or np.isnan(current):
        return None
    return (current / high) - 1.0


# ================================
# --> Orchestrator
# ================================

def calc_momentum_factors(prices: pd.Series, daily_returns: pd.Series) -> MomentumFactors:
    """Calculate all momentum factor exposures for a single ticker."""
    return MomentumFactors(
        r12_1=calc_r12_1(prices),
        r6_1=calc_r6_1(prices),
        r3_1=calc_r3_1(prices),
        risk_adj_momentum=calc_risk_adj_momentum(prices, daily_returns),
        pct_from_52w_high=calc_pct_from_52w_high(prices),
    )
