import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Dividend, Ticker
from sqlalchemy import desc

class CalculateTickerReturns:
    def __init__(self, price_data: pd.DataFrame, ticker: str = None):
        # Ensure we have a copy to avoid modifying the original
        self.price_data = price_data.copy()
        self.ticker = ticker
        
        # Ensure price_data has datetime index
        if not isinstance(self.price_data.index, pd.DatetimeIndex):
            if 'date' in self.price_data.columns:
                self.price_data.set_index('date', inplace=True)
            elif 'datetime' in self.price_data.columns:
                self.price_data.set_index('datetime', inplace=True)
        
        # Ensure index is datetime
        if not isinstance(self.price_data.index, pd.DatetimeIndex):
            self.price_data.index = pd.to_datetime(self.price_data.index)
        
        self.dividends = self._fetch_dividends()
    
    def _fetch_dividends(self):
        """Fetches dividend data for the ticker from the database and aligns it with price data dates."""
        if self.price_data.empty or not self.ticker:
            return pd.Series(0.0, index=self.price_data.index)
        
        session = MarketSession()
        try:
            # Get date range from price data
            start_date = self.price_data.index.min().date()
            end_date = self.price_data.index.max().date()
            
            # Query dividends for the ticker within the date range
            dividends = session.query(Dividend).join(Ticker).filter(
                Ticker.ticker == self.ticker.upper(),
                Dividend.date >= start_date,
                Dividend.date <= end_date
            ).order_by(Dividend.date).all()
            
            # Create a series with dividend amounts aligned to price data dates
            dividend_series = pd.Series(0.0, index=self.price_data.index)
            
            for div in dividends:
                # Find all dates in price data that match the dividend date
                mask = self.price_data.index.date == div.date
                matching_indices = self.price_data.index[mask]
                
                if len(matching_indices) > 0:
                    # Use adjDividend if available, otherwise use dividend
                    dividend_amount = div.adjDividend if div.adjDividend is not None else div.dividend
                    # Assign dividend to the first matching date (usually there's only one per day)
                    dividend_series.loc[matching_indices[0]] = dividend_amount
            
            return dividend_series
            
        except Exception as e:
            print(f"Error fetching dividends for {self.ticker}: {e}")
            return pd.Series(0.0, index=self.price_data.index)
        finally:
            session.close()
    
    def calculate_daily_price_returns(self):
        """
        Calculates the daily price return (capital gain/loss), which measures the
        percentage change in the stock's price.
        """
        return self.price_data['close'].pct_change(fill_method=None).dropna()

    def calculate_daily_total_returns(self):
        """
        Calculates the daily total return, which includes both price changes and dividends.
        """
        price_returns = self.calculate_daily_price_returns()
        # The dividend yield is calculated based on the previous day's closing price.
        daily_dividend_yield = self.dividends / self.price_data['close'].shift(1)
        daily_dividend_yield = daily_dividend_yield.fillna(0)
        
        total_returns = price_returns.add(daily_dividend_yield.loc[price_returns.index], fill_value=0)
        
        return total_returns
     
    def calculate_annualized_price_return(self):
        """
        Calculates the compound annualized price return from daily price returns.
        """
        returns = self.calculate_daily_price_returns()
        if returns.empty:
            return 0.0
        
        # Calculate compound annual growth rate
        total_return = (1 + returns).prod() - 1
        days = len(returns)
        if days == 0:
            return 0.0
        
        annualized = (1 + total_return) ** (252/days) - 1
        return annualized

    def calculate_annualized_total_return(self):
        """
        Calculates the compound annualized total return from daily total returns.
        """
        returns = self.calculate_daily_total_returns()
        if returns.empty:
            return 0.0
        
        # Calculate compound annual growth rate
        total_return = (1 + returns).prod() - 1
        days = len(returns)
        if days == 0:
            return 0.0
        
        annualized = (1 + total_return) ** (252/days) - 1
        return annualized

    def calculate_holding_period_return(self):
        """
        Calculates the holding period return, which is the total return
        over the entire period the investment was held.
        """
        if self.price_data.empty:
            return 0.0
        
        start_price = self.price_data['close'].iloc[0]
        end_price = self.price_data['close'].iloc[-1]
        
        total_dividends = self.dividends.sum()

        if start_price is None or start_price == 0:
            return 0.0
        
        holding_return = ((end_price - start_price) + total_dividends) / start_price
        return holding_return

    @staticmethod
    def calculate_real_return(nominal_return: float, inflation_rate: float) -> float:
        """
        Adjusts a nominal return for inflation to provide the real return.
        
        :param nominal_return: The nominal return as a decimal (e.g., 0.08 for 8%).
        :param inflation_rate: The inflation rate as a decimal (e.g., 0.02 for 2%).
        :return: The real return as a decimal.
        """
        return (1 + nominal_return) / (1 + inflation_rate) - 1
    

