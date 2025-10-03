import yaml
import pandas as pd
from app.core.calculations.sectors.industry import calc_industry_factor_benchmark_calculations
from app.utils.decorators.tool_validation import validate_required_args, validate_enum_arg, log_simulation_data_range

@validate_required_args('industry', 'factor')
@validate_enum_arg("factor", ["growth", "value", "momentum", "quality", "volatility"])
@log_simulation_data_range()
def get_industry_benchmark_calculations(industry: str, factor: str, **kwargs) -> str:
    """Get the industry benchmark calculations for a given industry and factor.

    Args:
        industry: The industry to get the benchmark calculations for
        factor: The factor to get the benchmark calculations for
        **kwargs: Additional keyword arguments (accepts _simulation_date for compatibility)

    Returns:
        Dictionary containing the benchmark calculations
    """
    try:
        if not isinstance(industry, str) or not industry:
            return yaml.dump({"success": False, "error": "Parameter 'industry' must be a non-empty string."}, default_flow_style=False)

        # Extract _simulation_date from kwargs for simulation mode
        _simulation_date = kwargs.get('_simulation_date', None)

        data = calc_industry_factor_benchmark_calculations(industry, factor, as_of_date=_simulation_date).to_dict()

        # Check if data is empty (industry not found or no tickers)
        if not data or all(v is None or (isinstance(v, float) and pd.isna(v)) for v in data.values()):
            return yaml.dump({
                "success": False,
                "error": f"No data found for industry '{industry}'. Please check the industry name. Example: 'beverages', 'food_products'"
            }, default_flow_style=False)

        return yaml.dump({"success": True, "data": data}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)

# Tool Schema Constants
GET_INDUSTRY_BENCHMARK_CALCULATIONS_DESCRIPTION = (
    "Get the industry benchmark calculations for a given industry and factor. For example, 'beverages' and 'growth'. "
    "Another example is 'food_products' and 'value'. Important Note: consumer_staples is not an industry, it is a sector.\n\n"
    "Example: get_industry_benchmark_calculations(industry='beverages', factor='growth')"
)

GET_INDUSTRY_BENCHMARK_CALCULATIONS_PARAMETERS = {
    "type": "object",
    "properties": {
        "industry": {
            "type": "string",
            "description": "The industry to get the benchmark calculations for. For example, 'beverages', 'food_products', etc.",
        },
        "factor": {
            "type": "string",
            "description": "The factor to get the benchmark calculations for. The options are 'growth', 'value', 'momentum', 'quality', and 'volatility'.",
            "enum": ["growth", "value", "momentum", "quality", "volatility"]
        },
    },
    "required": ["industry", "factor"],
}

GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL = {
    "name": "get_industry_benchmark_calculations",
    "description": GET_INDUSTRY_BENCHMARK_CALCULATIONS_DESCRIPTION,
    "parameters": GET_INDUSTRY_BENCHMARK_CALCULATIONS_PARAMETERS,
    "function": get_industry_benchmark_calculations,
}

if __name__ == "__main__":
    x = get_industry_benchmark_calculations(industry="beverages", factor="growth")
    print(x)
    x = yaml.safe_load(x)
    print(x["success"])