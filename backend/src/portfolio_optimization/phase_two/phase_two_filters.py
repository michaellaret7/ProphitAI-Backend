import json
from datetime import datetime, timedelta
from backend.src.utils.determine_etf import is_etf_asset_class
from backend.src.repositories.market_data.cached_ticker_repository import get_cached_ticker_data
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)

lookback_years = 1.5

class PhaseTwoFilters:
    def __init__(self, asset_class):
        self.asset_class = asset_class
        self.minimum_daily_average_volume = 10_000
        self.is_etf = is_etf_asset_class(self.asset_class)
        with open('backend/src/data/database/database_schemas.json', 'r') as f:
            self.database_schemas = json.load(f)
        
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Convert dates to ISO format strings for caching (hashable)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Use the cached function
        data = get_cached_ticker_data(
            ticker=ticker,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d"
        )
        
        if data is None:
            return None

        return data
    
    def _calculate_composite_score(self, tickers):
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
            tickers (list): List of ticker symbols to analyze
            
        Returns:
            list: Top 10 tickers sorted by composite score (highest to lowest)
        """
        
        ticker_scores = {}
        metrics_data = {}
        
        # Collect metrics for all tickers
        for ticker in tickers:
            try:
                # Calculate performance metrics using existing class
                metrics_calc = TickerPerformanceMetrics(ticker)
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
        
        # Calculate composite score using equal weights
        # Research shows equal weighting often outperforms complex weighting schemes
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
    
    def get_asset_class_tickers(self):
        if self.asset_class == "cash":
            return []

        for sector_data in self.database_schemas.values():
            if "schemas" in sector_data:
                for schema_data in sector_data["schemas"].values():
                    if "tables" in schema_data and self.asset_class in schema_data["tables"]:
                        return schema_data["tables"][self.asset_class].get("tickers", [])
        
        logger.warning(f"No tickers found for asset class: {self.asset_class}")
        return []

    def _calculate_daily_average_volume(self, equity_data):
        total_volume = equity_data["volume"].sum()
        number_of_trading_days = len(equity_data)

        if number_of_trading_days == 0:
            return 0
            
        daily_average_volume = total_volume / number_of_trading_days
        return daily_average_volume

    def filter_tickers(self, tickers):
        filtered_tickers = []
        for ticker in tickers:

            data = self._get_ticker_data(ticker) # --> get the data for the ticker

            if data is not None and not data.empty:
                volume = self._calculate_daily_average_volume(data) # --> calculate the daily average volume for the ticker

                if volume > self.minimum_daily_average_volume:
                    filtered_tickers.append(ticker)

            else:
                logger.warning(f"No data returned for ticker '{ticker}', it will be skipped.")

        logger.info(f"Filtered tickers: {filtered_tickers}")

        filtered_tickers = self._calculate_composite_score(filtered_tickers) # --> calculate the composite score for the tickers and return the top 10

        return filtered_tickers
    


if __name__ == "__main__":
    
    filters = PhaseTwoFilters("passenger_airlines")
    tickers = filters.get_asset_class_tickers()
    filtered_tickers = filters.filter_tickers(tickers)
    logger.info(f"Filtered tickers: {filtered_tickers}")