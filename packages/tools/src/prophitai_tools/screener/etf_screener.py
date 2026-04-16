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

# Classification parameters are lists of enum strings, not ranges.
LIST_PARAMS = frozenset({'industries', 'sub_industries'})


def _validate_and_convert(kwargs: dict) -> tuple[dict, str | None]:
    """Validate parameter shapes and convert ranges to tuples.

    Classification params (LIST_PARAMS) must be lists of strings.
    All other params must be 2-element ranges [min, max] where each is
    a number or null.

    Returns:
        (converted_kwargs, None) on success, ({}, error_message) on validation failure.
    """
    converted: dict = {}

    for key, value in kwargs.items():
        if value is None:
            continue

        if key in LIST_PARAMS:
            if not isinstance(value, list):
                return {}, f"Parameter '{key}' must be a list of strings, got {type(value).__name__}"
            converted[key] = value
            continue

        # Range parameter — must be [min, max] with numbers or null
        if not isinstance(value, list):
            return {}, (
                f"Parameter '{key}' must be a [min, max] array, got {type(value).__name__}. "
                f"Example: {key}=[10, 30] or {key}=[null, 30]"
            )
        if len(value) != 2:
            return {}, (
                f"Parameter '{key}' must be a 2-element [min, max] array, got {len(value)} element(s). "
                f"Example: {key}=[10, 30]"
            )
        for v in value:
            if v is not None and not isinstance(v, (int, float)):
                return {}, (
                    f"Parameter '{key}' range values must be numbers or null, "
                    f"got {type(v).__name__}: {v!r}"
                )

        converted[key] = tuple(value)

    return converted, None


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
    """
    converted_kwargs, err = _validate_and_convert(kwargs)
    if err is not None:
        return error_response(err)

    try:
        results, error = screen_etfs(**converted_kwargs)
    except TypeError as e:
        # Reason: unknown kwargs from the LLM surface as TypeError from _build_query
        msg = str(e)
        if 'unexpected keyword argument' in msg:
            return error_response(f"Unknown screener parameter: {msg}")
        raise

    if error is not None:
        return error_response(error)

    results_data = [r.model_dump() for r in results]
    results_yaml = yaml.dump(results_data, default_flow_style=False)

    return success_response(results_yaml)


# Reason: Screener has multiple range parameters defined in a pre-built schema.
# Override auto-generated (empty) schema with the complex pre-built one.
etf_screener.tool["description"] = ETF_SCREENER_DESCRIPTION
etf_screener.tool["parameters"] = ETF_SCREENER_PARAMETERS



