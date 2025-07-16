import pandas as pd
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from datetime import datetime, timedelta
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

class CalculatePortfolioReturns:
    def __init__(self, tickers_weights: Dict[str, float], start_date: str, end_date: str):
        """
        Initialize portfolio returns calculator.
        
        :param tickers_weights: Dictionary with tickers as keys and weights as values
        :param start_date: Start date for the analysis
        :param end_date: End date for the analysis
        """
        self.tickers_weights = tickers_weights
        self.start_date = start_date
        self.end_date = end_date
        self.ticker_calculators = {}
        self._initialize_ticker_calculators()
    
    def _fetch_ticker_data(self, ticker: str):
        """Helper function to fetch data for a single ticker."""
        ticker_upper = ticker.upper()
        
        price_data = get_price_data_daily(
            ticker=ticker_upper,
            start_date=datetime.strptime(self.start_date, '%Y-%m-%d'),
            end_date=datetime.strptime(self.end_date, '%Y-%m-%d')
        )
        
        return ticker, ticker_upper, price_data
    
    def _initialize_ticker_calculators(self):
        """Initialize CalculateTickerReturns for each ticker in the portfolio using concurrent fetching."""
        # Use ThreadPoolExecutor to fetch data concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all ticker data fetch tasks
            future_to_ticker = {
                executor.submit(self._fetch_ticker_data, ticker): ticker 
                for ticker in self.tickers_weights.keys()
            }
            
            # Process completed futures as they finish
            for future in as_completed(future_to_ticker):
                try:
                    ticker, ticker_upper, price_data = future.result()
                    
                    if price_data is not None and not price_data.empty:
                        # Initialize with both price_data and ticker
                        self.ticker_calculators[ticker] = CalculateTickerReturns(price_data, ticker_upper)
                except Exception as e:
                    ticker = future_to_ticker[future]
                    print(f"Error fetching data for {ticker}: {e}")
    
    def calculate_daily_price_returns(self):
        """
        Calculates the daily price returns for the portfolio by weighting individual ticker returns.
        """
        portfolio_returns = pd.Series(dtype=float)
        
        for ticker, weight in self.tickers_weights.items():
            if ticker in self.ticker_calculators:
                ticker_returns = self.ticker_calculators[ticker].calculate_daily_price_returns()
                weighted_returns = ticker_returns * weight
                
                if portfolio_returns.empty:
                    portfolio_returns = weighted_returns
                else:
                    portfolio_returns = portfolio_returns.add(weighted_returns, fill_value=0)
        
        return portfolio_returns
    
    def calculate_daily_total_returns(self):
        """
        Calculates the daily total returns for the portfolio by weighting individual ticker returns.
        """
        portfolio_returns = pd.Series(dtype=float)
        
        for ticker, weight in self.tickers_weights.items():
            if ticker in self.ticker_calculators:
                ticker_returns = self.ticker_calculators[ticker].calculate_daily_total_returns()
                weighted_returns = ticker_returns * weight
                
                if portfolio_returns.empty:
                    portfolio_returns = weighted_returns
                else:
                    portfolio_returns = portfolio_returns.add(weighted_returns, fill_value=0)
        
        return portfolio_returns
    
    def calculate_annualized_price_return(self):
        """
        Calculates the compound annualized price return for the portfolio.
        """
        daily_returns = self.calculate_daily_price_returns()
        if daily_returns.empty:
            return 0.0
        
        # Calculate compound annual growth rate
        total_return = (1 + daily_returns).prod() - 1
        days = len(daily_returns)
        if days == 0:
            return 0.0
        
        annualized = (1 + total_return) ** (252/days) - 1
        return annualized
    
    def calculate_annualized_total_return(self):
        """
        Calculates the compound annualized total return for the portfolio.
        """
        daily_returns = self.calculate_daily_total_returns()
        if daily_returns.empty:
            return 0.0
        
        # Calculate compound annual growth rate
        total_return = (1 + daily_returns).prod() - 1
        days = len(daily_returns)
        if days == 0:
            return 0.0
        
        annualized = (1 + total_return) ** (252/days) - 1
        return annualized
    
    def calculate_holding_period_return(self):
        """
        Calculates the holding period return for the portfolio.
        """
        portfolio_hpr = 0.0
        
        for ticker, weight in self.tickers_weights.items():
            if ticker in self.ticker_calculators:
                ticker_hpr = self.ticker_calculators[ticker].calculate_holding_period_return()
                portfolio_hpr += ticker_hpr * weight
        
        return portfolio_hpr
    
    @staticmethod
    def calculate_real_return(nominal_return: float, inflation_rate: float) -> float:
        """
        Adjusts a nominal return for inflation to provide the real return.
        
        :param nominal_return: The nominal return as a decimal (e.g., 0.08 for 8%).
        :param inflation_rate: The inflation rate as a decimal (e.g., 0.02 for 2%).
        :return: The real return as a decimal.
        """
        return (1 + nominal_return) / (1 + inflation_rate) - 1

if __name__ == "__main__":
    # Example usage
    tickers_weights = {
        "xlf": 0.2,
        "spy": 0.2,
        "qqq": 0.2,
        "iwm": 0.1,
        "nvda": 0.3,
        "ba": -0.2,
        "mrna": -0.2,
        "alb": -0.2
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*2)
    
    portfolio_calculator = CalculatePortfolioReturns(
        tickers_weights=tickers_weights,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    print(portfolio_calculator.calculate_daily_total_returns().head())
    print(portfolio_calculator.calculate_daily_price_returns().head())
    print(portfolio_calculator.calculate_annualized_total_return())
    print(portfolio_calculator.calculate_annualized_price_return())
    print(portfolio_calculator.calculate_holding_period_return())
    print(portfolio_calculator.calculate_real_return(portfolio_calculator.calculate_annualized_total_return(), 0.02))

