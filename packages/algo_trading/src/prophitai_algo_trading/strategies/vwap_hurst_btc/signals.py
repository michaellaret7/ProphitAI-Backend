"""Pure signal functions for VWAP Hurst BTC strategy.

Reusable boolean conditions based on VWAP z-score, Hurst regime, and
EMA crossovers. All functions are stateless: input Series -> output Series.
"""

import pandas as pd


# ================================
# --> Helper funcs
# ================================

def vwap_oversold(z_score: pd.Series, threshold: float) -> pd.Series:
    """Price is significantly below VWAP (undervalued)."""
    return z_score < -threshold


def vwap_overbought(z_score: pd.Series, threshold: float) -> pd.Series:
    """Price is significantly above VWAP (overvalued)."""
    return z_score > threshold


def vwap_reverted_from_below(z_score: pd.Series, threshold: float) -> pd.Series:
    """Price has reverted back toward VWAP from below."""
    return z_score > -threshold


def vwap_reverted_from_above(z_score: pd.Series, threshold: float) -> pd.Series:
    """Price has reverted back toward VWAP from above."""
    return z_score < threshold


def ema_bullish_cross(ema_fast: pd.Series, ema_slow: pd.Series) -> pd.Series:
    """Fast EMA crossed above slow EMA (bullish momentum)."""
    return (ema_fast > ema_slow) & (ema_fast.shift(1) <= ema_slow.shift(1))


def ema_bearish_cross(ema_fast: pd.Series, ema_slow: pd.Series) -> pd.Series:
    """Fast EMA crossed below slow EMA (bearish momentum)."""
    return (ema_fast < ema_slow) & (ema_fast.shift(1) >= ema_slow.shift(1))


def ema_fast_above_slow(ema_fast: pd.Series, ema_slow: pd.Series) -> pd.Series:
    """Fast EMA is above slow EMA (uptrend)."""
    return ema_fast > ema_slow


def ema_fast_below_slow(ema_fast: pd.Series, ema_slow: pd.Series) -> pd.Series:
    """Fast EMA is below slow EMA (downtrend)."""
    return ema_fast < ema_slow


def regime_mean_reverting(regime: pd.Series) -> pd.Series:
    """Currently in mean-reverting regime (Hurst < 0.45)."""
    return regime == 0


def regime_trending(regime: pd.Series) -> pd.Series:
    """Currently in trending regime (Hurst > 0.55)."""
    return regime == 1


def regime_random_walk(regime: pd.Series) -> pd.Series:
    """Currently in random walk regime (no edge)."""
    return regime == 2
