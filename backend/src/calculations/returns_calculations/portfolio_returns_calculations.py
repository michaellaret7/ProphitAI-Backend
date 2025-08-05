import pandas as pd
import numpy as np
from backend.src.repositories.price_data import get_price_data_daily, get_price_data_15_mins
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

    portfolio_dict = {
        "long_tickers": {
            "CASY": {
                "position": "long",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.1,
                "reasoning": "Record operational momentum, robust FCF growth, disciplined capital allocation, and consistent execution. Defensive growth, positive technicals, and rising analyst targets support a core allocation despite valuation."
            },
            "CELH": {
                "position": "long",
                "industry": "beverages",
                "risk_allocation": 0.1,
                "reasoning": "Exceptional EPS and FCF growth, industry-leading gross margin, clean balance sheet, and secular health/wellness tailwinds. Despite high volatility and valuation, quality and brand momentum justify a core position."
            },
            "ODC": {
                "position": "long",
                "industry": "household_products",
                "risk_allocation": 0.05,
                "reasoning": "Accelerating margin/FCF growth, capital discipline, and strategic mix shift toward high-value segments. Positive technicals, strong balance sheet, and underappreciated re-rating catalysts."
            },
            "ODD": {
                "position": "long",
                "industry": "personal_care_products",
                "risk_allocation": 0.05,
                "reasoning": "Hyper-growth, sector-leading margins, high FCF, asset-light, and net cash. Digital/AI-driven business model, strong brand, and positive analyst/management alignment justify premium multiples."
            },
            "PM": {
                "position": "long",
                "industry": "tobacco",
                "risk_allocation": 0.1,
                "reasoning": "Dominant in smoke-free transformation, best-in-class margins, very strong FCF and dividend, low beta, and secular growth. Recent technical weakness is an opportunity given structural defensiveness."
            },
            "VITL": {
                "position": "long",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Best-in-class margin and growth profile, brand leadership, clean balance sheet, and high compounding potential. Defensive growth, positive sentiment, and analyst support for a core allocation."
            },
            "WMT": {
                "position": "long",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.05,
                "reasoning": "Omni-channel leadership, e-commerce acceleration, strong balance sheet, and defensive core holding. Low volatility, high visibility, and cash returns support inclusion."
            },
            "BJ": {
                "position": "long",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.05,
                "reasoning": "Growth compounder, market share gains, digital innovation, and conservative capital structure. Membership renewal rates and private label strength add conviction."
            },
            "SFM": {
                "position": "long",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.05,
                "reasoning": "Exceptional comp sales/margin expansion, no debt, e-commerce momentum, and disciplined new store pipeline. Health/wellness focus and private label growth reinforce quality."
            },
            "COCO": {
                "position": "long",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Strong brand momentum, high revenue/profitability growth, zero net debt, and international expansion. Category leadership in functional beverages with positive technicals."
            },
            "MNST": {
                "position": "long",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Superior quality, EPS/FCF growth, global brand leadership, and innovation offsetting U.S. share loss. Stretched valuation is offset by fundamentals and positive sentiment."
            },
            "CL": {
                "position": "long",
                "industry": "household_products",
                "risk_allocation": 0.05,
                "reasoning": "Defensive global leader, robust margins, FCF stability, and innovation pipeline. Market share gains and resilience make it a solid stabilizer in the portfolio."
            },
            "IPAR": {
                "position": "long",
                "industry": "personal_care_products",
                "risk_allocation": 0.05,
                "reasoning": "Resilient growth, margin expansion, strong brand launches, prudent cost control, and healthy cash flow/dividend. Niche leadership with conservative guidance."
            },
            "TPB": {
                "position": "long",
                "industry": "tobacco",
                "risk_allocation": 0.05,
                "reasoning": "Modern oral nicotine disruptor, accelerating market share, positive FCF, and upward guidance. Margin compression risk offset by execution and momentum."
            },
            "DOLE": {
                "position": "long",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Turnaround/value play, improving margins, deleveraging, cost discipline, and capital returns. Execution in fresh/value-added supports inclusion."
            },
            "PPC": {
                "position": "long",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Diversified protein, positive growth/margins, strong cash flow, and branded/value-added growth. Healthy capital structure and operational execution."
            },
            "INGR": {
                "position": "long",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Defensive, high-quality operator, margin expansion, positive EPS/cash flow, and cost discipline. Diversified portfolio and strong analyst sentiment."
            }
        },
        "short_tickers": {
            "WBA": {
                "position": "short",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.05,
                "reasoning": "Persistent negative comps, margin pressure, high leverage, legal/operational drag, and dividend risk. Structural headwinds make it a high-conviction short."
            },
            "ANDE": {
                "position": "short",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.05,
                "reasoning": "Margin compression, negative earnings, poor return metrics, high volatility, and weak FCF. Deteriorating fundamentals warrant a tactical short."
            },
            "TGT": {
                "position": "short",
                "industry": "distribution_and_retail",
                "risk_allocation": 0.02,
                "reasoning": "Declining comps, margin/inventory pressure, high leverage, and weak FCF. Cautious guidance and execution risk add to short case."    
            },
            "STZ": {
                "position": "short",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Negative momentum, core beer headwinds, reduced growth guidance, expensive valuation, and high leverage. Analyst downgrades and cautious management reinforce conviction."
            },
            "PEP": {
                "position": "short",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Negative momentum, revenue/FCF contraction, high valuation, margin pressure, high leverage, and cautious analyst sentiment."
            },
            "SAM": {
                "position": "short",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Severe negative momentum, category headwinds, weak cash generation, and high valuation. Sentiment/price targets support further downside."    
            },
            "MGPI": {
                "position": "short",
                "industry": "beverages",
                "risk_allocation": 0.05,
                "reasoning": "Cyclical downturn, revenue/profit declines, execution/legal risk, and negative technicals. High-conviction fundamental and technical short."  
            },
            "ENR": {
                "position": "short",
                "industry": "household_products",
                "risk_allocation": 0.05,
                "reasoning": "Negative momentum, deteriorating revenue/FCF, excessive leverage, margin compression, and litigation risk."
            },
            "SPB": {
                "position": "short",
                "industry": "household_products",
                "risk_allocation": 0.05,
                "reasoning": "Severe negative momentum, declining revenue/EPS, margin compression, weak technical/fundamental profile."
            },
            "COTY": {
                "position": "short",
                "industry": "personal_care_products",
                "risk_allocation": 0.05,
                "reasoning": "Severe negative momentum, weak operational metrics, persistent declines, high leverage, tight liquidity, and negative sentiment."
            },
            "KVUE": {
                "position": "short",
                "industry": "personal_care_products",
                "risk_allocation": 0.05,
                "reasoning": "Negative organic growth, margin compression, FCF deterioration, high tariffs, high valuation, and cautious management/analyst stance."        
            },
            "KLG": {
                "position": "short",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Rallying on momentum despite negative FCF, persistent volume declines, high leverage, and extreme valuation. Weak fundamentals."
            },
            "JJSF": {
                "position": "short",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Margin compression, negative revenue/FCF growth, persistent volume headwinds, and high valuation. Fundamentals do not justify price."
            },
            "SEB": {
                "position": "short",
                "industry": "food_products",
                "risk_allocation": 0.05,
                "reasoning": "Recent price momentum unsupported by operational performance, shrinking revenue/EPS, negative FCF, and thin margins. Strong mean-reversion short."
            }
        }
    }

    tickers_weights = {}
    
    # Add long positions with positive weights
    for ticker, info in portfolio_dict["long_tickers"].items():
        tickers_weights[ticker] = info["risk_allocation"]
    
    # Add short positions with negative weights
    for ticker, info in portfolio_dict["short_tickers"].items():
        tickers_weights[ticker] = -info["risk_allocation"]

    print(tickers_weights)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*4)
    
    portfolio_calculator = CalculatePortfolioReturns(
        tickers_weights=tickers_weights,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    # Create and show portfolio performance plot
    portfolio_calculator.plot_portfolio_performance()

