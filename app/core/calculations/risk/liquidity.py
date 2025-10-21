"""
Liquidity scoring system for risk assessment.

This module implements a comprehensive liquidity scoring framework based on 
institutional best practices, combining market microstructure metrics with 
fundamental indicators to assess asset liquidity risk.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, Optional, Union, Tuple
from datetime import datetime, timedelta
from app.utils.time_utils import get_current_utc_time
import logging

logger = logging.getLogger(__name__)


class LiquidityCalculator:
    """Calculate liquidity metrics following institutional standards."""
    
    # Market cap thresholds (in millions) for liquidity classification
    MARKET_CAP_TIERS = {
        'mega': 200_000,    # > $200B
        'large': 10_000,    # $10B - $200B  
        'mid': 2_000,       # $2B - $10B
        'small': 300,       # $300M - $2B
        'micro': 50,        # $50M - $300M
        'nano': 0           # < $50M
    }
    
    # Liquidity score weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        'amihud_ratio': 0.20,      # Price impact measure
        'roll_spread': 0.15,       # Transaction cost proxy
        'turnover_ratio': 0.20,    # Trading activity
        'dollar_volume': 0.25,     # Absolute liquidity
        'high_low_spread': 0.10,   # Bid-ask proxy
        'market_cap_score': 0.10   # Size-based liquidity
    }
    
    @staticmethod
    def amihud_illiquidity_ratio(
        daily_returns: pd.Series,
        daily_volume_dollars: pd.Series,
        lookback_days: int = 30
    ) -> float:
        """
        Calculate Amihud (2002) illiquidity ratio.
        Measures price impact per dollar traded.
        Lower values = higher liquidity.
        
        Formula: Mean(|Return| / Dollar_Volume)
        """
        if daily_returns.empty or daily_volume_dollars.empty:
            return np.nan
            
        # Align series and use recent data
        df = pd.concat([
            daily_returns.abs(),
            daily_volume_dollars
        ], axis=1).dropna().tail(lookback_days)
        
        if df.empty:
            return np.nan
            
        # Avoid division by zero
        df.columns = ['abs_return', 'dollar_volume']
        df = df[df['dollar_volume'] > 0]
        
        if df.empty:
            return np.nan
            
        # Calculate ratio (multiply by 1e6 for readability)
        ratio = (df['abs_return'] / df['dollar_volume']) * 1e6
        return float(ratio.mean())
    
    @staticmethod
    def roll_spread(
        close_prices: pd.Series,
        lookback_days: int = 30
    ) -> float:
        """
        Calculate Roll (1984) effective spread estimator.
        Estimates bid-ask spread from price changes.
        Lower values = tighter spreads = higher liquidity.
        
        Formula: 2 * sqrt(-cov(price_change_t, price_change_t-1))
        """
        if close_prices.empty or len(close_prices) < 3:
            return np.nan
            
        # Use recent data
        prices = close_prices.tail(lookback_days + 1)
        price_changes = prices.pct_change().dropna()
        
        if len(price_changes) < 2:
            return np.nan
            
        # Calculate serial covariance
        cov = price_changes.cov(price_changes.shift(1))
        
        if cov >= 0:
            # Positive covariance indicates trending, not mean reversion
            # Use high-low spread as fallback
            return np.nan
            
        # Roll spread estimate (as percentage)
        spread = 2 * np.sqrt(-cov) * 100
        return float(spread)
    
    @staticmethod
    def turnover_ratio(
        daily_volume: pd.Series,
        shares_outstanding: float,
        lookback_days: int = 30
    ) -> float:
        """
        Calculate average daily turnover ratio.
        Measures trading activity relative to float.
        Higher values = higher liquidity.
        
        Formula: Mean(Daily_Volume / Shares_Outstanding)
        """
        if daily_volume.empty or shares_outstanding <= 0:
            return np.nan
            
        recent_volume = daily_volume.tail(lookback_days)
        if recent_volume.empty:
            return np.nan
            
        # Calculate daily turnover and get average (as percentage)
        daily_turnover = (recent_volume / shares_outstanding) * 100
        return float(daily_turnover.mean())
    
    @staticmethod
    def average_dollar_volume(
        close_prices: pd.Series,
        daily_volume: pd.Series,
        lookback_days: int = 30
    ) -> float:
        """
        Calculate average daily dollar volume.
        Direct measure of trading liquidity.
        Higher values = higher liquidity.
        """
        if close_prices.empty or daily_volume.empty:
            return np.nan
            
        # Align and calculate dollar volume
        df = pd.concat([close_prices, daily_volume], axis=1).dropna().tail(lookback_days)
        if df.empty:
            return np.nan
            
        df.columns = ['close', 'volume']
        dollar_volume = df['close'] * df['volume']
        
        return float(dollar_volume.mean())
    
    @staticmethod
    def high_low_spread(
        high_prices: pd.Series,
        low_prices: pd.Series,
        close_prices: pd.Series,
        lookback_days: int = 30
    ) -> float:
        """
        Calculate Corwin-Schultz high-low spread estimator.
        Proxy for bid-ask spread using high-low prices.
        Lower values = higher liquidity.
        
        Returns spread as percentage of price.
        """
        if high_prices.empty or low_prices.empty or close_prices.empty:
            return np.nan
            
        # Align series
        df = pd.concat([
            high_prices,
            low_prices,
            close_prices
        ], axis=1).dropna().tail(lookback_days)
        
        if df.empty:
            return np.nan
            
        df.columns = ['high', 'low', 'close']
        
        # Simple high-low spread as percentage of close
        spread = ((df['high'] - df['low']) / df['close']) * 100
        return float(spread.mean())
    
    @staticmethod
    def market_cap_liquidity_score(market_cap: float) -> float:
        """
        Assign liquidity score based on market cap tier.
        Larger cap = higher liquidity score.
        
        Returns: Score between 0 and 1
        """
        if pd.isna(market_cap) or market_cap <= 0:
            return 0.0
            
        # Convert to millions for comparison
        market_cap_millions = market_cap / 1e6
        
        # Assign score based on tier
        if market_cap_millions >= LiquidityCalculator.MARKET_CAP_TIERS['mega']:
            return 1.0
        elif market_cap_millions >= LiquidityCalculator.MARKET_CAP_TIERS['large']:
            return 0.85
        elif market_cap_millions >= LiquidityCalculator.MARKET_CAP_TIERS['mid']:
            return 0.70
        elif market_cap_millions >= LiquidityCalculator.MARKET_CAP_TIERS['small']:
            return 0.50
        elif market_cap_millions >= LiquidityCalculator.MARKET_CAP_TIERS['micro']:
            return 0.30
        else:
            return 0.15
    
    @staticmethod
    def calculate_composite_score(
        metrics: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
        higher_is_better: Optional[Dict[str, bool]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate composite liquidity score from individual metrics.
        
        Args:
            metrics: Dictionary of calculated liquidity metrics
            weights: Custom weights for each metric (must sum to 1.0)
            higher_is_better: Dict indicating if higher values mean better liquidity
            
        Returns:
            Tuple of (composite_score, normalized_metrics)
        """
        if not metrics:
            return np.nan, {}
            
        # Use default weights if not provided
        if weights is None:
            weights = LiquidityCalculator.DEFAULT_WEIGHTS
            
        # Define which metrics have inverse relationship with liquidity
        if higher_is_better is None:
            higher_is_better = {
                'amihud_ratio': False,      # Lower is better
                'roll_spread': False,        # Lower is better
                'turnover_ratio': True,      # Higher is better
                'dollar_volume': True,       # Higher is better
                'high_low_spread': False,    # Lower is better
                'market_cap_score': True     # Higher is better
            }
        
        # Normalize metrics to 0-1 scale based on trading liquidity standards
        normalized = {}
        for metric_name, value in metrics.items():
            if pd.isna(value) or metric_name not in weights:
                continue
                
            # Trading liquidity-specific normalization
            if metric_name == 'market_cap_score':
                # Already normalized
                normalized[metric_name] = value
                
            elif metric_name == 'dollar_volume':
                # Dollar volume thresholds based on real market liquidity tiers
                # Ultra-liquid (SPY tier): $20B+ = 0.95-1.00
                # Mega-liquid (AAPL/NVDA): $5-20B = 0.90-0.95
                # Very liquid (S&P 500): $500M-5B = 0.75-0.90
                # Liquid: $50-500M = 0.60-0.75
                # Moderate: $10-50M = 0.40-0.60
                # Low: $1-10M = 0.20-0.40
                # Illiquid: <$1M = 0-0.20
                if value <= 0:
                    normalized[metric_name] = 0
                elif value < 1e6:  # < $1M - Illiquid
                    normalized[metric_name] = value / 1e6 * 0.20
                elif value < 1e7:  # $1M - $10M - Low liquidity
                    normalized[metric_name] = 0.20 + (value - 1e6) / (1e7 - 1e6) * 0.20
                elif value < 5e7:  # $10M - $50M - Moderate
                    normalized[metric_name] = 0.40 + (value - 1e7) / (5e7 - 1e7) * 0.20
                elif value < 5e8:  # $50M - $500M - Liquid
                    normalized[metric_name] = 0.60 + (value - 5e7) / (5e8 - 5e7) * 0.15
                elif value < 5e9:  # $500M - $5B - Very liquid
                    normalized[metric_name] = 0.75 + (value - 5e8) / (5e9 - 5e8) * 0.15
                elif value < 2e10:  # $5B - $20B - Mega liquid
                    normalized[metric_name] = 0.90 + (value - 5e9) / (2e10 - 5e9) * 0.05
                else:  # $20B+ - Ultra liquid (SPY tier)
                    # Logarithmic scale above $20B
                    normalized[metric_name] = min(0.95 + np.log10(value / 2e10) * 0.02, 1.0)
                    
            elif metric_name == 'amihud_ratio':
                # Amihud: Lower is better, 0 is perfect liquidity
                # Scale: 0 = 1.0, 0.001 = 0.8, 0.01 = 0.5, 0.1 = 0.2, >1 = 0
                if value <= 0:
                    normalized[metric_name] = 1.0
                elif value < 0.001:
                    normalized[metric_name] = 1.0 - value / 0.001 * 0.2
                elif value < 0.01:
                    normalized[metric_name] = 0.8 - (value - 0.001) / (0.01 - 0.001) * 0.3
                elif value < 0.1:
                    normalized[metric_name] = 0.5 - (value - 0.01) / (0.1 - 0.01) * 0.3
                elif value < 1:
                    normalized[metric_name] = 0.2 - (value - 0.1) / (1 - 0.1) * 0.15
                else:
                    normalized[metric_name] = max(0.05 - value * 0.01, 0)
                    
            elif metric_name == 'high_low_spread':
                # Intraday range (high-low spread) - normal volatility for liquid stocks
                # Ultra-liquid: <1% = 0.90-1.00
                # Very liquid: 1-2% = 0.75-0.90  
                # Liquid: 2-3% = 0.60-0.75
                # Moderate: 3-4% = 0.45-0.60
                # Low: 4-6% = 0.25-0.45
                # Illiquid: >6% = 0-0.25
                if value <= 0:
                    normalized[metric_name] = 1.0
                elif value < 1.0:  # <1% - Ultra liquid range
                    normalized[metric_name] = 0.90 + (1.0 - value) / 1.0 * 0.10
                elif value < 2.0:  # 1-2% - Very liquid range
                    normalized[metric_name] = 0.75 + (2.0 - value) / 1.0 * 0.15
                elif value < 3.0:  # 2-3% - Liquid range
                    normalized[metric_name] = 0.60 + (3.0 - value) / 1.0 * 0.15
                elif value < 4.0:  # 3-4% - Moderate range
                    normalized[metric_name] = 0.45 + (4.0 - value) / 1.0 * 0.15
                elif value < 6.0:  # 4-6% - Low liquidity range
                    normalized[metric_name] = 0.25 + (6.0 - value) / 2.0 * 0.20
                else:  # >6% - Illiquid/high volatility
                    normalized[metric_name] = max(0.25 - (value - 6.0) * 0.05, 0)
                    
            elif metric_name == 'roll_spread':
                # Roll spread (%) - similar to high_low_spread thresholds
                if value <= 0:
                    normalized[metric_name] = 1.0
                elif value < 0.1:
                    normalized[metric_name] = 1.0 - value / 0.1 * 0.1
                elif value < 0.5:
                    normalized[metric_name] = 0.9 - (value - 0.1) / 0.4 * 0.3
                elif value < 1.0:
                    normalized[metric_name] = 0.6 - (value - 0.5) / 0.5 * 0.3
                else:
                    normalized[metric_name] = max(0.3 - (value - 1.0) * 0.1, 0)
                    
            elif metric_name == 'turnover_ratio':
                # Daily turnover %: 0.5-2% is healthy, >5% is very liquid
                if value <= 0:
                    normalized[metric_name] = 0
                elif value < 0.1:
                    normalized[metric_name] = value / 0.1 * 0.3
                elif value < 0.5:
                    normalized[metric_name] = 0.3 + (value - 0.1) / 0.4 * 0.3
                elif value < 2.0:
                    normalized[metric_name] = 0.6 + (value - 0.5) / 1.5 * 0.25
                elif value < 5.0:
                    normalized[metric_name] = 0.85 + (value - 2.0) / 3.0 * 0.1
                else:
                    normalized[metric_name] = min(0.95 + value * 0.001, 1.0)
            else:
                # Default fallback for any other metrics
                if higher_is_better.get(metric_name, True):
                    normalized[metric_name] = min(value, 1.0)
                else:
                    normalized[metric_name] = max(1.0 - value, 0)
        
        # Calculate weighted composite score
        composite_score = 0.0
        total_weight = 0.0
        
        for metric_name, norm_value in normalized.items():
            weight = weights.get(metric_name, 0)
            composite_score += norm_value * weight
            total_weight += weight
        
        # Normalize by actual weights used (handles missing metrics)
        if total_weight > 0:
            composite_score = composite_score / total_weight
        else:
            composite_score = np.nan
            
        return float(composite_score), normalized
    
    def score_asset(
        self,
        ohlcv_data: pd.DataFrame,
        market_cap: Optional[float] = None,
        shares_outstanding: Optional[float] = None,
        lookback_days: int = 30
    ) -> Dict[str, Union[float, Dict]]:
        """
        Calculate comprehensive liquidity score for an asset.
        
        Args:
            ohlcv_data: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            market_cap: Current market capitalization
            shares_outstanding: Number of shares outstanding
            lookback_days: Days of historical data to use for metrics
            
        Returns:
            Dictionary containing:
                - composite_score: Overall liquidity score (0-1)
                - metrics: Individual metric values
                - normalized: Normalized metric values
                - grade: Letter grade (A-F)
        """
        if ohlcv_data.empty:
            return {
                'composite_score': np.nan,
                'metrics': {},
                'normalized': {},
                'grade': 'U'  # Unknown
            }
        
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in ohlcv_data.columns for col in required_cols):
            raise ValueError(f"OHLCV data must contain columns: {required_cols}")
        
        # Calculate returns
        daily_returns = ohlcv_data['close'].pct_change()
        
        # Calculate dollar volume
        dollar_volume = ohlcv_data['close'] * ohlcv_data['volume']
        
        # Calculate individual metrics
        metrics = {}
        
        # 1. Amihud illiquidity ratio
        metrics['amihud_ratio'] = self.amihud_illiquidity_ratio(
            daily_returns=daily_returns,
            daily_volume_dollars=dollar_volume,
            lookback_days=lookback_days
        )
        
        # 2. Roll spread (may return NaN if not calculable)
        roll = self.roll_spread(
            close_prices=ohlcv_data['close'],
            lookback_days=lookback_days
        )
        if not pd.isna(roll):
            metrics['roll_spread'] = roll
        
        # 3. Turnover ratio (if shares outstanding available)
        if shares_outstanding and shares_outstanding > 0:
            metrics['turnover_ratio'] = self.turnover_ratio(
                daily_volume=ohlcv_data['volume'],
                shares_outstanding=shares_outstanding,
                lookback_days=lookback_days
            )
        
        # 4. Average dollar volume
        metrics['dollar_volume'] = self.average_dollar_volume(
            close_prices=ohlcv_data['close'],
            daily_volume=ohlcv_data['volume'],
            lookback_days=lookback_days
        )
        
        # 5. High-low spread
        metrics['high_low_spread'] = self.high_low_spread(
            high_prices=ohlcv_data['high'],
            low_prices=ohlcv_data['low'],
            close_prices=ohlcv_data['close'],
            lookback_days=lookback_days
        )
        
        # 6. Market cap score
        if market_cap is not None:
            metrics['market_cap_score'] = self.market_cap_liquidity_score(
                market_cap=market_cap
            )
        
        # Filter out NaN metrics
        valid_metrics = {k: v for k, v in metrics.items() if not pd.isna(v)}
        
        # Calculate composite score
        composite_score, normalized = self.calculate_composite_score(
            metrics=valid_metrics,
            weights=self.DEFAULT_WEIGHTS
        )
        
        # Assign letter grade
        grade = self._assign_grade(composite_score)
        
        return {
            'composite_score': composite_score,
            'metrics': metrics,
            'normalized': normalized,
            'grade': grade
        }
    
    @staticmethod
    def _assign_grade(score: float) -> str:
        """
        Convert numeric score to letter grade based on market liquidity tiers.
        
        Grading scale:
        - A: 0.85+ (Ultra/Mega liquid - SPY, QQQ, AAPL, NVDA, MSFT)
        - B: 0.70-0.85 (Very liquid - most S&P 500 stocks)
        - C: 0.55-0.70 (Liquid - tradeable mid/small caps)
        - D: 0.40-0.55 (Moderate liquidity - caution advised)
        - F: <0.40 (Illiquid - high trading risk)
        
        Returns:
            Letter grade A-F or U for unknown
        """
        if pd.isna(score):
            return 'U'
        elif score >= 0.85:
            return 'A'
        elif score >= 0.70:
            return 'B'
        elif score >= 0.55:
            return 'C'
        elif score >= 0.40:
            return 'D'
        else:
            return 'F'
    
    def analyze_ticker(
        self,
        ticker: str,
        lookback_days: int = 30,
        price_data_days: int = 252
    ) -> Dict[str, Union[float, Dict, str]]:
        """
        Analyze liquidity for a given ticker symbol.
        
        Args:
            ticker: Stock ticker symbol
            lookback_days: Days of historical data to use for liquidity metrics
            price_data_days: Days of price data to fetch (default 252 = 1 year)
            
        Returns:
            Dictionary containing liquidity analysis results
        """
        from app.repositories.price_data import get_price_data_daily
        from app.repositories.fundamental_data import get_fundamental_data
        from datetime import datetime, timedelta
        
        # Get price data
        end_date = get_current_utc_time()
        start_date = end_date - timedelta(days=price_data_days)
        
        # Fetch OHLCV data
        ohlcv_data = get_price_data_daily(ticker, start_date, end_date)
        
        if ohlcv_data.empty:
            return {
                'ticker': ticker,
                'composite_score': np.nan,
                'metrics': {},
                'normalized': {},
                'grade': 'U',
                'market_cap': None,
                'shares_outstanding': None,
                'error': 'No price data available'
            }
        
        # Fetch fundamental data for market cap and shares
        market_cap = None
        shares_outstanding = None
        
        try:
            # Try income statement for shares outstanding
            income_statement = get_fundamental_data(ticker, "income_statement", quarters_back=1)
            logger.debug(f"Income statement data for {ticker}: {income_statement}")
            
            if income_statement.get("data") and income_statement["data"]:
                latest = income_statement["data"][0]
                shares_outstanding = latest.get("shares_outstanding")
                logger.debug(f"Shares outstanding for {ticker}: {shares_outstanding}")
            
            # Calculate market cap from latest price and shares
            if not ohlcv_data.empty and shares_outstanding:
                latest_price = ohlcv_data['close'].iloc[-1]
                market_cap = latest_price * shares_outstanding
                logger.debug(f"Calculated market cap for {ticker}: {market_cap}")
            
            # If we still don't have shares outstanding, try balance sheet
            if shares_outstanding is None:
                balance_sheet = get_fundamental_data(ticker, "balance_sheet", quarters_back=1)
                logger.debug(f"Balance sheet data for {ticker}: {balance_sheet}")
                if balance_sheet.get("data") and balance_sheet["data"]:
                    latest_bs = balance_sheet["data"][0]
                    # Balance sheet doesn't have shares_outstanding, so we'll skip this
                    pass
        except Exception as e:
            logger.warning(f"Could not fetch fundamental data for {ticker}: {e}")
            market_cap = None
            shares_outstanding = None
        
        # Calculate liquidity score (market_cap and shares_outstanding are optional)
        result = self.score_asset(
            ohlcv_data=ohlcv_data,
            market_cap=market_cap,
            shares_outstanding=shares_outstanding,
            lookback_days=lookback_days
        )
        
        # Add debug info about what data we have
        logger.debug(f"Final data for {ticker}: market_cap={market_cap}, shares_outstanding={shares_outstanding}")
        
        # Add ticker and additional info to result
        result['ticker'] = ticker
        result['market_cap'] = market_cap
        result['shares_outstanding'] = shares_outstanding
        
        return result



