import yaml
import pandas as pd
from app.core.calculations.sectors.sub_industry import calc_sub_industry_factor_benchmark_calculations
from app.utils.decorators.tool_validation import validate_required_args, validate_enum_arg

@validate_required_args('sub_industry', 'factor')
@validate_enum_arg("factor", ["growth", "value", "momentum", "quality", "volatility"])
def get_sub_industry_benchmark_calculations(sub_industry: str, factor: str, **kwargs) -> str:
    """Get the sub-industry benchmark calculations for a given sub-industry and factor.

    Args:
        sub_industry: The sub-industry to get the benchmark calculations for
        factor: The factor to get the benchmark calculations for
        **kwargs: Additional keyword arguments (accepts _simulation_date for compatibility)

    Returns:
        Dictionary containing the benchmark calculations
    """
    try:
        if not isinstance(sub_industry, str) or not sub_industry:
            return yaml.dump({"success": False, "error": "Parameter 'sub_industry' must be a non-empty string."}, default_flow_style=False)

        # Extract _simulation_date from kwargs for simulation mode
        _simulation_date = kwargs.get('_simulation_date', None)

        data = calc_sub_industry_factor_benchmark_calculations(sub_industry, factor, as_of_date=_simulation_date).to_dict()

        # Check if data is empty (sub_industry not found or no tickers)
        if not data or all(v is None or (isinstance(v, float) and pd.isna(v)) for v in data.values()):
            return yaml.dump({
                "success": False,
                "error": f"No data found for sub_industry '{sub_industry}'. Please check the sub_industry name. Example: 'soft_drinks', 'packaged_foods_meats'"
            }, default_flow_style=False)

        return yaml.dump({"success": True, "data": data}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


# Tool Schema Constants
GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_DESCRIPTION = (
    "Get the sub-industry benchmark calculations for a given sub-industry and factor. For example, 'soft_drinks' and 'growth'. "
    "Another example is 'packaged_foods' and 'value'.\n\n"
    "Example: get_sub_industry_benchmark_calculations(sub_industry='soft_drinks', factor='growth')"
)

GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_PARAMETERS = {
    "type": "object",
    "properties": {
        "sub_industry": {
            "type": "string",
            "description": "The sub-industry to get the benchmark calculations for. For example, 'soft_drinks', 'packaged_foods', etc.",
        },
        "factor": {
            "type": "string",
            "description": "The factor to get the benchmark calculations for. The options are 'growth', 'value', 'momentum', 'quality', and 'volatility'.",
            "enum": ["growth", "value", "momentum", "quality", "volatility"]
        },
    },
    "required": ["sub_industry", "factor"],
}

GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL = {
    "name": "get_sub_industry_benchmark_calculations",
    "description": GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_DESCRIPTION,
    "parameters": GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_PARAMETERS,
    "function": get_sub_industry_benchmark_calculations,
}