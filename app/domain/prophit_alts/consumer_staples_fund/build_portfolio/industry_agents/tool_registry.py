from app.core.agentic_framework.base_agent.tool_lib.agent_specific.industry import (
    get_eligible_tickers,
    calc_industry_factor_benchmark_calculations,
    calc_sub_industry_factor_benchmark_calculations,
    get_weekly_returns,
    get_base_ticker_info,
)
from app.core.agentic_framework.base_agent.tool_lib.ticker.factors import calculate_ticker_factors
from app.core.agentic_framework.base_agent.tool_lib.data.repository import fetch_repository_data
from app.repositories.fundamental_data import get_fundamental_data

def register_industry_tools(agent):
    agent.add_tool(
        name="get_eligible_tickers",
        description="Get the eligible tickers for a given industry that are eligible for you to choose from.",
        parameters={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "The industry to get the eligible tickers for. For example, 'beverages', 'food_products', etc.",
                },
            },
            "required": ["industry"],
        },
        function=get_eligible_tickers,
    )

    agent.add_tool(
        name="get_industry_benchmark_calculations",
        description="Get the industry benchmark calculations for a given industry and factor. For example, 'beverages' and 'growth'. Another example is 'food_products' and 'value'.",
        parameters={
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
        },
        function=lambda industry, factor: calc_industry_factor_benchmark_calculations(industry, factor).to_dict(),
    )
    
    agent.add_tool(
        name="get_sub_industry_benchmark_calculations",
        description="Get the sub-industry benchmark calculations for a given sub-industry and factor. For example, 'soft_drinks' and 'growth'. Another example is 'packaged_foods' and 'value'.",
        parameters={
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
        },
        function=lambda sub_industry, factor: calc_sub_industry_factor_benchmark_calculations(sub_industry, factor).to_dict(),
    )
        
    agent.add_tool(
        name="calculate_ticker_factors",
        description="Calculate all factor metrics for a given ticker and factor type. Can calculate growth, value, momentum, quality, or volatility factors.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol to calculate factors for. For example, 'AAPL', 'MSFT', 'KO', etc.",
                },
                "factor": {
                    "type": "string",
                    "description": "The factor type to calculate. Options are 'growth', 'value', 'momentum', 'quality', or 'volatility'.",
                    "enum": ["growth", "value", "momentum", "quality", "volatility"]
                },
            },
            "required": ["ticker", "factor"],
        },
        function=calculate_ticker_factors,
    )
    
    agent.add_tool(
        name="get_weekly_returns",
        description="Get weekly returns for the last year for a given ticker symbol.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol to get weekly returns for. For example, 'AAPL', 'MSFT', 'KO', etc.",
                },
            },
            "required": ["ticker"],
        },
        function=get_weekly_returns,
    )
    
    agent.add_tool(
        name="get_fundamental_data",
        description="Get fundamental financial data for a ticker including income statements, balance sheets, cash flow statements, financial ratios, or analyst estimates.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The ticker symbol to get fundamental data for. For example, 'AAPL', 'MSFT', 'KO', etc.",
                },
                "statement_type": {
                    "type": "string",
                    "description": "Type of fundamental data to retrieve. Must be one of: 'income_statement', 'balance_sheet', 'cash_flow', 'financial_ratios', 'analyst_estimates'.",
                    "enum": ["income_statement", "balance_sheet", "cash_flow", "financial_ratios", "analyst_estimates"]
                },
                "quarters_back": {
                    "type": "integer",
                    "description": "Number of quarters of historical data to retrieve. Default is 1 (most recent quarter only).",
                    "default": 1
                },
            },
            "required": ["ticker", "statement_type"],
        },
        function=get_fundamental_data,
    )

    agent.add_tool(
        name="fetch_repository_data",
        description=(
            "Fetch auxiliary data for a ticker. Supported data_type: "
            "'press_releases','stock_news','price_target_news','grades_individual','grades_summary',"
            "'ratings','analyst_recommendations','price_target_summary','etf_info','etf_holdings',"
            "'earnings_transcripts','latest_transcript','dividends_series'."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Ticker symbol (e.g., 'AAPL').",
                },
                "data_type": {
                    "type": "string",
                    "description": "Type of data to fetch.",
                    "enum": [
                        "press_releases",
                        "stock_news",
                        "price_target_news",
                        "grades_individual",
                        "grades_summary",
                        "ratings",
                        "analyst_recommendations",
                        "price_target_summary",
                        "etf_info",
                        "etf_holdings",
                        "earnings_transcripts",
                        "latest_transcript",
                        "dividends_series"
                    ]
                },
                "limit": {
                    "type": "integer",
                    "description": "Optional max number of items (applies to earnings_transcripts).",
                    "minimum": 1,
                    "maximum": 4
                }
            },
            "required": ["ticker", "data_type"],
        },
        function=fetch_repository_data,
    )

    agent.add_tool(
        name="get_base_ticker_info",
        description="Retrieves foundational information for a list of stock tickers. The function takes a list of ticker symbols (e.g., ['AAPL', 'MSFT']) and returns key data points for each, including sector, industry, sub-industry, current price, market capitalization, average volume, EPS, and P/E ratio.",
        parameters={
            "type": "object",
            "properties": {
                "tickers": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "A list of ticker symbols to retrieve information for. For example, ['AAPL', 'MSFT', 'KO']",
                },
            },
            "required": ["tickers"],
        },
        function=get_base_ticker_info,
    )