from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from app.repositories.macro_data import get_economic_indicators
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.time_utils import get_current_utc_time
import tiktoken

def _count_tokens(text: str) -> int:
    """Count the number of tokens in a string using tiktoken."""
    return len(tiktoken.encoding_for_model("gpt-4o").encode(text))

@log_simulation_data_range()
def macro_indicators(
    years_back: int = 5,
    indicators: list[str] | None = None,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Fetch economic indicator data for specified indicators.

    Args:
        years_back: Number of years of historical data to fetch (default: 5)
        indicators: List of indicator names to fetch. If None, fetches all available indicators.
        _simulation_date: INTERNAL USE ONLY - For simulation mode, acts as the end date to get all data up to that point.

    Returns:
        YAML formatted string with indicator data organized by indicator name
    """
    acceptable_fields = ['CPI', 'GDP', 'consumerSentiment', 'durableGoods', 'federalFunds',
                        'industrialProductionTotalIndex', 'inflationRate', 'initialClaims',
                        'nominalPotentialGDP', 'realGDP', 'realGDPPerCapita', 'retailMoneyFunds',
                        'retailSales', 'totalNonfarmPayroll', 'totalVehicleSales', 'unemploymentRate']

    # If no indicators specified, fetch all
    if indicators is None:
        indicators = acceptable_fields

    # Validate each indicator in the list
    invalid_indicators = [ind for ind in indicators if ind not in acceptable_fields]
    if invalid_indicators:
        return error_response(
            f"Invalid indicators: {invalid_indicators}. "
            f"Acceptable fields: {acceptable_fields}"
        )

    # Calculate date range based on years_back
    # Reason: In simulation mode, use _simulation_date as end_date; otherwise use current UTC time
    if _simulation_date is not None:
        end_date = _simulation_date
    else:
        end_date = get_current_utc_time()

    # Calculate start_date from years_back (365.25 days per year to account for leap years)
    start_date = end_date - timedelta(days=int(years_back * 365.25))

    # Fetch data for each indicator and format separately
    # Reason: Each indicator has different release schedules (daily, weekly, monthly) so keep separate
    results = {}

    for indicator in indicators:
        df = get_economic_indicators(
            indicator=indicator,
            start_date=start_date,
            end_date=end_date
        )

        if not df.empty:
            # Keep only date and value columns
            df = df[['date', 'value']].copy()

            # Rename value column to include indicator name
            df.rename(columns={'value': f'{indicator}_value'}, inplace=True)

            # Ensure date is datetime type
            df['date'] = pd.to_datetime(df['date'])

            # Sort by date
            df = df.sort_values('date')

            # Format numerical columns
            # Reason: Round indicator values to 3 decimals for readability
            df[f'{indicator}_value'] = df[f'{indicator}_value'].round(3)

            # Convert date column to ISO format strings
            df['date'] = df['date'].dt.strftime('%Y-%m-%d')

            # Convert to list of dictionaries
            results[indicator] = df.to_dict(orient='records')
    
    if not results:
        return success_response("No data available for the specified indicators and date range.")

    return success_response(results)



# Tool Schema Constants
MACRO_INDICATORS_DESCRIPTION = (
    "Fetch historical economic indicator data for one or more macroeconomic indicators. "
    "Returns a dictionary where keys are indicator names and values are lists of data points (date and value). "
    "\n\n**Available Indicators (16 total):**"
    "\n  • Price Indices: CPI, inflationRate"
    "\n  • Economic Output: GDP, realGDP, nominalPotentialGDP, realGDPPerCapita"
    "\n  • Employment: unemploymentRate, totalNonfarmPayroll, initialClaims"
    "\n  • Consumer: consumerSentiment, retailSales, totalVehicleSales"
    "\n  • Production: industrialProductionTotalIndex, durableGoods"
    "\n  • Monetary: federalFunds, retailMoneyFunds"
    "\n\n**Use Cases:**"
    "\n  • Inflation analysis: indicators=['CPI', 'inflationRate']"
    "\n  • Economic growth: indicators=['GDP', 'realGDP']"
    "\n  • Labor market: indicators=['unemploymentRate', 'totalNonfarmPayroll']"
    "\n  • Consumer health: indicators=['consumerSentiment', 'retailSales']"
    "\n  • All indicators: indicators=None (returns all 16, use sparingly)"
    "\n\n**Date Range:**"
    "\n  • Use years_back to specify how many years of historical data to fetch"
    "\n  • Default is 5 years of data"
    "\n  • In simulation mode, data is fetched from years_back before the simulation date"
    "\n\n**Examples:**"
    "\n  macro_indicators(indicators=['CPI', 'inflationRate'], years_back=3)"
    "\n  macro_indicators(indicators=['GDP', 'unemploymentRate'], years_back=10)"
    "\n  macro_indicators(indicators=['consumerSentiment'])  # Uses default 5 years"
)

MACRO_INDICATORS_PARAMETERS = {
    "type": "object",
    "properties": {
        "indicators": {
            "type": "array",
            "description": (
                "List of indicator names to fetch. If omitted, fetches all 16 indicators (use sparingly). "
                "\n\nValid indicators: CPI, GDP, consumerSentiment, durableGoods, federalFunds, "
                "industrialProductionTotalIndex, inflationRate, initialClaims, nominalPotentialGDP, "
                "realGDP, realGDPPerCapita, retailMoneyFunds, retailSales, totalNonfarmPayroll, "
                "totalVehicleSales, unemploymentRate"
            ),
            "items": {
                "type": "string",
                "enum": [
                    "CPI", "GDP", "consumerSentiment", "durableGoods", "federalFunds",
                    "industrialProductionTotalIndex", "inflationRate", "initialClaims",
                    "nominalPotentialGDP", "realGDP", "realGDPPerCapita", "retailMoneyFunds",
                    "retailSales", "totalNonfarmPayroll", "totalVehicleSales", "unemploymentRate"
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

MACRO_INDICATORS_TOOL = {
    "name": "macro_indicators",
    "description": MACRO_INDICATORS_DESCRIPTION,
    "parameters": MACRO_INDICATORS_PARAMETERS,
    "function": macro_indicators,
}
