"""Sector performance tools.

This module provides tools for fetching historical performance data for sectors,
enabling trend analysis and sector rotation strategies.
"""

from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta
import pandas as pd
from app.core.atlas.tools.responses import success_response, error_response
from .mappings import SECTOR_MAPPING, FMP_TO_EQUITY_SECTOR

def get_sector_performance(sectors: list[str] | None = None, years_back: int = 1, frequency: str = 'weekly') -> str:
    """Get the historical weekly performance of one or more sectors.

    Args:
        sectors: List of sectors to get performance for. Must use internal format
                (e.g., 'equity_sector_information_technology').
                If None, fetches all available sectors.
        years_back: Number of years back to retrieve data from. Defaults to 1.
        frequency: Data frequency - 'weekly' or 'daily'. Defaults to 'weekly'.

    Returns:
        YAML formatted string with weekly sector performance data in wide format.
        Each week includes: date (Friday - last trading day of week), {sector_name}_avg_change for each sector.
        Weekly values represent the cumulative performance for that week (sum of daily changes).
    """
    # If no sectors specified, fetch all
    if sectors is None:
        sectors = list(SECTOR_MAPPING.keys())

    # Type validation: Handle string input (convert to list)
    # Reason: LLM sometimes passes a string instead of a list, which causes Python to iterate over characters
    if isinstance(sectors, str):
        return error_response(
            f"Parameter 'sectors' must be a list, not a string. "
            f"Use sectors=['{sectors}'] instead of sectors='{sectors}'"
        )

    # Validate that sectors is a list
    if not isinstance(sectors, list):
        return error_response(
            f"Parameter 'sectors' must be a list or None. Got: {type(sectors).__name__}"
        )

    # Validate each sector in the list
    for s in sectors:
        if s not in SECTOR_MAPPING:
            return error_response(
                f"Invalid sector: '{s}'. Please use one of the following: {list(SECTOR_MAPPING.keys())}"
            )

    fmp = FMP_API_DATA()

    # Calculate date range
    to_date = datetime.now().strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=years_back * 365)).strftime('%Y-%m-%d')

    # Fetch data for all sectors and merge into wide format
    # Reason: Wide format reduces token usage by having one row per date with columns for each sector
    merged_df = None

    for equity_sector in sectors:
        # Map internal sector name to FMP sector name
        fmp_sector = SECTOR_MAPPING[equity_sector]

        # Fetch data for this sector
        data = fmp.get_historical_sector_performance(fmp_sector, from_date=from_date, to_date=to_date)

        if data:
            df = pd.DataFrame(data)

            # Keep only date and averageChange columns
            df = df[['date', 'averageChange']].copy()

            # Rename averageChange column to include sector name
            df.rename(columns={
                'averageChange': f'{equity_sector}_avg_change'
            }, inplace=True)

            # Convert averageChange to float and round
            df[f'{equity_sector}_avg_change'] = df[f'{equity_sector}_avg_change'].astype(float).round(2)

            # Merge with existing data on date
            if merged_df is None:
                merged_df = df
            else:
                merged_df = pd.merge(merged_df, df, on='date', how='outer')

    # Format the results
    if merged_df is not None and not merged_df.empty:
        # Ensure date is datetime type for resampling
        merged_df['date'] = pd.to_datetime(merged_df['date'])

        # Sort by date
        merged_df = merged_df.sort_values('date')

        # Resample to weekly frequency (Friday as end of week)
        # Reason: Weekly data reduces token usage while maintaining trend information
        # Using 'W-FRI' to end weeks on Friday (last trading day) instead of Sunday
        merged_df = merged_df.set_index('date')

        # Get all avg_change columns
        avg_change_cols = [col for col in merged_df.columns if col.endswith('_avg_change')]

        # For avg_change: sum the daily changes to get total weekly performance
        resampled_df = pd.DataFrame()
        if avg_change_cols:
            if frequency == 'weekly':
                resampled_df = merged_df[avg_change_cols].resample('W-FRI').sum()
            else:  # daily
                resampled_df = merged_df[avg_change_cols]

        # Reset index to get date back as column
        resampled_df = resampled_df.reset_index()

        # Drop rows with all NaN values (weeks with no data)
        resampled_df = resampled_df.dropna(how='all', subset=avg_change_cols)

        # Round to 2 decimal places
        for col in avg_change_cols:
            if col in resampled_df.columns:
                resampled_df[col] = resampled_df[col].round(2)

        # Convert date column to ISO format strings
        resampled_df['date'] = resampled_df['date'].dt.strftime('%Y-%m-%d')

        current_date = datetime.now().strftime('%Y-%m-%d')

        # Remove any future dates (last row if it's beyond current date)
        while not resampled_df.empty and resampled_df.iloc[-1]['date'] > current_date:
            resampled_df.drop(resampled_df.index[-1], inplace=True)

        return success_response(resampled_df.to_dict(orient='records'))
    else:
        return error_response(f"No data found for sectors: {sectors}")


# Tool Schema Constants
GET_SECTOR_PERFORMANCE_DESCRIPTION = (
    "Fetch historical weekly performance data for one or more sectors. "
    "Returns time-series data showing cumulative weekly percentage changes for each sector. "
    "Data is resampled to weekly frequency (Friday as week-end) to reduce token usage while maintaining trend information."
    "\n\n**Available Sectors (11 total):**"
    "\n  - equity_sector_information_technology"
    "\n  - equity_sector_health_care"
    "\n  - equity_sector_financials"
    "\n  - equity_sector_consumer_discretionary"
    "\n  - equity_sector_consumer_staples"
    "\n  - equity_sector_industrials"
    "\n  - equity_sector_communication_services"
    "\n  - equity_sector_energy"
    "\n  - equity_sector_materials"
    "\n  - equity_sector_utilities"
    "\n  - equity_sector_real_estate"
    "\n\n**Data Format:**"
    "\n  - Wide format: one row per week with columns for each sector"
    "\n  - Column naming: {sector_name}_avg_change"
    "\n  - date: Friday (last trading day of week)"
    "\n  - Weekly values: Sum of daily percentage changes for that week"
    "\n\n**Use Cases:**"
    "\n  - Compare sector performance: sectors=['equity_sector_technology', 'equity_sector_financials']"
    "\n  - Track single sector: sectors=['equity_sector_energy']"
    "\n  - All sectors overview: sectors=None (returns all 11, use sparingly)"
    "\n  - Historical analysis: years_back=3 for 3-year performance trends"
    "\n\n**Examples:**"
    "\n  get_sector_performance(sectors=['equity_sector_information_technology'], years_back=1)"
    "\n  get_sector_performance(sectors=['equity_sector_financials', 'equity_sector_energy'], years_back=2)"
    "\n  get_sector_performance(sectors=None, years_back=1)  # All sectors"
)

GET_SECTOR_PERFORMANCE_PARAMETERS = {
    "type": "object",
    "properties": {
        "sectors": {
            "type": "array",
            "description": (
                "List of sector identifiers to fetch. If omitted, fetches all 11 sectors (use sparingly). "
                "Must use internal equity_sector format."
            ),
            "items": {
                "type": "string",
                "enum": [
                    "equity_sector_information_technology",
                    "equity_sector_health_care",
                    "equity_sector_financials",
                    "equity_sector_consumer_discretionary",
                    "equity_sector_consumer_staples",
                    "equity_sector_industrials",
                    "equity_sector_communication_services",
                    "equity_sector_energy",
                    "equity_sector_materials",
                    "equity_sector_utilities",
                    "equity_sector_real_estate"
                ]
            },
            "default": None
        },
        "years_back": {
            "type": "integer",
            "description": (
                "Number of years of historical data to fetch. "
                "Default is 1 year. Data is resampled to weekly frequency."
            ),
            "default": 1,
            "minimum": 1,
            "maximum": 10
        },
        "frequency": {
            "type": "string",
            "description": (
                "Data frequency - 'weekly' or 'daily'. "
                "Default is 'weekly' for reduced token usage."
            ),
            "enum": ["weekly", "daily"],
            "default": "weekly"
        }
    },
    "additionalProperties": False
}

GET_SECTOR_PERFORMANCE_TOOL = {
    "name": "get_sector_performance",
    "description": GET_SECTOR_PERFORMANCE_DESCRIPTION,
    "parameters": GET_SECTOR_PERFORMANCE_PARAMETERS,
    "function": get_sector_performance,
}
