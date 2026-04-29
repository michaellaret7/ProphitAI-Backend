"""Macro economic indicators tool.

Fetches historical data for 16 US macroeconomic indicators
covering price indices, GDP, employment, consumer, production, and monetary metrics.
"""

from typing import Annotated, Optional
from datetime import timedelta

import pandas as pd

from prophitai_atlas.tools.decorator import agent_tool, Param, Schema
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.repositories.macro import get_economic_indicators
from prophitai_shared.time_utils import get_current_utc_time


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

CATEGORY_INDICATORS: dict[str, list[str]] = {
    "price_indices": ["CPI", "inflationRate"],
    "economic_output": ["GDP", "realGDP", "nominalPotentialGDP", "realGDPPerCapita"],
    "employment": ["unemploymentRate", "totalNonfarmPayroll", "initialClaims"],
    "consumer": ["consumerSentiment", "retailSales", "totalVehicleSales"],
    "production": ["industrialProductionTotalIndex", "durableGoods"],
    "monetary": ["federalFunds", "retailMoneyFunds"],
}

CATEGORY_NAMES = list(CATEGORY_INDICATORS.keys())


# ================================
# --> Tools
# ================================

@agent_tool(name="macro_indicators", category="market")
def macro_indicators(
    indicators: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": (
                "Specific indicator names to fetch. Combined (union) with `categories` "
                "if both are set. If both are omitted, fetches all 16.\n"
                "Valid: CPI, GDP, consumerSentiment, durableGoods, federalFunds, "
                "industrialProductionTotalIndex, inflationRate, initialClaims, "
                "nominalPotentialGDP, realGDP, realGDPPerCapita, retailMoneyFunds, "
                "retailSales, totalNonfarmPayroll, totalVehicleSales, unemploymentRate"
            ),
            "items": {"type": "string", "enum": INDICATOR_NAMES},
            "default": None,
        }),
    ] = None,
    categories: Annotated[
        Optional[list[str]],
        Schema({
            "type": "array",
            "description": (
                "Indicator categories to fetch in bulk. Each category expands to "
                "its member indicators. Combined (union) with `indicators` if both "
                "are set.\n"
                "Members:\n"
                "  price_indices    -> CPI, inflationRate\n"
                "  economic_output  -> GDP, realGDP, nominalPotentialGDP, realGDPPerCapita\n"
                "  employment       -> unemploymentRate, totalNonfarmPayroll, initialClaims\n"
                "  consumer         -> consumerSentiment, retailSales, totalVehicleSales\n"
                "  production       -> industrialProductionTotalIndex, durableGoods\n"
                "  monetary         -> federalFunds, retailMoneyFunds"
            ),
            "items": {"type": "string", "enum": CATEGORY_NAMES},
            "default": None,
        }),
    ] = None,
    years_back: Annotated[int, Param(min_val=1, max_val=10)] = 5,
    limit: Annotated[Optional[int], Param(min_val=1, max_val=120)] = None,
) -> str:
    """Fetch historical US macroeconomic indicator data at monthly resolution.

Returns a dictionary keyed by indicator name, each containing a list of
{date, value} data points sorted chronologically (oldest -> newest). Series
are collapsed to one observation per calendar month (last value of the
month), so daily series like inflationRate return ~12 points per year
instead of ~252.

**Selecting indicators:**
- `indicators` — pick exact indicator names.
- `categories` — pick groups in bulk (e.g. all employment indicators).
- Both can be combined — the result is the union of the two sets.
- If both are omitted, all 16 indicators are returned.

**Sizing the response:**
- `years_back` sets the lookback window (default 5 years).
- `limit` caps the number of MOST RECENT monthly observations returned
  per indicator. Use this to keep payloads small when you only need the
  recent trend — e.g. limit=6 for the last 6 months, limit=12 for the
  last year. Omit to return the full window.

**Indicator categories (16 total):**
- price_indices: CPI, inflationRate
- economic_output: GDP, realGDP, nominalPotentialGDP, realGDPPerCapita
- employment: unemploymentRate, totalNonfarmPayroll, initialClaims
- consumer: consumerSentiment, retailSales, totalVehicleSales
- production: industrialProductionTotalIndex, durableGoods
- monetary: federalFunds, retailMoneyFunds

**Use Cases:**
- Recent inflation snapshot: indicators=['CPI', 'inflationRate'], limit=6
- All employment data, last year: categories=['employment'], limit=12
- Labor market + Fed funds: categories=['employment', 'monetary']
- Inflation + growth combo: categories=['price_indices', 'economic_output']
- Bulk pull: indicators=None, categories=None (returns all 16, use sparingly)

    Args:
        indicators: Specific indicator names to fetch (default: None)
        categories: Indicator categories to expand and fetch (default: None)
        years_back: Years of historical data (default: 5)
        limit: Max number of most-recent monthly observations per indicator
            (default: None = return full window)

    Examples:
        macro_indicators(indicators=['CPI', 'inflationRate'], years_back=3)
        macro_indicators(categories=['employment'], limit=12)
        macro_indicators(categories=['monetary'], indicators=['CPI'], limit=6)
        macro_indicators(indicators=['GDP', 'unemploymentRate'], years_back=10)
    """
    try:
        # Reason: validate category names before expansion so a typo fails fast
        if categories is not None:
            invalid_cats = [c for c in categories if c not in CATEGORY_INDICATORS]
            if invalid_cats:
                return error_response(
                    f"Invalid categories: {invalid_cats}. Valid: {CATEGORY_NAMES}"
                )

        # Reason: union of explicit indicators and category-expanded indicators.
        # If neither is supplied, default to all 16. Preserve canonical order from
        # INDICATOR_NAMES so the output is stable regardless of input order.
        if indicators is None and categories is None:
            target_indicators = list(INDICATOR_NAMES)
        else:
            selected: set[str] = set(indicators or [])
            for cat in categories or []:
                selected.update(CATEGORY_INDICATORS[cat])
            target_indicators = [i for i in INDICATOR_NAMES if i in selected]

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

            # Reason: FMP returns inflationRate as daily; other 15 are monthly/quarterly.
            # Collapse to one row per calendar month (last observation) to keep payload
            # consistent across indicators. No-op for monthly/quarterly series.
            df = df.groupby(df["date"].dt.to_period("M"), as_index=False).last()

            if limit is not None:
                df = df.tail(limit)

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
