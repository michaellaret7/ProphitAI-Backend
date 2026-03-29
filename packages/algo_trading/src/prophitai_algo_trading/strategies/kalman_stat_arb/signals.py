"""Pure signal functions for Kalman Filter Stat Arb strategy.

Reusable boolean conditions based on z-score levels, slope direction,
and regime state. All functions are stateless: input Series -> output Series.
"""

import pandas as pd


def z_score_below_threshold(z_score: pd.Series, threshold: float) -> pd.Series:
    """Z-score is below negative threshold (price undervalued vs fair value)."""
    return z_score < -threshold


def z_score_above_threshold(z_score: pd.Series, threshold: float) -> pd.Series:
    """Z-score is above positive threshold (price overvalued vs fair value)."""
    return z_score > threshold


def z_score_reverted_above(z_score: pd.Series, threshold: float) -> pd.Series:
    """Z-score has reverted above negative exit threshold."""
    return z_score > -threshold


def z_score_reverted_below(z_score: pd.Series, threshold: float) -> pd.Series:
    """Z-score has reverted below positive exit threshold."""
    return z_score < threshold


def slope_positive(slope: pd.Series) -> pd.Series:
    """Kalman slope is positive (uptrend detected)."""
    return slope > 0


def slope_negative(slope: pd.Series) -> pd.Series:
    """Kalman slope is negative (downtrend detected)."""
    return slope < 0


def slope_accelerating(slope: pd.Series, slope_sma: pd.Series) -> pd.Series:
    """Slope is above its moving average (trend strengthening)."""
    return slope > slope_sma


def slope_decelerating(slope: pd.Series, slope_sma: pd.Series) -> pd.Series:
    """Slope is below its moving average (trend weakening)."""
    return slope < slope_sma


def regime_mean_reverting(regime: pd.Series) -> pd.Series:
    """Currently in mean-reverting regime (low innovation variance)."""
    return regime == 0


def regime_trending(regime: pd.Series) -> pd.Series:
    """Currently in trending regime (high innovation variance)."""
    return regime == 1
