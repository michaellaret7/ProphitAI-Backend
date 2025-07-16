import json
from datetime import datetime, timedelta
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import Ticker
from backend.src.utils.determine_etf import is_etf_asset_class
from backend.src.repositories.price_data import get_price_data_daily
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

lookback_years = 2

class PhaseTwoFilters:
    def __init__(self, asset_class):
        self.asset_class = asset_class
        self.minimum_daily_average_volume = 25_000
        self.is_etf = is_etf_asset_class(self.asset_class)
        
        # Pre-fetch market data (SPY) once during initialization
        self.spy_data = self._get_ticker_data('SPY')
        if self.spy_data is not None:
            spy_calculator = CalculateTickerReturns(self.spy_data, 'SPY')
            self.market_returns = spy_calculator.calculate_daily_total_returns()
        else:
            self.market_returns = None
        
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Use the new function with datetime objects
        data = get_price_data_daily(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
        )
        
        if data is None:
            return None

        return data
    
    # MOVE THIS TO CALCULATIONS FOLDER AND REVIEW THE CALCULATIONS (FIND THE BEST WAY TO DO THIS)
    def _calculate_composite_score(self, tickers_with_data):
        """
        Calculate composite scores for tickers using multiple performance metrics.
        
        Based on quantitative finance research, this method uses a simple but effective
        approach combining multiple factors with equal weights after normalization.
        
        The composite score combines:
        - Return metrics: Sharpe ratio, Sortino ratio, Calmar ratio
        - Risk-adjusted returns: Omega ratio, Information ratio
        - Downside protection: Max drawdown (inverted), downside capture (inverted)
        - Consistency: Win rate, profit factor
        
        Args:
            tickers_with_data (dict): Dictionary mapping ticker symbols to their price data
            
        Returns:
            list: Top 10 tickers sorted by composite score (highest to lowest)
        """
        
        ticker_scores = {}
        metrics_data = {}
        
        # Collect metrics for all tickers
        for ticker, price_data in tickers_with_data.items():
            try:
                # Calculate performance metrics using existing class with pre-fetched data
                metrics_calc = TickerPerformanceMetrics(ticker, price_data=price_data, market_returns=self.market_returns)
                metrics = metrics_calc.calc_all()
                
                # Store metrics for normalization
                metrics_data[ticker] = {
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'sortino_ratio': metrics.sortino_ratio,
                    'calmar_ratio': metrics.calmar_ratio,
                    'omega_ratio': metrics.omega_ratio,
                    'information_ratio': metrics.information_ratio,
                    'max_drawdown': metrics.max_drawdown,  # Will be inverted
                    'downside_capture': metrics.downside_capture,  # Will be inverted
                    'win_rate': metrics.win_rate,
                    'profit_factor': metrics.profit_factor
                }
                
            except Exception as e:
                logger.warning(f"Failed to calculate metrics for {ticker}: {str(e)}")
                continue
        
        if not metrics_data:
            logger.error("No valid metrics calculated for any ticker")
            return []
        
        # Convert to DataFrame for easier manipulation
        df = pd.DataFrame.from_dict(metrics_data, orient='index')
        
        # Handle infinite values and NaNs
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # For each metric, replace NaN with the median value
        for col in df.columns:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
        
        # Normalize metrics using z-score normalization
        normalized_df = pd.DataFrame(index=df.index)
        
        for col in df.columns:
            # Calculate z-scores
            mean = df[col].mean()
            std = df[col].std()
            
            if std == 0:
                # If no variation, all scores are 0
                normalized_df[col] = 0
            else:
                if col in ['max_drawdown', 'downside_capture']:
                    # For these metrics, lower is better, so invert the z-score
                    normalized_df[col] = -(df[col] - mean) / std
                else:
                    # For other metrics, higher is better
                    normalized_df[col] = (df[col] - mean) / std
        
        composite_scores = normalized_df.mean(axis=1)
        
        # Sort tickers by composite score (descending)
        sorted_tickers = composite_scores.sort_values(ascending=False)
        
        # Log the results
        logger.info(f"Calculated composite scores for {len(sorted_tickers)} tickers")
        logger.info(f"Top 10 tickers by composite score:")
        for i, (ticker, score) in enumerate(sorted_tickers.head(10).items()):
            logger.info(f"  {i+1}. {ticker}: {score:.4f}")
        
        # Return top 10 tickers
        return sorted_tickers.head(10).index.tolist()
    
    def _calculate_daily_average_volume(self, equity_data): # --> calculate the daily average volume for a given ticker
        total_volume = equity_data["volume"].sum()
        number_of_trading_days = len(equity_data)

        if number_of_trading_days == 0:
            return 0
            
        daily_average_volume = total_volume / number_of_trading_days
        return daily_average_volume
    
    def get_asset_class_tickers(self): # --> extract the tickers from within a given asset class
        if self.asset_class == "cash":
            return []

        session = MarketSession()
        tickers = session.query(Ticker).filter(Ticker.sector == self.asset_class or Ticker.industry == self.asset_class or Ticker.sub_industry == self.asset_class).all()
        session.close()
        tickers = [ticker.ticker for ticker in tickers]

        return tickers

    def filter_tickers(self, tickers): # --> filter the tickers based on the daily average volume and the composite score (this is the main function that is called)
        # Dictionary to store tickers with their data
        tickers_with_data = {}
        
        for ticker in tickers:
            data = self._get_ticker_data(ticker) # --> get the data for the ticker

            if data is not None and not data.empty:
                volume = self._calculate_daily_average_volume(data) # --> calculate the daily average volume for the ticker

                if volume > self.minimum_daily_average_volume:
                    # Store the ticker with its data for later use
                    tickers_with_data[ticker] = data

            else:
                logger.warning(f"No data returned for ticker '{ticker}', it will be skipped.")

        logger.info(f"Filtered tickers: {list(tickers_with_data.keys())}")

        # Pass the tickers with their pre-fetched data
        filtered_tickers_sorted = self._calculate_composite_score(tickers_with_data) # --> calculate the composite score for the tickers and return the top 10

        # Return both the sorted ticker list and the data dictionary
        return filtered_tickers_sorted, {ticker: tickers_with_data[ticker] for ticker in filtered_tickers_sorted}

if __name__ == "__main__":
    filters = PhaseTwoFilters("passenger_airlines")
    tickers = filters.get_asset_class_tickers()
    logger.info(f"Tickers: {tickers}")
    filtered_tickers, tickers_with_data = filters.filter_tickers(tickers)
    logger.info(f"Filtered tickers: {filtered_tickers}")