"""Signed consecutive-direction streak counter.

For each bar, count how many consecutive same-direction bars precede it
(including itself), signed by the direction. Up-streaks are positive,
down-streaks are negative, flat bars reset to zero. Used by ConnorsRSI
(streak as an oscillator input) and by the consecutive-bar-fade alpha
(streak as an exhaustion signal).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def streak_series(close_series: pd.Series) -> pd.Series:
    """Signed consecutive-direction streak count for one ticker.

    Vectorized via direction-change cumulative-sum grouping: each
    contiguous-sign run gets a unique group id, then the within-group
    cumulative count gives the streak length.

    Args:
        close_series: Bar close prices for a single ticker.

    Returns:
        Series of signed streak counts aligned to ``close_series.index``.
    """
    diffs = close_series.diff()
    sign = np.sign(diffs).fillna(0.0)

    sign_change = sign != sign.shift(1)
    group_id = sign_change.cumsum()

    streak_count = sign.groupby(group_id).cumcount() + 1

    return streak_count * sign
