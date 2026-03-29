"""Shared validation for backtest engines."""

import pandas as pd

REQUIRED_COLUMNS = {"open", "high", "low", "close", "volume"}


def validate_backtest_data(data: pd.DataFrame) -> None:
    """Ensure the DataFrame has all required OHLCV columns and is non-empty.

    Args:
        data: DataFrame to validate.

    Raises:
        ValueError: If columns are missing or data is empty.
    """
    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"Data is missing required columns: {missing}")
    if data.empty:
        raise ValueError("Data DataFrame is empty.")
