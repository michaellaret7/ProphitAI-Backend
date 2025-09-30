"""Utilities for simulation mode support across calculation tools.

This module provides date handling and filtering utilities that allow tools to
operate in either production mode (using current time) or simulation mode
(using a historical cutoff date).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import pandas as pd


def get_end_date(simulation_date: Optional[datetime] = None) -> datetime:
    """Get the effective end date for calculations.

    Args:
        simulation_date: If provided, use this as the cutoff date (simulation mode).
                        If None, use current time (production mode).

    Returns:
        datetime: The end date to use for data fetching
    """
    if simulation_date is not None:
        return simulation_date
    return datetime.now(timezone.utc)


def get_date_range(
    simulation_date: Optional[datetime] = None,
    lookback_days: int = 180
) -> tuple[datetime, datetime]:
    """Get start and end dates for data fetching.

    Args:
        simulation_date: Optional cutoff date for simulation mode
        lookback_days: Number of days to look back from end date

    Returns:
        Tuple of (start_date, end_date)
    """
    end = get_end_date(simulation_date)
    start = end - timedelta(days=lookback_days)
    return start, end


def filter_series_by_date(
    series: pd.Series,
    cutoff_date: Optional[datetime] = None
) -> pd.Series:
    """Filter a time series to only include dates before or on the cutoff date.

    Args:
        series: Time series to filter (with DatetimeIndex)
        cutoff_date: Maximum date to include (if None, returns series unchanged)

    Returns:
        Filtered series (or original if cutoff_date is None)
    """
    if cutoff_date is None or series is None or series.empty:
        return series

    if not isinstance(series.index, pd.DatetimeIndex):
        series.index = pd.to_datetime(series.index)

    return series[series.index <= cutoff_date]


def filter_dataframe_by_date(
    df: pd.DataFrame,
    cutoff_date: Optional[datetime] = None,
    date_column: str = 'date'
) -> pd.DataFrame:
    """Filter a DataFrame to only include rows before or on the cutoff date.

    Args:
        df: DataFrame to filter
        cutoff_date: Maximum date to include (if None, returns df unchanged)
        date_column: Name of the date column to filter on

    Returns:
        Filtered DataFrame (or original if cutoff_date is None)
    """
    if cutoff_date is None or df is None or df.empty:
        return df

    if date_column not in df.columns:
        return df

    df[date_column] = pd.to_datetime(df[date_column])
    return df[df[date_column] <= cutoff_date]