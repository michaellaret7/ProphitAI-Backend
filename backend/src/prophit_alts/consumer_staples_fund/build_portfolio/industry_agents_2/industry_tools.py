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
from backend.src.repositories.news_data import get_press_releases, get_stock_news, get_price_target_news
from backend.src.repositories.ratings_data import (
    get_stock_grades_individual,
    get_stock_grades_summary,
    get_ratings,
    get_analyst_recommendations,
    get_price_target_summary,
)
from backend.src.repositories.etf_data import get_etf_info, get_etf_holdings
from backend.src.repositories.transcripts_data import get_earnings_transcripts, get_latest_transcript
from backend.src.repositories.price_data import get_dividends_series
from datetime import datetime, timedelta
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker

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
    """Calculate all factor metrics for a given ticker and factor type."""
    # Growth, Value, and Quality factors take ticker string directly
    if factor in ["growth", "value", "quality"]:
        if factor == "growth":
            return GrowthFactors(ticker).calc_all()
        elif factor == "value":
            return ValueFactors(ticker).calc_all()
        else:  # quality
            return QualityFactors(ticker).calc_all()
    
    # Momentum and Volatility factors need price series
    elif factor in ["momentum", "volatility"]:
        ds = DataService()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=500)  # ~2 years of data
        
        # Get price data for ticker (and SPY for market-relative metrics)
        price_data = ds.get_price_data(ticker, start_date, end_date)
        if price_data is None or price_data.frame.empty:
            return {"error": f"No price data available for {ticker}"}
        
        price_series = price_data.frame['close']
        
        # Get SPY data for both momentum and volatility
        spy_data = ds.get_price_data("SPY", start_date, end_date)
        spy_prices = spy_data.frame['close'] if spy_data and not spy_data.frame.empty else None
        
        if factor == "momentum":
            # Get additional data for momentum calculations
            volume_series = price_data.frame.get('volume', None)
            
            # Get dividends if available
            try:
                divs = ds.get_dividends(ticker, start_date, end_date).series
                divs = divs.reindex(price_series.index).fillna(0.0)
            except Exception:
                divs = None
            
            return MomentumFactors(
                price_series=price_series,
                volume_series=volume_series,
                market_price_series=spy_prices,
                dividends_series=divs
            ).calc_all()
        else:  # volatility
            return VolatilityFactors(price_series, spy_price_series=spy_prices).calc_all()
    
    else:
        raise ValueError(f"Unknown factor: {factor}")

def fetch_repository_data(ticker: str, data_type: str, limit: int | None = None):
    """Route to repository functions based on data_type.

    Supported data_type values:
      - press_releases, stock_news, price_target_news
      - grades_individual, grades_summary, ratings, analyst_recommendations
      - price_target_summary
      - etf_info, etf_holdings
      - earnings_transcripts, latest_transcript
      - dividends_series
    """
    t = (data_type or "").strip().lower()
    now = datetime.now()
    start_news = now - timedelta(days=180)
    start_divs = now - timedelta(days=365)

    if t in ["press_releases", "press-release", "press"]:
        return get_press_releases(ticker, start=start_news, end=now, limit=50, ascending=False)
    if t in ["stock_news", "news"]:
        return get_stock_news(ticker, start=start_news, end=now, limit=50, ascending=False)
    if t in ["price_target_news", "pt_news"]:
        return get_price_target_news(ticker, start=start_news, end=now, limit=50, ascending=False)

    if t in ["grades_individual", "grades_detail"]:
        return get_stock_grades_individual(ticker, start=start_news, end=now)
    if t in ["grades_summary", "grades"]:
        return get_stock_grades_summary(ticker, start=start_news, end=now)
    if t == "ratings":
        return get_ratings(ticker, start=start_news, end=now)
    if t in ["analyst_recommendations", "analyst_recomendations", "recommendations"]:
        return get_analyst_recommendations(ticker, start=start_news, end=now)
    if t == "price_target_summary":
        return get_price_target_summary(ticker)

    if t == "etf_info":
        return get_etf_info(ticker)
    if t == "etf_holdings":
        return get_etf_holdings(ticker)

    if t == "earnings_transcripts":
        # Default last 2 years; honor optional limit for number of transcripts
        return get_earnings_transcripts(
            ticker,
            start_year=now.year - 2,
            end_year=now.year,
            limit=limit,
        )
    if t == "latest_transcript":
        return get_latest_transcript(ticker)

    if t == "dividends_series":
        s = get_dividends_series(ticker, start_divs, now)
        items = [{"date": str(idx.date()), "amount": float(val)} for idx, val in s.items()]
        return {"ticker": ticker.upper(), "count": len(items), "items": items}

    return {"error": f"Unknown data_type: {data_type}"}

def get_eligible_tickers(industry: str):
    """Get the eligible tickers for a given industry."""
    market_session = MarketSession()
    tickers = market_session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > 600_000_000).all()
    market_session.close()
    return [ticker.ticker for ticker in tickers]

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

