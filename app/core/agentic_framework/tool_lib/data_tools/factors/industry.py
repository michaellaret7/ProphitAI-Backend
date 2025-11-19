"""Industry-level factor benchmark tools."""

from typing import Optional
from datetime import datetime, date
from functools import lru_cache
import pandas as pd
from app.core.calculations.sectors.industry import calc_industry_factor_benchmark_calculations
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.token_count import get_token_count

VALID_FACTORS = ["growth", "value", "momentum", "quality", "volatility"]

@log_simulation_data_range()
def get_industry_factor_benchmark(
    industries: str | list[str],
    factor: str,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get industry-level factor benchmark calculations.

    Calculates factor metrics (growth, value, momentum, quality, volatility) for all stocks
    within specified industries, providing a benchmark for comparing individual stocks against
    their industry peers.

    Args:
        industries: Industry name or list of industry names
                   (e.g., 'beverages' or ['beverages', 'food_products', 'household_products'])
        factor: Factor to calculate - one of:
                - 'growth': Revenue/earnings growth metrics
                - 'value': Valuation ratios (P/E, P/B, etc.)
                - 'momentum': Price momentum and trends
                - 'quality': Profitability and quality metrics
                - 'volatility': Price volatility and risk metrics
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        JSON formatted string with factor benchmark data for the industries including:
        - Industry-level aggregated factor metrics for each industry
        - Constituent ticker statistics
        - Benchmark values for comparison

    Note:
        Industry names must match the standard classification (e.g., 'beverages', not 'beverage').
        Use lowercase with underscores for multi-word industries (e.g., 'food_products').
        'consumer_staples' is a sector, not an industry - use specific industries like
        'beverages', 'food_products', 'household_products', etc.
    """
    try:
        # Normalize to list for uniform processing
        if isinstance(industries, str):
            industries_list = [industries]
        elif isinstance(industries, list):
            industries_list = industries
        else:
            return error_response("Parameter 'industries' must be a string or list of strings.")

        # Validate list is not empty
        if not industries_list:
            return error_response("Parameter 'industries' must not be empty.")

        # Validate each industry in the list
        for ind in industries_list:
            if not isinstance(ind, str) or not ind:
                return error_response("Each industry must be a non-empty string.")

        # Validate factor parameter
        if not isinstance(factor, str) or not factor:
            return error_response("Parameter 'factor' must be a non-empty string.")

        if factor not in VALID_FACTORS:
            return error_response(
                f"Invalid factor '{factor}'. Must be one of: {VALID_FACTORS}"
            )

        # Calculate factor benchmarks for each industry
        results = {}
        for industry in industries_list:
            try:
                industry_data = calc_industry_factor_benchmark_calculations(
                    industry,
                    factor,
                    as_of_date=_simulation_date
                ).to_dict()

                # Check if data is empty (industry not found or no tickers)
                if not industry_data or all(v is None or (isinstance(v, float) and pd.isna(v)) for v in industry_data.values()):
                    results[industry] = {
                        "error": f"No data found for industry '{industry}'"
                    }
                else:
                    results[industry] = industry_data

            except Exception as e:
                results[industry] = {
                    "error": str(e)
                }

        # Return results with metadata
        response_data = {
            "factor": factor,
            "industries_requested": len(industries_list),
            "results": results
        }

        return success_response(response_data)
    except Exception as e:
        return error_response(e)

if __name__ == "__main__":
    x = get_industry_factor_benchmark(industries=['beverages', 'food_products', 'household_products'], factor='growth')
    print(x)
    print(get_token_count(x))

# Tool Schema Constants
GET_INDUSTRY_FACTOR_BENCHMARK_DESCRIPTION = (
    "Get industry-level factor benchmark calculations for one or more industries. "
    "Returns aggregated factor metrics for all stocks within the specified industries, useful for peer comparison. "
    "Supports both single industry and multiple industries in one call. "
    "\n\n**Supported Factors:**"
    "\n  - growth: Revenue/earnings growth metrics"
    "\n  - value: Valuation ratios (P/E, P/B, P/S, etc.)"
    "\n  - momentum: Price momentum and trend metrics"
    "\n  - quality: Profitability and quality metrics (ROE, margins, etc.)"
    "\n  - volatility: Price volatility and risk metrics"
    "\n\n**Use Cases:**"
    "\n  - Compare stock performance against industry benchmark"
    "\n  - Identify industry-wide trends in growth, valuation, momentum"
    "\n  - Assess relative positioning within industry peers"
    "\n  - Screen for stocks that deviate from industry norms"
    "\n  - Analyze industry factor exposure for portfolio construction"
    "\n  - Compare factor metrics across multiple industries efficiently"
    "\n\n**Important Notes:**"
    "\n  - Industry names are lowercase with underscores (e.g., 'food_products', not 'Food Products')"
    "\n  - 'consumer_staples' is a SECTOR, not an industry"
    "\n  - Use specific industries: 'beverages', 'food_products', 'household_products', etc."
    "\n  - Data availability depends on number of tickers in the industry"
    "\n  - Can pass single industry string or list of industries"
    "\n\n**Examples:**"
    "\n  get_industry_factor_benchmark(industries='beverages', factor='growth')"
    "\n  get_industry_factor_benchmark(industries=['beverages', 'food_products'], factor='value')"
    "\n  get_industry_factor_benchmark(industries=['household_products', 'personal_products', 'tobacco'], factor='quality')"
)

GET_INDUSTRY_FACTOR_BENCHMARK_PARAMETERS = {
    "type": "object",
    "properties": {
        "industries": {
            "oneOf": [
                {
                    "type": "string",
                    "description": "Single industry name"
                },
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of industry names"
                }
            ],
            "description": (
                "Industry name(s) to get factor benchmark for. Can be a single string or array of strings. "
                "Must be lowercase with underscores. "
                "Examples: 'beverages', ['beverages', 'food_products'], ['household_products', 'tobacco']. "
                "NOTE: 'consumer_staples' is a SECTOR, not an industry - use specific industries instead."
            ),
        },
        "factor": {
            "type": "string",
            "description": (
                "Factor to calculate: 'growth' (revenue/earnings growth), 'value' (valuation ratios), "
                "'momentum' (price trends), 'quality' (profitability metrics), or 'volatility' (risk metrics)."
            ),
            "enum": ["growth", "value", "momentum", "quality", "volatility"]
        },
    },
    "required": ["industries", "factor"],
    "additionalProperties": False
}

GET_INDUSTRY_FACTOR_BENCHMARK_TOOL = {
    "name": "get_industry_factor_benchmark",
    "description": GET_INDUSTRY_FACTOR_BENCHMARK_DESCRIPTION,
    "parameters": GET_INDUSTRY_FACTOR_BENCHMARK_PARAMETERS,
    "function": get_industry_factor_benchmark,
}