"""
Ichimoku Cloud Alpha Signals

Pure functions for generating trading signals from Ichimoku Cloud indicators.
Based on: Bayesian-optimized Ichimoku strategy (Hulela, 2025)

Entry: Tenkan crosses above Kijun while price is above cloud
Exit: Price drops below cloud
"""

import pandas as pd


# --- Crossover Signals (Generic, Reusable) ---

def bullish_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Detect when fast line crosses above slow line.

    Returns True on the bar where crossover occurs.
    """
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))


def bearish_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Detect when fast line crosses below slow line.

    Returns True on the bar where crossover occurs.
    """
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))


# --- Cloud Position Signals ---

def price_above_cloud(close: pd.Series, senkou_a: pd.Series, senkou_b: pd.Series) -> pd.Series:
    """Price is above the Ichimoku cloud (bullish territory)."""
    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    return close > cloud_top


def price_below_cloud(close: pd.Series, senkou_a: pd.Series, senkou_b: pd.Series) -> pd.Series:
    """Price is below the Ichimoku cloud (bearish territory)."""
    cloud_bottom = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    return close < cloud_bottom


def price_inside_cloud(close: pd.Series, senkou_a: pd.Series, senkou_b: pd.Series) -> pd.Series:
    """Price is inside the cloud (consolidation/indecision)."""
    cloud_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    cloud_bottom = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    return (close <= cloud_top) & (close >= cloud_bottom)

# --- Cloud Trend Signals ---

def cloud_is_bullish(senkou_a: pd.Series, senkou_b: pd.Series) -> pd.Series:
    """Cloud is green (Senkou A > Senkou B) - bullish trend."""
    return senkou_a > senkou_b


def cloud_is_bearish(senkou_a: pd.Series, senkou_b: pd.Series) -> pd.Series:
    """Cloud is red (Senkou A < Senkou B) - bearish trend."""
    return senkou_a < senkou_b
