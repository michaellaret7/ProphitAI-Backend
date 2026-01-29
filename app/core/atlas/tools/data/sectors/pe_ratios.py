"""Sector P/E ratio tools.

This module provides tools for fetching historical Price-to-Earnings ratios
for sectors, enabling valuation analysis and sector comparison.
"""

from app.db.core.pull_fmp_data import FMP_API_DATA
from datetime import datetime, timedelta
import pandas as pd
from app.core.atlas.tools.responses import success_response, error_response
from .mappings import SECTOR_MAPPING, FMP_TO_EQUITY_SECTOR

def get_sector_pe(sectors: list[str] | None = None, years_back: int = 1, frequency: str = 'weekly') -> str:
    """Get the historical weekly P/E ratios of one or more sectors.

    Args:
        sectors: List of sectors to get P/E ratios for. Must use internal format
                (e.g., 'equity_sector_information_technology').
                If None, fetches all available sectors.
        years_back: Number of years back to retrieve data from. Defaults to 1.

    Returns:
        YAML formatted string with weekly sector P/E ratio data in wide format.
        Each week includes: date (Friday - last trading day of week), {sector_name}_pe for each sector.
        Weekly values represent the P/E ratio at the end of the week (last value).
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
        data = fmp.get_historical_sector_pe(fmp_sector, from_date=from_date, to_date=to_date)

        if data:
            df = pd.DataFrame(data)

            # Keep only date and pe columns
            df = df[['date', 'pe']].copy()

            # Rename pe column to include sector name
            df.rename(columns={
                'pe': f'{equity_sector}_pe'
            }, inplace=True)

            # Convert pe to float and round
            df[f'{equity_sector}_pe'] = df[f'{equity_sector}_pe'].astype(float).round(2)

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

        # Get all pe columns
        pe_cols = [col for col in merged_df.columns if col.endswith('_pe')]

        # For P/E ratios: take the last value of the week (Friday's P/E)
        # Reason: P/E ratios are not additive, we want the most recent valuation metric
        resampled_df = pd.DataFrame()

        if pe_cols:
            if frequency == 'weekly':
                resampled_df = merged_df[pe_cols].resample('W-FRI').last()
            else:  # daily
                resampled_df = merged_df[pe_cols]

        # Reset index to get date back as column
        resampled_df = resampled_df.reset_index()

        # Drop rows with all NaN values (weeks with no data)
        resampled_df = resampled_df.dropna(how='all', subset=pe_cols)

        # Round to 2 decimal places
        for col in pe_cols:
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
        return error_response(f"No P/E data found for sectors: {sectors}")


# Tool Schema Constants
GET_SECTOR_PE_DESCRIPTION = (
    "Fetch historical weekly Price-to-Earnings (P/E) ratios for one or more sectors. "
    "Returns time-series data showing valuation metrics for each sector over time. "
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
    "\n  - Column naming: {sector_name}_pe"
    "\n  - date: Friday (last trading day of week)"
    "\n  - Weekly values: P/E ratio at end of week (Friday's most recent value)"
    "\n\n**Use Cases:**"
    "\n  - Valuation comparison: sectors=['equity_sector_technology', 'equity_sector_financials']"
    "\n  - Track sector valuation: sectors=['equity_sector_energy']"
    "\n  - Market-wide valuation: sectors=None (returns all 11, use sparingly)"
    "\n  - Historical valuation trends: years_back=3 for 3-year P/E history"
    "\n  - Identify overvalued/undervalued sectors"
    "\n\n**P/E Ratio Interpretation:**"
    "\n  - Higher P/E: Market expects higher growth, potentially overvalued"
    "\n  - Lower P/E: Market expects lower growth, potentially undervalued"
    "\n  - Compare to historical averages to assess current valuation levels"
    "\n\n**Examples:**"
    "\n  get_sector_pe(sectors=['equity_sector_information_technology'], years_back=1)"
    "\n  get_sector_pe(sectors=['equity_sector_financials', 'equity_sector_energy'], years_back=2)"
    "\n  get_sector_pe(sectors=None, years_back=1)  # All sectors"
)

GET_SECTOR_PE_PARAMETERS = {
    "type": "object",
    "properties": {
        "sectors": {
            "type": "array",
            "description": (
                "List of sector identifiers to fetch P/E ratios for. If omitted, fetches all 11 sectors (use sparingly). "
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
                "Number of years of historical P/E data to fetch. "
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

GET_SECTOR_PE_TOOL = {
    "name": "get_sector_pe",
    "description": GET_SECTOR_PE_DESCRIPTION,
    "parameters": GET_SECTOR_PE_PARAMETERS,
    "function": get_sector_pe,
}
