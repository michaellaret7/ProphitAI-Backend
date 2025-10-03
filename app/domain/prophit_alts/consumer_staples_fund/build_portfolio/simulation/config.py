"""Configuration for CIO agent simulation.

This module defines the simulation parameters, including the historical cutoff date
and data availability status for different data types.
"""

from datetime import datetime
from typing import Set

# Simulation cutoff date - agent will behave as if this is "today"
SIMULATION_CUTOFF_DATE = datetime(2024, 9, 30, 23, 59, 59)

# Data types that have sufficient data BEFORE the September 2024 cutoff
# Based on validation results showing earliest data availability
AVAILABLE_DATA_TYPES: Set[str] = {
    "dividends_series",      # ✓ earliest: 2023-10-19
    "grades_individual",     # ✓ earliest: 2023-10-02
    "price_target_news",     # ✓ earliest: 2023-10-18
    "ratings",               # ✓ earliest: 2023-10-02
}

# Data types that do NOT have data before September 2024 cutoff
# These will return empty results or errors in simulation mode
UNAVAILABLE_DATA_TYPES: Set[str] = {
    "analyst_recommendations",  # ✗ earliest: 2025-07-08
    "earnings_transcripts",     # ✗ removed from simulation
    "latest_transcript",        # ✗ earliest: 2025-02-20
    "press_releases",           # ✗ no data
    "price_target_summary",     # ✗ no data
    "stock_news",               # ✗ earliest: 2025-07-29
}

# Lookback windows for different data types (in days before cutoff)
LOOKBACK_WINDOWS = {
    "news": 180,           # 6 months
    "dividends": 365,      # 1 year
    "transcripts": 730,    # 2 years
    "price_data": 1095,    # 3 years
}


def get_simulation_end_date() -> datetime:
    """Get the simulation cutoff date.

    Returns:
        datetime: The date representing "now" in the simulation
    """
    return SIMULATION_CUTOFF_DATE


def get_simulation_start_date(lookback_days: int) -> datetime:
    """Get the simulation start date based on lookback period.

    Args:
        lookback_days: Number of calendar days to look back from cutoff date
                      (Note: this is calendar days, not trading days)

    Returns:
        datetime: The start date for data fetching
    """
    from datetime import timedelta
    return SIMULATION_CUTOFF_DATE - timedelta(days=lookback_days)


def is_data_type_available(data_type: str) -> bool:
    """Check if a data type has available data before the cutoff.

    Args:
        data_type: The type of data being requested

    Returns:
        bool: True if data is available, False otherwise
    """
    return data_type in AVAILABLE_DATA_TYPES


def get_unavailable_data_message(data_type: str) -> str:
    """Get error message for unavailable data types.

    Args:
        data_type: The type of data that's unavailable

    Returns:
        str: Error message explaining why data is unavailable
    """
    return (
        f"Data type '{data_type}' is not available as of September 30, 2024. "
        f"This data type only has records starting from 2025 onwards."
    )