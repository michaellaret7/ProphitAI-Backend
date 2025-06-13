from .get_data import get_stock_data, get_tickers, get_portfolio_returns, calculate_stock_metrics
from typing import List, Dict, Callable, Any

# Define all tools here
TOOLS: List[Dict[str, Any]] = [
    {
        "name": "get_stock_data",
        "description": "Get the historical stock data in hour increments for a given ticker and date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "The stock ticker symbol to get price for."},
                "start_date_str": {"type": "string", "description": "The start date in 'YYYY-MM-DD' format."},
                "end_date_str": {"type": "string", "description": "The end date in 'YYYY-MM-DD' format."}
            },
            "required": ["ticker", "start_date_str", "end_date_str"]
        },
        "function": get_stock_data
    },
    {
        "name": "get_tickers",
        "description": "Get a list of available stock ticker symbols",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "function": get_tickers
    },
    {
        "name": "calculate_stock_metrics",
        "description": "Calculate financial metrics (max drawdown, volatility, etc.) for all available stock tickers within a specific date range.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date_str": {"type": "string", "description": "The start date for the analysis period in 'YYYY-MM-DD' format."},
                "end_date_str": {"type": "string", "description": "The end date for the analysis period in 'YYYY-MM-DD' format."}
            },
            "required": ["start_date_str", "end_date_str"]
        },
        "function": calculate_stock_metrics
    },
    {
        "name": "get_portfolio_returns",
        "description": "Calculate the cumulative hourly returns for an equally weighted portfolio of all available stock tickers.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date_str": {"type": "string", "description": "The start date in 'YYYY-MM-DD' format."},
                "end_date_str": {"type": "string", "description": "The end date in 'YYYY-MM-DD' format."}
            },
            "required": ["start_date_str", "end_date_str"]
        },
        "function": get_portfolio_returns
    }
    # Add more tools here in the same format if needed
]

def register_tools(agent_instance):
    """
    Register all defined tools with the given StressTestAgent instance.
    
    Args:
        agent_instance: StressTestAgent instance to register tools with
    """
    for tool_config in TOOLS:
        agent_instance.add_tool(
            name=tool_config["name"],
            description=tool_config["description"],
            parameters=tool_config["parameters"],
            function=tool_config["function"]
        ) 