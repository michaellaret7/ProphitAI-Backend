from backend.src.calculations_v2.sectors.industry import *
from backend.src.calculations_v2.sectors.sub_industry import *
from backend.src.calculations_v2.factors.growth import GrowthFactors
from backend.src.calculations_v2.factors.value import ValueFactors
from backend.src.calculations_v2.factors.momentum import MomentumFactors
from backend.src.calculations_v2.factors.quality import QualityFactors
from backend.src.calculations_v2.factors.volatility import VolatilityFactors
from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.returns.calculator import ReturnsCalculator
from backend.src.repositories.fundamental_data import get_fundamental_data
from datetime import datetime, timedelta

def get_weekly_returns(ticker: str):
    """Get weekly returns for the last year for a given ticker."""
    ds = DataService()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    # Get price data for the ticker
    price_data = ds.get_price_data(ticker, start_date, end_date)
    if price_data is None or price_data.frame.empty:
        return {"error": f"No price data available for {ticker}"}
    
    # Get closing prices
    close_prices = price_data.frame['close']
    
    # Resample to weekly and calculate returns
    weekly_prices = close_prices.resample('W').last()
    weekly_returns = weekly_prices.pct_change().dropna()
    
    # Convert to dictionary with string dates and format as percentages
    return {
        "ticker": ticker,
        "weekly_returns": {str(date.date()): f"{round(ret * 100, 2)}%" for date, ret in weekly_returns.items()},
        "total_weeks": len(weekly_returns),
        "average_weekly_return": f"{round(weekly_returns.mean() * 100, 2)}%" if not weekly_returns.empty else "0%"
    }

def calculate_ticker_factors(ticker: str, factor: str):
    if factor == "growth":
        return GrowthFactors(ticker).calc_all()
    elif factor == "value":
        return ValueFactors(ticker).calc_all()
    elif factor == "momentum":
        return MomentumFactors(ticker).calc_all()
    elif factor == "quality":
        return QualityFactors(ticker).calc_all()
    elif factor == "volatility":
        return VolatilityFactors(ticker).calc_all()
    else:
        raise ValueError(f"Unknown factor: {factor}")

def register_industry_tools(agent):
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
