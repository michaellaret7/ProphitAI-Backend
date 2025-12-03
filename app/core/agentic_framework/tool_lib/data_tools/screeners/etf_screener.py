from app.core.agentic_framework.tool_lib.data_tools.screeners.etf.execute import execute_query
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.core.agentic_framework.tool_lib.data_tools.screeners.etf.schema import ETF_SCREENER_DESCRIPTION, ETF_SCREENER_PARAMETERS
import yaml

def etf_screener(**kwargs):
    """Screen ETFs based on fundamental, valuation, and performance criteria.
    
    Args:
        **kwargs: Keyword arguments for the ETF screener.
    Returns:
        A success response with the results in YAML format, or an error response if the screener fails.
    """
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


ETF_SCREENER_TOOL = {
    "name": "etf_screener",
    "description": ETF_SCREENER_DESCRIPTION,
    "parameters": ETF_SCREENER_PARAMETERS,
    "function": etf_screener,
}


