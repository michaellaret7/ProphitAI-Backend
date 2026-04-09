"""Deterministic synthetic OHLCV fixtures for strategy contract testing.

Every fixture is pure math — no randomness, no external data.  Same input
produces the same output every time.  Each fixture generates realistic
OHLCV relationships (high >= open,close; low <= open,close; volume > 0).

Usage::

    from prophitai_algo_trading.testing.fixtures import uptrend, downtrend

    df = uptrend()          # 300-bar monotonic uptrend
    df = flat(bars=500)     # 500-bar sideways market
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


OHLCV_COLS = frozenset({"open", "high", "low", "close", "volume"})
"""Column names present in every fixture DataFrame."""


# ================================
# --> Helper funcs
# ================================


def make_ohlcv(
    closes: list[float],
    spread_pct: float = 0.01,
    base_volume: int = 1_000_000,
) -> pd.DataFrame:
    """Build a deterministic OHLCV DataFrame from a close price series.

    Derives open/high/low from close prices deterministically:
    - Open = previous close (first bar: open == close).
    - High = max(open, close) * (1 + spread_pct / 2).
    - Low  = min(open, close) * (1 - spread_pct / 2).
    - Volume = constant across all bars.

    Args:
        closes: Sequence of close prices.
        spread_pct: Controls the high/low range around max/min of open/close.
        base_volume: Constant volume for every bar.

    Returns:
        DataFrame with columns: open, high, low, close, volume.
        Index is business days starting from 2020-01-02.
    """
    closes_arr = np.array(closes, dtype=float)

    opens = np.roll(closes_arr, 1)
    opens[0] = closes_arr[0]

    bar_max = np.maximum(opens, closes_arr)
    bar_min = np.minimum(opens, closes_arr)

    highs = bar_max * (1.0 + spread_pct / 2.0)
    lows = bar_min * (1.0 - spread_pct / 2.0)

    volume = np.full(len(closes), base_volume, dtype=float)
    index = pd.bdate_range(start="2020-01-02", periods=len(closes))

    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes_arr,
            "volume": volume,
        },
        index=index,
    )


# ================================
# --> Fixture generators
# ================================


def uptrend(
    bars: int = 300,
    start: float = 100.0,
    drift: float = 0.002,
) -> pd.DataFrame:
    """Monotonic uptrend: close[i] = start * (1 + drift)^i.

    Long signals SHOULD fire.  Short signals should NOT.
    """
    closes = [start * (1.0 + drift) ** i for i in range(bars)]

    return make_ohlcv(closes)


def downtrend(
    bars: int = 300,
    start: float = 100.0,
    drift: float = 0.002,
) -> pd.DataFrame:
    """Monotonic downtrend: close[i] = start * (1 - drift)^i.

    Short signals SHOULD fire.  Long signals should NOT.
    """
    closes = [start * (1.0 - drift) ** i for i in range(bars)]

    return make_ohlcv(closes)


def mean_reverting(
    bars: int = 300,
    center: float = 100.0,
    amplitude: float = 10.0,
    period: int = 40,
) -> pd.DataFrame:
    """Sine wave oscillation around a center price.

    Mean-reversion strategies should fire.  Trend-following may whipsaw.
    """
    closes = [
        center + amplitude * math.sin(2.0 * math.pi * i / period)
        for i in range(bars)
    ]

    return make_ohlcv(closes)


def flat(
    bars: int = 300,
    price: float = 100.0,
) -> pd.DataFrame:
    """Constant price — zero directional movement.

    No directional signals should fire.  Tests that strategies
    don't hallucinate signals in noise-free conditions.
    """
    closes = [price] * bars

    return make_ohlcv(closes, spread_pct=0.001)


def volatile_breakout(
    bars: int = 300,
    calm_bars: int = 200,
    calm_drift: float = 0.0003,
    break_drift: float = 0.008,
) -> pd.DataFrame:
    """Low-drift calm phase followed by steep upward breakout.

    Tests that vol-gated and momentum strategies react to regime change.
    The calm phase has minimal drift; the breakout phase accelerates sharply.
    """
    calm = [100.0 * (1.0 + calm_drift) ** i for i in range(calm_bars)]

    last = calm[-1]
    breakout = [
        last * (1.0 + break_drift) ** i
        for i in range(1, bars - calm_bars + 1)
    ]

    return make_ohlcv(calm + breakout)


def gap_up(
    bars: int = 300,
    gap_bar: int = 150,
    gap_pct: float = 0.05,
    drift: float = 0.001,
) -> pd.DataFrame:
    """Uptrend with a single large gap-up at ``gap_bar``.

    Tests stop/exit logic and position management around price gaps.
    """
    closes: list[float] = []
    price = 100.0

    for i in range(bars):
        if i == gap_bar:
            price *= 1.0 + gap_pct

        closes.append(price)
        price *= 1.0 + drift

    return make_ohlcv(closes)


def gap_down(
    bars: int = 300,
    gap_bar: int = 150,
    gap_pct: float = 0.05,
    drift: float = 0.001,
) -> pd.DataFrame:
    """Uptrend with a single large gap-down at ``gap_bar``.

    Tests stop-loss and forced exit behavior when price gaps through stops.
    """
    closes: list[float] = []
    price = 100.0

    for i in range(bars):
        if i == gap_bar:
            price *= 1.0 - gap_pct

        closes.append(price)
        price *= 1.0 + drift

    return make_ohlcv(closes)
