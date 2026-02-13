from datetime import datetime, timedelta
from typing import Optional
from app.repositories.macro.rates import get_government_bond_rates
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.atlas.tools.responses import success_response, error_response
from app.utils.time_utils import get_current_utc_time
import tiktoken
import pandas as pd

def _count_tokens(text: str) -> int:
    """Count the number of tokens in a string using tiktoken."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))

@log_simulation_data_range()
def macro_rates(
    years_back: int = 5,
    countries: list[str] | None = None,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Fetch government bond yield curve data for specified countries.

    Args:
        years_back: Number of years of historical data to fetch (default: 5)
        countries: List of country codes to fetch. If None, fetches all available countries.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, acts as the end date to get all data up to that point.

    Returns:
        YAML formatted string with yield curve data organized by country.
        Each country includes data for multiple maturities: m1, m2, m3, m6, y1, y2, y3, y5, y7, y10, y20, y30
    """
    # Common countries with government bond data
    acceptable_countries = ['USA', 'GB', 'DE', 'FR', 'IT', 'ES', 'JP', 'CA', 'AU', 'NZ', 'CH', 'SE', 'NO', 'DK']

    if 'US' in countries and 'USA' not in countries:
        countries.pop(countries.index('US'))
        countries.insert(0, 'USA')

    # If no countries specified, fetch all
    if countries is None:
        countries = acceptable_countries

    # Validate each country in the list
    invalid_countries = [country for country in countries if country not in acceptable_countries]
    if invalid_countries:
        return error_response(
            f"Invalid country codes: {invalid_countries}. "
            f"Acceptable countries: {acceptable_countries}"
        )

    # Calculate date range based on years_back
    # Reason: In simulation mode, use _simulation_date as end_date; otherwise use current UTC time
    if _simulation_date is not None:
        end_date = _simulation_date
    else:
        end_date = get_current_utc_time()

    # Calculate start_date from years_back (365.25 days per year to account for leap years)
    start_date = end_date - timedelta(days=int(years_back * 365.25))

    # Fetch data for all countries and merge into wide format
    # Reason: Wide format reduces token usage by having one row per date with columns for each country/maturity
    merged_df = None

    for country in countries:
        df = get_government_bond_rates(
            country=country,
            start_date=start_date,
            end_date=end_date
        )

        if not df.empty:
            # Drop country column if it exists
            if 'country' in df.columns:
                df = df.drop(columns=['country'])

            # Get all maturity columns (exclude date)
            maturity_cols = [col for col in df.columns if col != 'date']

            # Rename maturity columns to include country prefix
            rename_dict = {col: f'{country}_{col}' for col in maturity_cols}
            df = df.rename(columns=rename_dict)

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

        # Resample to weekly frequency (Sunday as end of week)
        # Reason: Weekly data reduces token usage while maintaining trend information
        merged_df = merged_df.set_index('date')

        # For rates: take last value of the week (most recent rate)
        resampled_df = merged_df.resample('W').last()

        # Reset index to get date back as column
        resampled_df = resampled_df.reset_index()

        # Drop rows with all NaN values (weeks with no data)
        resampled_df = resampled_df.dropna(how='all', subset=[col for col in resampled_df.columns if col != 'date'])

        # Format numerical columns
        # Reason: Round rates to 3 decimals for readability
        rate_cols = [col for col in resampled_df.columns if col != 'date']
        for col in rate_cols:
            if col in resampled_df.columns:
                resampled_df[col] = resampled_df[col].round(3)

        # Convert date column to ISO format strings
        resampled_df['date'] = resampled_df['date'].astype(str)

        # Convert to string format
        results = resampled_df.to_dict(orient='records')
    else:
        results = "No data available for the specified countries and date range."

    return success_response(results)



# Tool Schema Constants
MACRO_RATES_DESCRIPTION = (
    "Fetch historical government bond yield curve data for one or more countries. "
    "Returns time-series data with date and rates for multiple maturities (m1, m2, m3, m6, y1, y2, y3, y5, y7, y10, y20, y30). "
    "\n\n**Available Countries (14 total):**"
    "\n  • North America: US (United States), CA (Canada)"
    "\n  • Europe: GB (United Kingdom), DE (Germany), FR (France), IT (Italy), ES (Spain), CH (Switzerland), SE (Sweden), NO (Norway), DK (Denmark)"
    "\n  • Asia-Pacific: JP (Japan), AU (Australia), NZ (New Zealand)"
    "\n\n**Yield Curve Maturities:**"
    "\n  • Short-term: m1, m2, m3, m6 (1-month to 6-month rates)"
    "\n  • Medium-term: y1, y2, y3, y5, y7 (1-year to 7-year rates)"
    "\n  • Long-term: y10, y20, y30 (10-year to 30-year rates)"
    "\n\n**Use Cases:**"
    "\n  • US yield curve analysis: countries=['US']"
    "\n  • European rates comparison: countries=['DE', 'FR', 'IT', 'ES']"
    "\n  • Global rate environment: countries=['US', 'GB', 'DE', 'JP']"
    "\n  • All countries: countries=None (returns all 14, use sparingly)"
    "\n\n**Date Range:**"
    "\n  • Use years_back to specify how many years of historical data to fetch"
    "\n  • Default is 5 years of data"
    "\n  • In simulation mode, data is fetched from years_back before the simulation date"
    "\n\n**Examples:**"
    "\n  macro_rates(countries=['USA'], years_back=3)"
    "\n  macro_rates(countries=['USA', 'DE', 'JP'], years_back=10)"
    "\n  macro_rates(countries=['USA'])  # Uses default 5 years"
)

MACRO_RATES_PARAMETERS = {
    "type": "object",
    "properties": {
        "countries": {
            "type": "array",
            "description": (
                "List of country codes to fetch. If omitted, fetches all 14 countries (use sparingly). "
                "\n\nValid countries: US, UK, DE, FR, IT, ES, JP, CA, AU, NZ, CH, SE, NO, DK"
            ),
            "items": {
                "type": "string",
                "enum": ["US", "UK", "DE", "FR", "IT", "ES", "JP", "CA", "AU", "NZ", "CH", "SE", "NO", "DK"]
            },
            "default": None
        },
        "years_back": {
            "type": "integer",
            "description": (
                "Number of years of historical data to fetch. "
                "Default is 5 years. In simulation mode, data is fetched from years_back before the simulation date."
            ),
            "default": 5
        }
    },
    "additionalProperties": False
}

MACRO_RATES_TOOL = {
    "name": "macro_rates",
    "description": MACRO_RATES_DESCRIPTION,
    "parameters": MACRO_RATES_PARAMETERS,
    "function": macro_rates,
}
