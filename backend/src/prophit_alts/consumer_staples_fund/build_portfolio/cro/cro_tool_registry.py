from backend.src.prophit_alts.consumer_staples_fund.build_portfolio.cro.cro_tools import *
from backend.src.stress_test.runner import run_stress_test_workflow
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import get_upside_downside_ratios
from backend.src.db.core.db_config import ProphitAltsSession
from backend.src.db.core.prophit_alts_models import *

def register_cro_tools(agent):
    """
    Register all CRO agent tools with the provided agent instance.
    
    Args:
        agent: The CROAgent instance to register tools with
    """
    
    # Stress test tool
    agent.add_tool(
        name="stress_test",
        description="Run an extensive stress test on the provided portfolio.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values"
                }
            },
            "required": ["portfolio_dict"]
        },
        function=lambda portfolio_dict: run_stress_test_workflow(portfolio_dict)
    )
    
    # Larger ticker pool tool
    agent.add_tool(
        name="get_larger_ticker_pool",
        description="Get the larger pool of tickers from the CIO agent's original selection. Use this when you need alternative tickers to substitute or add to the portfolio. Returns a dictionary of ticker_name: {position, industry, risk_allocation, reasoning}. THIS TAKES NO PARAMETERS.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=lambda: get_larger_ticker_pool()
    )

    # Upside/downside ratios tool
    agent.add_tool(
        name="get_upside_downside_ratios",
        description="Get the upside capture and downside capture ratios for the portfolio.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values"
                }
            },
            "required": ["portfolio_dict"]
        },
        function=lambda portfolio_dict: get_upside_downside_ratios(portfolio_dict)
    )

    # Factor calculations tool
    agent.add_tool(
        name="get_all_factor_calculations",
        description="Get all factor calculations for a ticker. This is good for fundamental analysis on a single ticker.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "The ticker symbol you want to get factor calculations for"
                }
            },
            "required": ["ticker"]
        },
        function=lambda ticker: get_all_factor_calculations(ticker)
    )

    # Ticker performance metrics tool
    agent.add_tool(
        name="get_ticker_performance_metrics",
        description="Get performance metrics for a ticker. This is good for technical analysis on a single ticker.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "The ticker symbol you want to get performance metrics for"
                }
            },
            "required": ["ticker"]
        },
        function=lambda ticker: get_ticker_performance_metrics(ticker)
    )

    # Most recent fundamentals tool
    agent.add_tool(
        name="get_most_recent_fundamentals",
        description="Get the most recent fundamentals for a ticker. This is good for fundamental analysis on a single ticker.",
        parameters={
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string", 
                    "description": "The ticker symbol you want to get the most recent fundamentals for"
                },
                "fundamentals_type": {
                    "type": "string", 
                    "description": "The type of fundamentals you want to get. Options are: ['balance_sheet', 'income_statement', 'cash_flow_statement', 'financial_ratios', 'analyst_estimates', 'all']"
                }
            },
            "required": ["ticker", "fundamentals_type"]
        },
        function=lambda ticker, fundamentals_type: get_most_recent_fundamentals(ticker, fundamentals_type)
    )

    # Portfolio performance analysis tool
    agent.add_tool(
        name="analyze_portfolio_performance",
        description="Analyze the performance of the portfolio. This is good for portfolio level analysis.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "Dictionary with tickers as keys and {'conviction': float, 'position': 'long'|'short'} as values. Follow the <Dictionary Format Rules> from the prompt for this format."
                }
            },
            "required": ["portfolio_dict"]
        },
        function=lambda portfolio_dict: analyze_portfolio_performance(portfolio_dict)
    )

    # Initial portfolio data tool
    agent.add_tool(
        name="get_initial_portfolio_data",
        description="Get the initial portfolio stress test and performance analysis from the CIO agent.",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        function=lambda: get_initial_portfolio_data()
    )

    # Initial portfolio dictionary tool
    agent.add_tool(
        name="get_initial_portfolio_dict",
        description="Get the initial portfolio dictionary. If you do not have the initial portfolio dictionary, you must call this tool first.",
        parameters={},
        function=lambda: get_initial_portfolio_dict()
    )

    agent.add_tool(
        name="calculate_correlation_matrix",
        description="Calculate the correlation matrix for the portfolio.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "Dictionary with tickers as keys and {'weight': float, 'position': 'long'|'short'} as values"
                }
            },
            "required": ["portfolio_dict"]
        },
        function=lambda portfolio_dict: calculate_correlation_matrix(portfolio_dict)
    )

    agent.add_tool(
        name="calculate_covariance_matrix",
        description="Calculate the covariance matrix for the portfolio.",
        parameters={
            "type": "object",
            "properties": {
                "portfolio_dict": {
                    "type": "object",
                    "description": "Dictionary with tickers as keys and {'weight': float, 'position': 'long'|'short'} as values"
                }
            },
            "required": ["portfolio_dict"]
        },
        function=lambda portfolio_dict: calculate_covariance_matrix(portfolio_dict)
    )