"""
Capture ratio calculations for stress testing.
"""
import pandas as pd
import numpy as np
from backend.src.calculations.performance_calculations.portfolio_performance_calculations import PortfolioPerformanceCalculations
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics

def calculate_portfolio_capture_ratio(portfolio_returns: pd.Series, spy_returns: pd.Series):
    """
    Calculate portfolio upside/downside capture ratio against SPY.
    
    :param portfolio_returns: Portfolio returns series
    :param spy_returns: SPY benchmark returns series
    :return: Dictionary with capture metrics
    """
    if portfolio_returns.empty or spy_returns.empty:
        return "No portfolio or SPY data available"
    
    # Use the portfolio performance calculations method
    perf_calc = PortfolioPerformanceCalculations({}, '', '')  # Dummy initialization
    capture_metrics = perf_calc.calculate_upside_downside_capture(
        fund_returns=portfolio_returns,
        benchmark_returns=spy_returns
    )
    
    # Convert all numpy floats to Python floats
    for key, value in capture_metrics.items():
        if isinstance(value, (int, float)) and not np.isnan(value):
            capture_metrics[key] = float(round(value, 3))
    
    return capture_metrics

def calculate_ticker_capture_ratios(ticker_returns: pd.DataFrame, benchmark_ticker: str = 'SPY'):
    """
    Calculate individual ticker capture ratios for a stress scenario.
    
    :param ticker_returns: DataFrame of ticker returns
    :param benchmark_ticker: Ticker to use as benchmark (default: 'SPY')
    :return: Dictionary with capture metrics for each ticker
    """
    if ticker_returns.empty:
        return "No ticker data available"
    
    # Use the ticker performance calculations method
    ticker_capture_ratios = TickerPerformanceMetrics.calculate_ticker_capture_ratios(
        ticker_returns_df=ticker_returns,
        benchmark_ticker=benchmark_ticker
    )

    for ticker, capture_ratio in ticker_capture_ratios.items():
        if isinstance(capture_ratio, dict):
            for key, value in capture_ratio.items():
                if isinstance(value, (int, float)) and not np.isnan(value):
                    ticker_capture_ratios[ticker][key] = float(round(value, 3))

    if 'SPY' in ticker_capture_ratios:
        del ticker_capture_ratios['SPY']

    return ticker_capture_ratios

if __name__ == "__main__":
    from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns
    from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
    from backend.src.repositories.price_data import get_price_data_daily
    from datetime import datetime

    # Define portfolio with equal weights
    tickers_weights = {
        'SPY': 0.33,
        'AAPL': 0.33,
        'MSFT': 0.34
    }

    # Date parameters
    start_date = '2024-01-01'
    end_date = '2025-01-02'
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d')

    # Initialize portfolio returns calculator with proper parameters
    portfolio_calculator = CalculatePortfolioReturns(
        tickers_weights=tickers_weights, 
        start_date=start_date, 
        end_date=end_date
    )

    # Calculate portfolio returns
    portfolio_returns = portfolio_calculator.calculate_daily_total_returns()
    
    # Create a DataFrame with all ticker returns
    all_ticker_returns = pd.DataFrame()
    
    for ticker in ['SPY', 'AAPL', 'MSFT']:
        # Fetch price data for each ticker
        price_data = get_price_data_daily(
            ticker=ticker,
            start_date=start_datetime,
            end_date=end_datetime
        )
        
        # Calculate returns for each ticker
        ticker_calc = CalculateTickerReturns(
            price_data=price_data,
            ticker=ticker
        )
        
        # Add to DataFrame
        all_ticker_returns[ticker] = ticker_calc.calculate_daily_total_returns()
    
    # Get SPY returns for benchmark comparison
    spy_returns = all_ticker_returns['SPY']
    
    print("Portfolio Returns:")
    print(portfolio_returns.head())
    print(f"\nPortfolio Annualized Return: {portfolio_calculator.calculate_annualized_total_return():.2%}")
    
    print("\n" + "="*60)
    print("Portfolio Capture Ratios vs SPY:")
    print(calculate_portfolio_capture_ratio(portfolio_returns, spy_returns))
    
    print("\n" + "="*60)
    print("Individual Ticker Capture Ratios vs SPY:")
    print(calculate_ticker_capture_ratios(all_ticker_returns, benchmark_ticker='SPY'))