"""Macro economic indicators tool.

Fetches historical data for 16 US macroeconomic indicators
covering price indices, GDP, employment, consumer, production, and monetary metrics.
"""

from typing import Annotated, Optional
from datetime import timedelta

import pandas as pd

from app.core.atlas.tools_v2.decorator import agent_tool, Param, Schema
from app.core.atlas.tools_v2.responses import success_response, error_response
from app.repositories.macro.indicators import get_economic_indicators
from app.utils.time_utils import get_current_utc_time


# ================================
# --> Helper funcs
# ================================

INDICATOR_NAMES = [
    "CPI",
    "GDP",
    "consumerSentiment",
    "durableGoods",
    "federalFunds",
    "industrialProductionTotalIndex",
    "inflationRate",
    "initialClaims",
    "nominalPotentialGDP",
    "realGDP",
    "realGDPPerCapita",
    "retailMoneyFunds",
    "retailSales",
    "totalNonfarmPayroll",
    "totalVehicleSales",
    "unemploymentRate",
]


# ================================
# --> Tools
# ================================

@agent_tool(name="macro_indicators")
def macro_indicators(
    indicators: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": (
                "Indicator names to fetch. If omitted, fetches all 16.\n"
                "Valid: CPI, GDP, consumerSentiment, durableGoods, federalFunds, "
                "industrialProductionTotalIndex, inflationRate, initialClaims, "
                "nominalPotentialGDP, realGDP, realGDPPerCapita, retailMoneyFunds, "
                "retailSales, totalNonfarmPayroll, totalVehicleSales, unemploymentRate"
            ),
            "items": {"type": "string", "enum": INDICATOR_NAMES},
            "default": None,
        }),
    ] = None,
    years_back: Annotated[int, Param(min_val=1, max_val=10)] = 5,
) -> str:
    """Fetch historical US macroeconomic indicator data.

Returns a dictionary keyed by indicator name, each containing a list of
{date, value} data points sorted chronologically.

**Available Indicators (16 total):**
- Price Indices: CPI, inflationRate
- Economic Output: GDP, realGDP, nominalPotentialGDP, realGDPPerCapita
- Employment: unemploymentRate, totalNonfarmPayroll, initialClaims
- Consumer: consumerSentiment, retailSales, totalVehicleSales
- Production: industrialProductionTotalIndex, durableGoods
- Monetary: federalFunds, retailMoneyFunds

**Use Cases:**
- Inflation analysis: indicators=['CPI', 'inflationRate']
- Economic growth: indicators=['GDP', 'realGDP']
- Labor market: indicators=['unemploymentRate', 'totalNonfarmPayroll']
- Consumer health: indicators=['consumerSentiment', 'retailSales']
- All indicators: indicators=None (returns all 16, use sparingly)

    Args:
        indicators: Indicator names to fetch (default: all 16)
        years_back: Years of historical data (default: 5)

    Examples:
        macro_indicators(indicators=['CPI', 'inflationRate'], years_back=3)
        macro_indicators(indicators=['GDP', 'unemploymentRate'], years_back=10)
    """
    try:
        target_indicators = indicators if indicators is not None else INDICATOR_NAMES

        # Reason: validate indicator names against known list
        invalid = [i for i in target_indicators if i not in INDICATOR_NAMES]
        if invalid:
            return error_response(f"Invalid indicators: {invalid}. Valid: {INDICATOR_NAMES}")

        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=int(years_back * 365.25))

        results: dict[str, list[dict]] = {}

        for indicator in target_indicators:
            df = get_economic_indicators(
                indicator=indicator,
                start_date=start_date,
                end_date=end_date,
            )
            if df.empty:
                continue

            df = df[["date", "value"]].copy()
            df.rename(columns={"value": f"{indicator}_value"}, inplace=True)
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date")
            df[f"{indicator}_value"] = df[f"{indicator}_value"].round(3)
            df["date"] = df["date"].dt.strftime("%Y-%m-%d")

            results[indicator] = df.to_dict(orient="records")

        if not results:
            return success_response("No data available for the specified indicators and date range.")

        return success_response(results)

    except Exception as e:
        return error_response(f"Failed to fetch macro indicators: {e}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(macro_indicators(indicators=["CPI", "federalFunds"], years_back=1))
