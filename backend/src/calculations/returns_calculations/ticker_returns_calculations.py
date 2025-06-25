import pandas as pd
import numpy as np
from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
from backend.src.utils.determine_etf import is_etf_ticker
from datetime import datetime, timedelta

class CalculateTickerReturns:
    def __init__(self, price_data: pd.DataFrame):
        self.price_data = price_data
        self.dividends = pd.Series(0.0, index=self.price_data.index)
    
    def calculate_daily_price_returns(self):
        """
        Calculates the daily price return (capital gain/loss), which measures the
        percentage change in the stock's price.
        """
        return self.price_data['close'].pct_change(fill_method=None).dropna()

    def calculate_daily_total_returns(self):
        """
        Calculates the daily total return, which includes both price changes and dividends.
        NOTE: This currently uses a placeholder for dividends.
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

if __name__ == "__main__":
    ticker = "xlf"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*4)
    
    if is_etf_ticker(ticker):
        price_repo = ETFPriceDataRepository()
        price_data = price_repo.fetch_etf_price_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            interval='1D'
        )
    else:
        price_repo = EquityPriceDataRepository()
        price_data = price_repo.fetch_equity_price_data(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            interval='1D'
        )
    
    if not price_data.empty:
        # Set 'date' as index if it's not already
        if 'date' in price_data.columns:
            price_data['date'] = pd.to_datetime(price_data['date'])
            price_data.set_index('date', inplace=True)

        returns_calculator = CalculateTickerReturns(
            price_data=price_data
        )

        print(returns_calculator.calculate_daily_price_returns())
        print(returns_calculator.calculate_daily_total_returns())
        print(returns_calculator.calculate_annualized_price_return())
        print(returns_calculator.calculate_annualized_total_return())
        print(returns_calculator.calculate_holding_period_return())
        print(returns_calculator.calculate_real_return(returns_calculator.calculate_annualized_total_return(), 0.02))