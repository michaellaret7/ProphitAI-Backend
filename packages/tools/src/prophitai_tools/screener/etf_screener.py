"""ETF screener tool for screening ETFs based on performance and cost criteria."""

import yaml

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.repositories.screener import screen_etfs
from prophitai_tools.screener.etf_schema import (
    ETF_SCREENER_DESCRIPTION,
    ETF_SCREENER_PARAMETERS,
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

@agent_tool(name="etf_screener", category="screener")
def etf_screener(**kwargs) -> str:
    """
    Screen ETFs based on performance, risk, cost, and classification criteria.

    Returns matching ETFs with their key metrics. All numeric filters use
    [min, max] arrays where null means unbounded. Classification filters
    (industries, sub_industries) use OR logic.

    Returns:
        YAML-formatted list of matching ETFs with metrics

    Examples:
        etf_screener(industries=["equity_etfs"], expense_ratio=[None, 0.002])
        >>> {"success": True, "data": "- ticker: SPY\\n  ..."}

    Raises:
        Exception: If query execution fails
    """
    converted_kwargs = _convert_lists_to_tuples(kwargs)
    results, error = screen_etfs(**converted_kwargs)

    if error is not None:
        return error_response(error)

    results_data = [r.model_dump() for r in results]
    results_yaml = yaml.dump(results_data, default_flow_style=False)

    return success_response(results_yaml)


# Reason: Screener has multiple range parameters defined in a pre-built schema.
# Override auto-generated (empty) schema with the complex pre-built one.
etf_screener.tool["description"] = ETF_SCREENER_DESCRIPTION
etf_screener.tool["parameters"] = ETF_SCREENER_PARAMETERS



