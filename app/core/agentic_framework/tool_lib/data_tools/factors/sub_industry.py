"""Sub-industry-level factor benchmark tools."""

from typing import Optional
from datetime import datetime
import pandas as pd
from app.core.calculations.sectors.sub_industry import calc_sub_industry_factor_benchmark_calculations
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.token_count import get_token_count

VALID_FACTORS = ["growth", "value", "momentum", "quality", "volatility"]

@log_simulation_data_range()
def get_sub_industry_factor_benchmark(
    sub_industries: str | list[str],
    factor: str,
    _simulation_date: Optional[datetime] = None
) -> str:
    """Get sub-industry-level factor benchmark calculations.

    Calculates factor metrics (growth, value, momentum, quality, volatility) for all stocks
    within specified sub-industries, providing a more granular benchmark than industry-level
    for comparing individual stocks against their closest peers.

    Args:
        sub_industries: Sub-industry name or list of sub-industry names
                       (e.g., 'soft_drinks' or ['soft_drinks', 'packaged_foods_meats', 'household_products'])
        factor: Factor to calculate - one of:
                - 'growth': Revenue/earnings growth metrics
                - 'value': Valuation ratios (P/E, P/B, etc.)
                - 'momentum': Price momentum and trends
                - 'quality': Profitability and quality metrics
                - 'volatility': Price volatility and risk metrics
        _simulation_date: INTERNAL USE ONLY - For simulation mode, not exposed to agents

    Returns:
        JSON formatted string with factor benchmark data for the sub-industries including:
        - Sub-industry-level aggregated factor metrics for each sub-industry
        - Constituent ticker statistics
        - Benchmark values for comparison

    Note:
        Sub-industry names must match the standard classification (e.g., 'soft_drinks', not 'soft drink').
        Use lowercase with underscores for multi-word sub-industries (e.g., 'packaged_foods_meats').
        Sub-industries provide more granular peer comparison than broader industry groupings.
    """
    try:
        # Normalize to list for uniform processing
        if isinstance(sub_industries, str):
            sub_industries_list = [sub_industries]
        elif isinstance(sub_industries, list):
            sub_industries_list = sub_industries
        else:
            return error_response("Parameter 'sub_industries' must be a string or list of strings.")

        # Validate list is not empty
        if not sub_industries_list:
            return error_response("Parameter 'sub_industries' must not be empty.")

        # Validate each sub-industry in the list
        for sub_ind in sub_industries_list:
            if not isinstance(sub_ind, str) or not sub_ind:
                return error_response("Each sub-industry must be a non-empty string.")

        # Validate factor parameter
        if not isinstance(factor, str) or not factor:
            return error_response("Parameter 'factor' must be a non-empty string.")

        if factor not in VALID_FACTORS:
            return error_response(
                f"Invalid factor '{factor}'. Must be one of: {VALID_FACTORS}"
            )

        # Calculate factor benchmarks for each sub-industry
        results = {}
        for sub_industry in sub_industries_list:
            try:
                sub_industry_data = calc_sub_industry_factor_benchmark_calculations(
                    sub_industry,
                    factor,
                    as_of_date=_simulation_date
                ).to_dict()

                # Check if data is empty (sub-industry not found or no tickers)
                if not sub_industry_data or all(v is None or (isinstance(v, float) and pd.isna(v)) for v in sub_industry_data.values()):
                    results[sub_industry] = {
                        "error": f"No data found for sub-industry '{sub_industry}'"
                    }
                else:
                    results[sub_industry] = sub_industry_data

            except Exception as e:
                results[sub_industry] = {
                    "error": str(e)
                }

        # Return results with metadata
        response_data = {
            "factor": factor,
            "sub_industries_requested": len(sub_industries_list),
            "results": results
        }

        return success_response(response_data)
    except Exception as e:
        return error_response(e)


if __name__ == "__main__":
    x = get_sub_industry_factor_benchmark(sub_industries=['semiconductors', 'technology_hardware_storage_and_peripherals'], factor='value')
    print(x)
    print(get_token_count(x))

    from app.db.core.db_config import MarketSession
    from app.db.core.models.market_data_models import Ticker

    with MarketSession() as session:
        x = session.query(Ticker).filter(Ticker.ticker == 'AAPL').first().sub_industry
        print(x)


# Tool Schema Constants
GET_SUB_INDUSTRY_FACTOR_BENCHMARK_DESCRIPTION = (
    "Get sub-industry-level factor benchmark calculations for one or more sub-industries. "
    "Returns aggregated factor metrics for all stocks within the specified sub-industries, providing more granular "
    "peer comparison than industry-level benchmarks. Supports both single sub-industry and multiple sub-industries in one call. "
    "\n\n**Supported Factors:**"
    "\n  - growth: Revenue/earnings growth metrics"
    "\n  - value: Valuation ratios (P/E, P/B, P/S, etc.)"
    "\n  - momentum: Price momentum and trend metrics"
    "\n  - quality: Profitability and quality metrics (ROE, margins, etc.)"
    "\n  - volatility: Price volatility and risk metrics"
    "\n\n**Use Cases:**"
    "\n  - Compare stock performance against closest peers (sub-industry level)"
    "\n  - More granular peer comparison than industry benchmarks"
    "\n  - Identify sub-industry-specific trends and patterns"
    "\n  - Screen for stocks within narrow peer groups"
    "\n  - Build highly focused peer-relative portfolios"
    "\n  - Compare factor metrics across multiple sub-industries efficiently"
    "\n\n**Important Notes:**"
    "\n  - Sub-industry names are lowercase with underscores (e.g., 'soft_drinks', not 'Soft Drinks')"
    "\n  - Sub-industries are more specific than industries (e.g., 'soft_drinks' vs 'beverages')"
    "\n  - Use for closer peer comparison than broad industry benchmarks"
    "\n  - Data availability depends on number of tickers in the sub-industry"
    "\n  - Can pass single sub-industry string or list of sub-industries"
    "\n\n**Common Sub-Industries (Consumer Staples Examples):**"
    "\n  - Beverages: 'soft_drinks', 'distillers_vintners', 'brewers'"
    "\n  - Food Products: 'packaged_foods_meats', 'agricultural_farm_products'"
    "\n  - Household Products: 'household_products'"
    "\n  - Personal Products: 'personal_products'"
    "\n  - Tobacco: 'tobacco'"
    "\n\n**Examples:**"
    "\n  get_sub_industry_factor_benchmark(sub_industries='soft_drinks', factor='growth')"
    "\n  get_sub_industry_factor_benchmark(sub_industries=['soft_drinks', 'distillers_vintners'], factor='value')"
    "\n  get_sub_industry_factor_benchmark(sub_industries=['packaged_foods_meats', 'household_products', 'personal_products'], factor='quality')"
)

GET_SUB_INDUSTRY_FACTOR_BENCHMARK_PARAMETERS = {
    "type": "object",
    "properties": {
        "sub_industries": {
            "oneOf": [
                {
                    "type": "string",
                    "description": "Single sub-industry name"
                },
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of sub-industry names"
                }
            ],
            "description": (
                "Sub-industry name(s) to get factor benchmark for. Can be a single string or array of strings. "
                "Must be lowercase with underscores. "
                "Examples: 'soft_drinks', ['soft_drinks', 'packaged_foods_meats'], ['household_products', 'tobacco']. "
                "Sub-industries provide more granular peer groups than broader industries."
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
    "required": ["sub_industries", "factor"],
    "additionalProperties": False
}

GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL = {
    "name": "get_sub_industry_factor_benchmark",
    "description": GET_SUB_INDUSTRY_FACTOR_BENCHMARK_DESCRIPTION,
    "parameters": GET_SUB_INDUSTRY_FACTOR_BENCHMARK_PARAMETERS,
    "function": get_sub_industry_factor_benchmark,
}
