"""Momentum factor calculations (price-based).

Reuses calc_roc and calc_risk_adj_momentum from technicals/momentum.py.
Only pct_from_52w_high is defined here (no technicals equivalent).
"""

import numpy as np
import pandas as pd

from app.core.calc_v2.factors.config import (
    SKIP_RECENT,
    HIGH_52W_WINDOW,
    MIN_OBSERVATIONS,
)
from app.core.calc_v2.technicals.momentum import calc_roc, calc_risk_adj_momentum
from app.core.calc_v2.models.factors import MomentumFactors


# ================================
# --> Helper funcs
# ================================

def _last_roc(close: pd.Series, window: int, skip_recent: int = SKIP_RECENT) -> float | None:
    """Extract the most recent scalar ROC value from the technicals calc_roc Series.

    Returns None if the Series is empty (insufficient data).
    """
    roc_series = calc_roc(close, window=window, skip_recent=skip_recent)

    if roc_series.empty:
        return None

    val = float(roc_series.iloc[-1])

    return None if np.isnan(val) else val


def _last_risk_adj_momentum(close: pd.Series) -> float | None:
    """Extract the most recent scalar risk-adjusted momentum value."""
    series = calc_risk_adj_momentum(close)

    if series.empty:
        return None

    val = float(series.iloc[-1])

    return None if np.isnan(val) else val


# ================================
# --> Individual factor funcs
# ================================

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

def calc_momentum_factors(prices: pd.Series) -> MomentumFactors:
    """Calculate all momentum factor exposures for a single ticker."""
    return MomentumFactors(
        r12_1=_last_roc(prices, window=252),
        r6_1=_last_roc(prices, window=126),
        r3_1=_last_roc(prices, window=63),
        risk_adj_momentum=_last_risk_adj_momentum(prices),
        pct_from_52w_high=calc_pct_from_52w_high(prices),
    )
