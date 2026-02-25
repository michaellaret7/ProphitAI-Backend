"""Equity screener tool for screening stocks based on fundamental criteria."""

import yaml

from app.core.atlas.tools.decorator import agent_tool
from app.core.atlas.tools.responses import success_response, error_response
from app.core.atlas.tools.screener.equity.execute import execute_query
from app.core.atlas.tools.screener.equity.schema import (
    EQUITY_SCREENER_DESCRIPTION,
    EQUITY_SCREENER_PARAMETERS,
)


# ================================
# --> Helper funcs
# ================================

def _convert_lists_to_tuples(kwargs: dict) -> dict:
    """Convert list values to tuples for range parameters (LLM sends JSON arrays)."""
    converted = {}
    for key, value in kwargs.items():
        if isinstance(value, list) and len(value) == 2:
            converted[key] = tuple(value)
        else:
            converted[key] = value
    return converted


# ================================
# --> Tools
# ================================

@agent_tool(name="equity_screener")
def equity_screener(**kwargs) -> str:
    """
    Screen equities based on fundamental, valuation, and performance criteria.

    Returns matching stocks with their key metrics. All numeric filters use
    [min, max] arrays where null means unbounded. Classification filters
    (sectors, industries, sub_industries) use OR logic.

    Returns:
        YAML-formatted list of matching stocks with metrics

    Examples:
        equity_screener(pe_ratio_ttm=[None, 15], dividend_yield_ttm=[0.03, None])
        >>> {"success": True, "data": "- ticker: KO\\n  ..."}

    Raises:
        Exception: If query execution fails
    """
    converted_kwargs = _convert_lists_to_tuples(kwargs)
    results, error = execute_query(**converted_kwargs)

    if error is not None:
        return error_response(error)

    results_data = [r.model_dump(exclude={"ticker_description"}) for r in results]
    results_yaml = yaml.dump(results_data, default_flow_style=False)

    return success_response(results_yaml)


# Reason: Screener has 60+ range parameters defined in a pre-built schema.
# Override auto-generated (empty) schema with the complex pre-built one.
equity_screener.tool["description"] = EQUITY_SCREENER_DESCRIPTION
equity_screener.tool["parameters"] = EQUITY_SCREENER_PARAMETERS


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(equity_screener(sectors=["equity_sector_financials"], pe_ratio_ttm=[None, 15]))
