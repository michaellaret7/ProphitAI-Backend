from app.core.agentic_framework.tool_lib.data_tools.screeners.equity.execute import execute_query
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.core.agentic_framework.tool_lib.data_tools.screeners.equity.schema import EQUITY_SCREENER_DESCRIPTION, EQUITY_SCREENER_PARAMETERS
import yaml

def equity_screener(**kwargs):
    """Screen equities based on fundamental, valuation, and performance criteria."""
    # Convert lists to tuples for range parameters (LLM sends JSON arrays)
    converted_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, list) and len(value) == 2:
            converted_kwargs[key] = tuple(value)
        else:
            converted_kwargs[key] = value

    results, error = execute_query(**converted_kwargs)

    if error is not None:
        return error_response(error)

    # Convert Pydantic models to dicts for clean YAML output
    results_data = [r.model_dump() for r in results]
    results_yaml = yaml.dump(results_data, default_flow_style=False)

    return success_response(results_yaml)

if __name__ == "__main__":
    # Test with list format (as LLM would send via JSON)
    results = equity_screener(
        sectors=['equity_sector_information_technology'],
        market_cap=(50000000000, None),  # LLM sends arrays, converted to tuples
        pe_ratio_ttm=[15, 60],
        momentum_3m=[0.05, None],
        ann_return=[0.10, None]
    )
    print(results)


EQUITY_SCREENER_TOOL = {
    "name": "equity_screener",
    "description": EQUITY_SCREENER_DESCRIPTION,
    "parameters": EQUITY_SCREENER_PARAMETERS,
    "function": equity_screener,
}

