"""Moving average indicators."""

from __future__ import annotations

import pandas as pd

from .helpers import sma, ema, wilder_ma


def calculate_moving_averages(
    df: pd.DataFrame, lookbacks: list[int], ma_type: str = "sma", price_col: str = "close"
) -> pd.DataFrame:
    """Compute moving averages for arbitrary lookbacks.

    - ma_type: "sma" | "ema" | "wilder"
    - price_col: column to average (default "close")
    Returns a DataFrame with one column per lookback, named like "sma_20".
    """
    if price_col not in df.columns:
        raise ValueError(f"price_col '{price_col}' not found in DataFrame columns")
    if not lookbacks:
        raise ValueError("lookbacks must be a non-empty list of positive integers")

    series = df[price_col]
    outputs: dict[str, pd.Series] = {}

    for lb in lookbacks:
        if not isinstance(lb, int) or lb <= 0:
            raise ValueError("lookbacks must contain positive integers")
        if ma_type == "sma":
            ma = sma(series, lb)
        elif ma_type == "ema":
            ma = ema(series, lb)
        elif ma_type == "wilder":
            ma = wilder_ma(series, lb)
        else:
            raise ValueError("ma_type must be one of: 'sma', 'ema', 'wilder'")
        outputs[f"{ma_type}_{lb}"] = ma

    return pd.DataFrame(outputs)
