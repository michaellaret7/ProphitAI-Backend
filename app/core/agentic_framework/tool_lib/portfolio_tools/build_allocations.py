from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.allocations import SimplePortfolioAllocator
from app.core.calculations.core.config import DEFAULT_LOOKBACK_3Y
from app.core.agentic_framework.tool_lib.common.schemas import PORTFOLIO_DICT_SCHEMA
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response

def build_portfolio(portfolio_dict: any, **kwargs) -> str:
    """
    Build optimized long/short portfolio using SimplePortfolioAllocator with risk-based optimization.

    Accepts any portfolio format and auto-converts to canonical format using GPT parser.
    Uses conviction values for allocation logic with risk-based weights and exposure targets.

    Args:
        portfolio_dict: Any format - string, dict, list, etc.
        Examples:
            - "AAPL 80% long, MSFT 60% short"  # String format
            - {"AAPL": {"conviction": 0.8, "position": "long"}}  # Conviction format
            - {"AAPL": 0.8, "MSFT": -0.6}  # Simple dict (negative = short)
            - [("AAPL", 0.8, "long"), ("MSFT", 0.6, "short")]  # List of tuples

    Returns:
        YAML string with structured portfolio: {"TICKER": {"ticker": str, "position": "long/short", "allocation": float}, ...}
        Allocation values are rounded to 3 decimal places.
        Returns error message if build fails.
    """
    # Validate portfolio_dict is not None
    if portfolio_dict is None:
        return error_response(
            "Missing required argument: 'portfolio_dict'. Please try again with a valid portfolio. "
            "Example: portfolio_dict={'AAPL': {'conviction': 0.8, 'position': 'long'}, 'MSFT': {'conviction': 0.6, 'position': 'long'}}"
        )

    # Parse any input into portfolio dict format using the canonical converter
    try:
        canonical_portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return error_response(f"Error parsing portfolio: {str(e)}")

    # Convert canonical format (allocation) to conviction format for SimplePortfolioAllocator
    conviction_portfolio = {}
    for ticker, data in canonical_portfolio_dict.items():
        conviction_portfolio[ticker] = {
            "conviction": data["allocation"],  # Use allocation as conviction
            "position": data["position"]
        }

    # Use SimplePortfolioAllocator to build the portfolio
    try:
        allocator = SimplePortfolioAllocator(
            portfolio_dict=portfolio_dict,
            target_annual_vol=0.17,
            target_gross_exposure=1.8,
            target_net_exposure=0.3,
            lookback_days=DEFAULT_LOOKBACK_3Y  # 3 years of calendar days
        )

        result = allocator.allocate()

        # Round allocation values to 3 decimal places
        rounded_result = {}
        for ticker, data in result.items():
            rounded_result[ticker] = {
                "ticker": data["ticker"],
                "position": data["position"],
                "allocation": round(data["allocation"], 3)
            }

        return success_response(rounded_result)

    except Exception as e:
        return error_response(f"Error building portfolio: {str(e)}")


# Tool Schema Constants
BUILD_PORTFOLIO_NAME = "build_portfolio"

BUILD_PORTFOLIO_DESCRIPTION = (
    "Build an optimized long/short portfolio using SimplePortfolioAllocator with risk-based optimization. "
    "Accepts any portfolio format (string, dict, list) and converts to canonical format. "
    "Uses conviction values for allocation logic with risk-based weights and exposure targets. "
    "Returns structured portfolio with ticker, position, and rounded allocation values. "
    "CRITICAL: include portfolio_dict with ALL holdings. Example: build_portfolio(portfolio_dict={'AAPL': {'conviction': 0.8, 'position': 'long'}, 'TSLA': {'conviction': 0.6, 'position': 'short'}})"
)

BUILD_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": PORTFOLIO_DICT_SCHEMA,
    },
    "required": ["portfolio_dict"],
    "additionalProperties": False
}

BUILD_PORTFOLIO_TOOL = {
    "name": BUILD_PORTFOLIO_NAME,
    "description": BUILD_PORTFOLIO_DESCRIPTION,
    "parameters": BUILD_PORTFOLIO_PARAMETERS,
    "function": build_portfolio,
}