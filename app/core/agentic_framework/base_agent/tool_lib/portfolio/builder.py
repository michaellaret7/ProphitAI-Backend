from app.utils.gpt_parser import canonical_portfolio
from app.core.calculations.portfolio.build.builder import CorrelationPortfolioBuilder
from app.core.calculations.core import DataService
from datetime import datetime, timedelta

def build_portfolio(portfolio_dict: any):
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
        return f"Error parsing portfolio: {str(e)}"

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
        return f"Cannot build portfolio - {'; '.join(error_msg)}. Please use only tickers with available price data."

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
        return f"Portfolio build failed: {built_portfolio['error']}"
    
    if "status" in built_portfolio and built_portfolio["status"] == "success":
        if "final_portfolio" in built_portfolio:
            return built_portfolio["final_portfolio"]
        else:
            return "Error: Build succeeded but final_portfolio not found in result"
    
    # If we get here, something unexpected happened
    return f"Unexpected result structure: {list(built_portfolio.keys())}"