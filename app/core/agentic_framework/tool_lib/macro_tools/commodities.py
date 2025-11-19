from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from app.repositories.macro_data import get_commodity_prices
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.time_utils import get_current_utc_time
import tiktoken

def _count_tokens(text: str) -> int:
    """Count the number of tokens in a string using tiktoken."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))

@log_simulation_data_range()
def macro_commodities(
    years_back: int = 5,
    symbols: list[str] | None = None,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Fetch commodity price data for specified symbols.

    Args:
        years_back: Number of years of historical data to fetch (default: 5)
        symbols: List of commodity symbols to fetch. If None, fetches all available commodities.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, acts as the end date to get all data up to that point.

    Returns:
        YAML formatted string with commodity price data (OHLCV) organized by symbol.
        Each commodity includes: symbol, date, open, high, low, close, volume
    """
    # Common commodity symbols (FMP API format)
    acceptable_symbols = [
        'GCUSD',   # Gold
        'SIUSD',   # Silver
        'PLUSD',   # Platinum
        'PAUSD',   # Palladium
        'CLUSD',   # Crude Oil WTI
        'BRUSD',   # Brent Crude Oil
        'NGUSD',   # Natural Gas
        'HGUSD',   # Copper
        'ZSUSD',   # Sugar
        'CCUSD',   # Cocoa
        'CTUSD',   # Cotton
        'KCUSD',   # Coffee
        'WUSD',    # Wheat
        'CUSD',    # Corn
        'SUSD',    # Soybeans
    ]

    # If no symbols specified, fetch all
    if symbols is None:
        symbols = acceptable_symbols

    # Validate each symbol in the list
    invalid_symbols = [symbol for symbol in symbols if symbol not in acceptable_symbols]
    if invalid_symbols:
        return error_response(
            f"Invalid commodity symbols: {invalid_symbols}. "
            f"Acceptable symbols: {acceptable_symbols}"
        )

    # Calculate date range based on years_back
    # Reason: In simulation mode, use _simulation_date as end_date; otherwise use current UTC time
    if _simulation_date is not None:
        end_date = _simulation_date
    else:
        end_date = get_current_utc_time()

    # Calculate start_date from years_back (365.25 days per year to account for leap years)
    start_date = end_date - timedelta(days=int(years_back * 365.25))

    # Fetch data for all symbols and merge into wide format
    # Reason: Wide format reduces token usage by having one row per date with columns for each symbol
    merged_df = None

    for symbol in symbols:
        df = get_commodity_prices(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )

        if not df.empty:
            # Keep only date, close, and volume columns
            df = df[['date', 'close', 'volume']].copy()

            # Rename columns to include symbol prefix
            df.rename(columns={
                'close': f'{symbol}_close',
                'volume': f'{symbol}_volume'
            }, inplace=True)

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

        # For close prices: take last value of the week
        # For volume: sum the weekly volume
        close_cols = [col for col in merged_df.columns if col.endswith('_close')]
        volume_cols = [col for col in merged_df.columns if col.endswith('_volume')]

        resampled_df = pd.DataFrame()
        if close_cols:
            resampled_df = pd.concat([resampled_df, merged_df[close_cols].resample('W').last()], axis=1)
        if volume_cols:
            resampled_df = pd.concat([resampled_df, merged_df[volume_cols].resample('W').sum()], axis=1)

        # Reset index to get date back as column
        resampled_df = resampled_df.reset_index()

        # Drop rows with all NaN values (weeks with no data)
        resampled_df = resampled_df.dropna(how='all', subset=[col for col in resampled_df.columns if col != 'date'])

        # Format numerical columns
        # Reason: Round prices to 3 decimals for readability, convert volumes to integers
        for col in close_cols:
            if col in resampled_df.columns:
                resampled_df[col] = resampled_df[col].round(3)
        for col in volume_cols:
            if col in resampled_df.columns:
                resampled_df[col] = resampled_df[col].fillna(0).astype(int)

        # Convert date column to ISO format strings
        resampled_df['date'] = resampled_df['date'].astype(str)

        # Convert to string format
        results = resampled_df.to_dict(orient='records')
    else:
        results = "No data available for the specified commodities and date range."
    
    return success_response(results)

# Tool Schema Constants
MACRO_COMMODITIES_DESCRIPTION = (
    "Fetch historical commodity price data (OHLCV) for one or more commodities. "
    "Returns time-series data with date, open, high, low, close, and volume for each commodity. "
    "\n\n**Available Commodities (15 total):**"
    "\n  - Precious Metals: GCUSD (Gold), SIUSD (Silver), PLUSD (Platinum), PAUSD (Palladium)"
    "\n  - Energy: CLUSD (Crude Oil WTI), BRUSD (Brent Crude), NGUSD (Natural Gas)"
    "\n  - Industrial Metals: HGUSD (Copper)"
    "\n  - Agriculture - Softs: ZSUSD (Sugar), CCUSD (Cocoa), CTUSD (Cotton), KCUSD (Coffee)"
    "\n  - Agriculture - Grains: WUSD (Wheat), CUSD (Corn), SUSD (Soybeans)"
    "\n\n**Data Fields:**"
    "\n  - symbol: Commodity symbol"
    "\n  - date: Trading date"
    "\n  - open: Opening price"
    "\n  - high: Highest price"
    "\n  - low: Lowest price"
    "\n  - close: Closing price"
    "\n  - volume: Trading volume"
    "\n\n**Use Cases:**"
    "\n  - Gold price tracking: symbols=['GCUSD']"
    "\n  - Energy complex: symbols=['CLUSD', 'BRUSD', 'NGUSD']"
    "\n  - Precious metals basket: symbols=['GCUSD', 'SIUSD', 'PLUSD', 'PAUSD']"
    "\n  - Agricultural commodities: symbols=['WUSD', 'CUSD', 'SUSD']"
    "\n  - All commodities: symbols=None (returns all 15, use sparingly)"
    "\n\n**Date Range:**"
    "\n  - Use years_back to specify how many years of historical data to fetch"
    "\n  - Default is 5 years of data"
    "\n  - In simulation mode, data is fetched from years_back before the simulation date"
    "\n\n**Examples:**"
    "\n  macro_commodities(symbols=['GCUSD'], years_back=3)"
    "\n  macro_commodities(symbols=['CLUSD', 'BRUSD'], years_back=10)"
    "\n  macro_commodities(symbols=['GCUSD', 'SIUSD'])  # Uses default 5 years"
)

MACRO_COMMODITIES_PARAMETERS = {
    "type": "object",
    "properties": {
        "symbols": {
            "type": "array",
            "description": (
                "List of commodity symbols to fetch. If omitted, fetches all 15 commodities (use sparingly). "
                "\n\nValid symbols: GCUSD (Gold), SIUSD (Silver), PLUSD (Platinum), PAUSD (Palladium), "
                "CLUSD (WTI Crude), BRUSD (Brent Crude), NGUSD (Natural Gas), HGUSD (Copper), "
                "ZSUSD (Sugar), CCUSD (Cocoa), CTUSD (Cotton), KCUSD (Coffee), "
                "WUSD (Wheat), CUSD (Corn), SUSD (Soybeans)"
            ),
            "items": {
                "type": "string",
                "enum": [
                    "GCUSD", "SIUSD", "PLUSD", "PAUSD",
                    "CLUSD", "BRUSD", "NGUSD",
                    "HGUSD",
                    "ZSUSD", "CCUSD", "CTUSD", "KCUSD",
                    "WUSD", "CUSD", "SUSD"
                ]
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

MACRO_COMMODITIES_TOOL = {
    "name": "macro_commodities",
    "description": MACRO_COMMODITIES_DESCRIPTION,
    "parameters": MACRO_COMMODITIES_PARAMETERS,
    "function": macro_commodities,
}