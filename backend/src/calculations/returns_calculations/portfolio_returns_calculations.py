import pandas as pd
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from datetime import datetime, timedelta
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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
    
    def plot_portfolio_performance(self, save_path: str = None):
        """
        Creates a comprehensive plot of portfolio performance including daily returns and cumulative returns.
        
        :param save_path: Optional path to save the plot. If None, displays the plot.
        """
        # Get daily returns
        daily_returns = self.calculate_daily_total_returns()
        
        if daily_returns.empty:
            print("No data available for plotting")
            return
        
        # Calculate cumulative returns
        cumulative_returns = (1 + daily_returns).cumprod() - 1
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Plot 1: Cumulative Returns
        ax1.plot(cumulative_returns.index, cumulative_returns * 100, 
                linewidth=2, color='#2E86AB', label='Cumulative Returns')
        ax1.set_title('Portfolio Cumulative Returns', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Cumulative Return (%)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Format x-axis dates
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Plot 2: Daily Returns
        ax2.plot(daily_returns.index, daily_returns * 100, 
                linewidth=1, color='#A23B72', alpha=0.7, label='Daily Returns')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.set_title('Portfolio Daily Returns', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Daily Return (%)', fontsize=12)
        ax2.set_xlabel('Date', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        
        # Format x-axis dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        # Add performance metrics as text
        total_return = round(self.calculate_annualized_total_return() * 100, 2)
        holding_return = round(self.calculate_holding_period_return() * 100, 2)
        real_return = round(self.calculate_real_return(self.calculate_annualized_total_return(), 0.02) * 100, 2)
        
        metrics_text = f"""Performance Metrics:
        Annualized Total Return: {total_return}%
        Holding Period Return: {holding_return}%
        Real Return (adj. for 2% inflation): {real_return}%"""
        
        fig.text(0.02, 0.02, metrics_text, fontsize=10, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.7))
        
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.15)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()

if __name__ == "__main__":
    # Example usage
    from backend.src.db.core.db_config import ProphitAltsSession
    from backend.src.db.core.prophit_alts_models import FundInitialPosition, PositionType

    session = ProphitAltsSession()
    positions = session.query(FundInitialPosition).filter(FundInitialPosition.fund_name == "consumer_staples_fund").all()
    tickers_weights = {}

    for position in positions:
        if position.position == PositionType.SHORT:
            tickers_weights[position.ticker_name] = position.risk_allocation * -1
        else:
            tickers_weights[position.ticker_name] = position.risk_allocation
    
    print(sum(tickers_weights.values()))

    session.close()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*4)
    
    portfolio_calculator = CalculatePortfolioReturns(
        tickers_weights=tickers_weights,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    # Create and show portfolio performance plot
    portfolio_calculator.plot_portfolio_performance()

