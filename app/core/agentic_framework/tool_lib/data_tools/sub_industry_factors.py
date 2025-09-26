import yaml
from app.core.calculations.sectors.sub_industry import calc_sub_industry_factor_benchmark_calculations

def get_sub_industry_benchmark_calculations(sub_industry: str, factor: str) -> str:
    """Get the sub-industry benchmark calculations for a given sub-industry and factor.
    
    Args:
        sub_industry: The sub-industry to get the benchmark calculations for
        factor: The factor to get the benchmark calculations for
        
    Returns:
        Dictionary containing the benchmark calculations
    """
    valid_factors = {"growth", "value", "momentum", "quality", "volatility"}

    if not isinstance(sub_industry, str) or not sub_industry:
        return "Error: Parameter 'sub_industry' must be a non-empty string."

    if not isinstance(factor, str) or factor not in valid_factors:
        return f"Error: Parameter 'factor' must be one of: {', '.join(valid_factors)}."
        
    return yaml.dump(calc_sub_industry_factor_benchmark_calculations(sub_industry, factor).to_dict(), default_flow_style=False)


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