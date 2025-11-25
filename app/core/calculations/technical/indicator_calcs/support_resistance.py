"""Support and resistance level indicators."""

from __future__ import annotations

from typing import Optional

import pandas as pd


def calculate_fibonacci_retracements(
    df: pd.DataFrame, lookback: Optional[int] = None, start_idx: Optional[int] = None, end_idx: Optional[int] = None
) -> dict[str, float]:
    """Calculate Fibonacci retracement levels.

    Can calculate in two ways:
    1. Automatic: Uses lookback period to find high/low (default: entire dataset)
    2. Manual: Uses start_idx and end_idx to define the swing

    Returns dict with retracement levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%
    """
    high = df["high"]
    low = df["low"]

    if start_idx is not None and end_idx is not None:
        # Manual swing definition
        swing_high = high.iloc[start_idx:end_idx + 1].max()
        swing_low = low.iloc[start_idx:end_idx + 1].min()
    elif lookback is not None:
        # Use lookback period
        swing_high = high.iloc[-lookback:].max()
        swing_low = low.iloc[-lookback:].min()
    else:
        # Use entire dataset
        swing_high = high.max()
        swing_low = low.min()

    diff = swing_high - swing_low

    # Standard Fibonacci retracement levels
    levels = {
        "level_0.0": swing_high,
        "level_23.6": swing_high - (diff * 0.236),
        "level_38.2": swing_high - (diff * 0.382),
        "level_50.0": swing_high - (diff * 0.500),
        "level_61.8": swing_high - (diff * 0.618),
        "level_78.6": swing_high - (diff * 0.786),
        "level_100.0": swing_low,
    }
    return levels


def calculate_fibonacci_extensions(df: pd.DataFrame, start_idx: int, end_idx: int, retrace_idx: int) -> dict[str, float]:
    """Calculate Fibonacci extension levels.

    Requires three points:
    - start_idx: Start of the initial move (A)
    - end_idx: End of the initial move (B)
    - retrace_idx: End of the retracement (C)

    Returns dict with extension levels: 127.2%, 138.2%, 161.8%, 200%, 261.8%
    """
    high = df["high"]
    low = df["low"]

    # Determine trend direction
    point_a = low.iloc[start_idx] if low.iloc[start_idx] < high.iloc[end_idx] else high.iloc[start_idx]
    point_b = high.iloc[end_idx] if low.iloc[start_idx] < high.iloc[end_idx] else low.iloc[end_idx]
    point_c = low.iloc[retrace_idx] if low.iloc[start_idx] < high.iloc[end_idx] else high.iloc[retrace_idx]

    diff = abs(point_b - point_a)
    is_uptrend = point_b > point_a

    # Extension levels
    if is_uptrend:
        levels = {
            "ext_127.2": point_c + (diff * 1.272),
            "ext_138.2": point_c + (diff * 1.382),
            "ext_161.8": point_c + (diff * 1.618),
            "ext_200.0": point_c + (diff * 2.000),
            "ext_261.8": point_c + (diff * 2.618),
        }
    else:
        levels = {
            "ext_127.2": point_c - (diff * 1.272),
            "ext_138.2": point_c - (diff * 1.382),
            "ext_161.8": point_c - (diff * 1.618),
            "ext_200.0": point_c - (diff * 2.000),
            "ext_261.8": point_c - (diff * 2.618),
        }
    return levels
