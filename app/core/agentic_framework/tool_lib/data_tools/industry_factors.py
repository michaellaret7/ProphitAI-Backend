from app.core.calculations.sectors.industry import calc_industry_factor_benchmark_calculations

def get_industry_benchmark_calculations(industry: str, factor: str) -> dict:
    """Get the industry benchmark calculations for a given industry and factor.
    
    Args:
        industry: The industry to get the benchmark calculations for
        factor: The factor to get the benchmark calculations for
        
    Returns:
        Dictionary containing the benchmark calculations
    """
    return calc_industry_factor_benchmark_calculations(industry, factor).to_dict()

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
