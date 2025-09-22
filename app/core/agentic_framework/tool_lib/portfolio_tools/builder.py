import yaml
from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.build.builder import CorrelationPortfolioBuilder
from app.core.calculations.core import DataService
from datetime import datetime, timedelta

def build_portfolio(portfolio_dict: any) -> str:
    """
    Parse ANY portfolio data into a proper portfolio dict and build optimized portfolio
    
    Args:
        portfolio_data: Any format - string, dict, list, etc.
        Examples:
            - "AAPL 10% long, MSFT 5% short"
            - {"AAPL": 0.1, "MSFT": -0.05}  
            - [("AAPL", 0.1, "long")]
    
    Returns:
        Dict in format: {"TICKER": {"allocation": 0.x, "position": "long/short"}, ...}
        Or error message if build fails
    """
    # Parse any input into portfolio dict format using the canonical converter
    try:
        portfolio_dict = canonical_portfolio(portfolio_dict)
    except Exception as e:
        return yaml.dump({"error": f"Error parsing portfolio: {str(e)}"}, default_flow_style=False)

    # Debug: Check which tickers have price data available
    ds = DataService()
    end = datetime.now()
    start = end - timedelta(days=252)
    requested_tickers = list(portfolio_dict.keys())
    
    # Check price data availability
    price_map = ds.get_bulk_close_series(requested_tickers, start, end)
    missing_tickers = []
    empty_tickers = []
    
    for ticker in requested_tickers:
        if ticker not in price_map:
            missing_tickers.append(ticker)
        elif price_map[ticker] is None or price_map[ticker].empty:
            empty_tickers.append(ticker)
    
    if missing_tickers or empty_tickers:
        error_msg = []
        if missing_tickers:
            error_msg.append(f"Tickers not found in database: {', '.join(missing_tickers)}")
        if empty_tickers:
            error_msg.append(f"Tickers with no price data: {', '.join(empty_tickers)}")
        
        # Return detailed error about which tickers are problematic
        return yaml.dump({"error": f"Cannot build portfolio - {'; '.join(error_msg)}. Please use only tickers with available price data."}, default_flow_style=False)

    built_portfolio = CorrelationPortfolioBuilder().build_portfolio(
        tickers=portfolio_dict,  
        target_annual_vol=0.20,
        portfolio_value=1_000_000,
        leverage=2.0,
        target_net_exposure=0.30,
        lookback_days=252,
        max_position_weight=0.10,
    )
    
    # Check if the build was successful
    if "error" in built_portfolio:
        # Return the error message for debugging
        return yaml.dump({"error": f"Portfolio build failed: {built_portfolio['error']}"}, default_flow_style=False)
    
    if "status" in built_portfolio and built_portfolio["status"] == "success":
        if "final_portfolio" in built_portfolio:
            return yaml.dump(built_portfolio["final_portfolio"], default_flow_style=False)
        else:
            return yaml.dump({"error": "Build succeeded but final_portfolio not found in result"}, default_flow_style=False)
    
    # If we get here, something unexpected happened
    return yaml.dump({"error": f"Unexpected result structure: {list(built_portfolio.keys())}"}, default_flow_style=False)


# Tool Schema Constants
BUILD_PORTFOLIO_NAME = "build_portfolio"

BUILD_PORTFOLIO_DESCRIPTION = (
    "Build an optimized long/short portfolio with historical data, optimization, and risk controls. "
    "Returns weights, position_sizes, core risk metrics, exposures, and final_portfolio. "
    "CRITICAL: include portfolio_dict with ALL holdings. Example: build_portfolio(portfolio_dict={'AAPL': {'allocation': 0.5, 'position': 'long'}, 'KO': {'allocation': 0.5, 'position': 'short'}})"
)

BUILD_PORTFOLIO_PARAMETERS = {
    "type": "object",
    "properties": {
        "portfolio_dict": {
            "type": "object",
            "description": (
                "**MANDATORY - DO NOT OMIT THIS PARAMETER.** "
                "Complete portfolio with ALL holdings. "
                "Keys = ticker symbols (e.g., 'AAPL'). "
                "Values = objects with 'allocation' (decimal 0-1) and 'position' ('long'/'short'). "
                "You MUST include this parameter with all portfolio tickers."
                "\n\n"
                """Example of CORRECT function call:
                build_portfolio(
                    portfolio_dict={
                        "AAPL": {"allocation": 0.125, "position": "long"},
                        "MSFT": {"allocation": 0.125, "position": "long"},
                        "AMZN": {"allocation": 0.125, "position": "long"},
                        "TSLA": {"allocation": 0.125, "position": "long"},
                        "META": {"allocation": 0.125, "position": "long"},
                        "SPY": {"allocation": 0.125, "position": "long"},
                        "QQQ": {"allocation": 0.125, "position": "long"},
                        "IWM": {"allocation": 0.125, "position": "long"}
                    }
                )"""
            ),
            "patternProperties": {
                "^[A-Z]{1,5}$": {
                    "type": "object",
                    "properties": {
                        "allocation": {
                            "type": "number",
                            "description": "Weight as decimal (e.g., 0.125 for 12.5%)",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "position": {
                            "type": "string",
                            "description": "Must be 'long' or 'short'",
                            "enum": ["long", "short"]
                        }
                    },
                    "required": ["allocation", "position"],
                    "additionalProperties": False
                }
            },
            "minProperties": 1,
            "additionalProperties": False
        },
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