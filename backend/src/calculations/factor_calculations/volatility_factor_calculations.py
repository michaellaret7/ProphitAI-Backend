from typing import Optional, Tuple
import numpy as np
import pandas as pd
import scipy.stats
from backend.src.data_models.style_factors_models import VolatilityFactorMetrics

class VolatilityFactors:
    def __init__(self, price_series: pd.Series, spy_price_series: Optional[pd.Series] = None):
        """
        Initialize VolatilityFactors with price data.
        
        Parameters
        ----------
        price_series : pd.Series
            Time series of asset prices
        spy_price_series : pd.Series, optional
            Time series of SPY prices for beta calculation
        """
        if price_series is None or price_series.empty:
            raise ValueError("Price series cannot be None or empty.")

        self.prices = price_series.astype(float)
        self.returns = self.prices.pct_change(fill_method=None).dropna()
        
        if spy_price_series is not None and not spy_price_series.empty:
            self.spy_prices = spy_price_series.astype(float).reindex(self.prices.index)
            self.spy_returns = self.spy_prices.pct_change(fill_method=None).dropna()
        else:
            self.spy_prices = None
            self.spy_returns = None
        
        self.annualized_volatility_lookback: int = 252
        self.skewness_lookback: int = 252
        self.kurtosis_lookback: int = 252
        self.atr_period: int = 14

    # ------------------------------------------------------------------
    # Realized Volatility Calculations
    # ------------------------------------------------------------------
    def realized_vol_30d(self) -> Optional[float]:
        """
        30-Day Realized Volatility = sqrt(252) × std(returns_30d)
        """
        if len(self.returns) < 30:
            return None
        
        returns_30d = self.returns.iloc[-30:]
        vol = returns_30d.std() * np.sqrt(252)
        return vol

    def realized_vol_90d(self) -> Optional[float]:
        """
        90-Day Realized Volatility = sqrt(252) × std(returns_90d)
        """
        if len(self.returns) < 90:
            return None
        
        returns_90d = self.returns.iloc[-90:]
        vol = returns_90d.std() * np.sqrt(252)
        return vol

    def annualized_volatility(self, lookback_days: int) -> Optional[float]:
        """
        Calculate annualized volatility for any lookback period.
        If fewer than lookback_days are available, uses all available returns.
        """
        # Use the most recent lookback_days returns (or all if fewer)
        returns_period = self.returns.iloc[-lookback_days:]
        vol = returns_period.std() * np.sqrt(252)
        return vol

    def daily_return_volatility(self) -> Optional[float]:
        """Calculate daily return volatility."""
        if len(self.returns) < 2:
            return None
        return np.std(self.returns, ddof=1)

    # ------------------------------------------------------------------
    # Beta Calculation (CAPM)
    # ------------------------------------------------------------------
    def beta_1yr(self) -> Optional[float]:
        """
        Beta (CAPM) = cov(returns, spy) / var(spy) - uses available data, minimum 30 days
        """
        if self.spy_returns is None:
            return None
        
        # Align returns and use available data (minimum 30 days)
        combined_df = pd.concat([self.returns, self.spy_returns], axis=1, keys=['asset', 'spy']).dropna()
        
        if len(combined_df) < 30:
            return None
        
        # Use up to 252 days if available, otherwise use what we have
        lookback = min(252, len(combined_df))
        recent_data = combined_df.iloc[-lookback:]
        asset_returns = recent_data['asset']
        spy_returns = recent_data['spy']
        
        covariance = np.cov(asset_returns, spy_returns)[0, 1]
        spy_variance = np.var(spy_returns, ddof=1)
        
        if spy_variance == 0:
            return None
        
        beta = covariance / spy_variance
        return beta

    # ------------------------------------------------------------------
    # Idiosyncratic Volatility
    # ------------------------------------------------------------------
    def idiosyncratic_vol(self) -> Optional[float]:
        """
        Idiosyncratic Volatility = std(residuals) from CAPM - uses available data, minimum 30 days
        """
        if self.spy_returns is None:
            return None
        
        # Align returns and use available data
        combined_df = pd.concat([self.returns, self.spy_returns], axis=1, keys=['asset', 'spy']).dropna()
        
        if len(combined_df) < 30:  # Minimum 30 days
            return None
        
        # Use up to 252 days if available, otherwise use what we have
        lookback = min(252, len(combined_df))
        recent_data = combined_df.iloc[-lookback:]
        y = recent_data['asset']
        x_market = recent_data['spy']
        
        try:
            import statsmodels.api as sm
            x = sm.add_constant(x_market)
            model = sm.OLS(y, x, missing="drop").fit()
            residuals = model.resid
        except ImportError:
            # Fallback: Manual CAPM calculation without statsmodels
            # Convert to numpy arrays to ensure proper calculation
            y_values = y.values
            x_values = x_market.values
            
            # Calculate beta using covariance method
            covariance = np.cov(y_values, x_values)[0, 1]
            market_variance = np.var(x_values, ddof=1)
            
            if market_variance == 0 or np.isnan(market_variance):
                return None
                
            beta = covariance / market_variance
            alpha = np.mean(y_values) - beta * np.mean(x_values)
            
            # Calculate predicted returns using CAPM: R = alpha + beta * R_market
            predicted_returns = alpha + beta * x_values
            
            # Calculate residuals: actual - predicted
            residuals = y_values - predicted_returns
        
        # Annualize the residual volatility
        # Use ddof=1 for sample standard deviation (consistent with financial practice)
        if hasattr(residuals, 'std'):
            # pandas Series
            idio_vol = residuals.std() * np.sqrt(252)
        else:
            # numpy array
            idio_vol = np.std(residuals, ddof=1) * np.sqrt(252)
        
        return idio_vol if not (np.isnan(idio_vol) or idio_vol <= 0) else None

    # ------------------------------------------------------------------
    # Downside Deviation
    # ------------------------------------------------------------------
    def downside_dev_30d(self) -> Optional[float]:
        """
        Downside Deviation (30d) = sqrt(mean(min(0, returns)^2)) × √252
        """
        if len(self.returns) < 30:
            return None
        
        returns_30d = self.returns.iloc[-30:]
        downside_returns = np.minimum(returns_30d, 0)
        downside_variance = np.mean(downside_returns ** 2)
        downside_dev = np.sqrt(downside_variance) * np.sqrt(252)
        
        return downside_dev

    # ------------------------------------------------------------------
    # Maximum Drawdown
    # ------------------------------------------------------------------
    def max_drawdown_1yr(self) -> Optional[float]:
        """
        Max Drawdown = (peak − trough) / peak - uses available data, minimum 30 days
        """
        if len(self.prices) < 30:
            return None
        
        # Use up to 252 days if available, otherwise use what we have
        lookback = min(252, len(self.prices))
        prices_period = self.prices.iloc[-lookback:]
        
        # Calculate cumulative maximum (running peak)
        cumulative_max = prices_period.expanding().max()

        # Avoid division by zero
        safe_cumulative_max = cumulative_max.replace(0, np.nan)
        
        # Calculate drawdown at each point
        drawdown = (prices_period - safe_cumulative_max) / safe_cumulative_max
        
        # Maximum drawdown is the most negative value
        max_dd = drawdown.min()
        return max_dd if not np.isnan(max_dd) else None

    # ------------------------------------------------------------------
    # ATR/Price Ratio
    # ------------------------------------------------------------------
    def atr_price_ratio(self, period: int = 14) -> Optional[float]:
        """
        ATR (14) / Price
        
        Average True Range divided by current price
        """
        if len(self.prices) < period + 1:
            return None
        
        # Calculate True Range components
        high = self.prices  # Using close as proxy for high
        low = self.prices   # Using close as proxy for low
        close = self.prices
        
        # True Range = max(high-low, |high-close_prev|, |low-close_prev|)
        close_prev = close.shift(1)
        tr1 = high - low  # This will be 0 since we're using close prices
        tr2 = np.abs(high - close_prev)
        tr3 = np.abs(low - close_prev)
        
        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        
        # Calculate ATR using simple moving average
        atr = true_range.rolling(window=period).mean().iloc[-1]
        current_price = self.prices.iloc[-1]
        
        if current_price == 0:
            return None
        
        atr_ratio = atr / current_price
        return atr_ratio

    # ------------------------------------------------------------------
    # Variance Ratio
    # ------------------------------------------------------------------
    def variance_ratio_3m_12m(self) -> Optional[float]:
        """
        Variance Ratio (3m / 12m) = var_short / var_long - uses available data
        """
        if len(self.returns) < 63:  # Need at least 3 months
            return None
        
        # Use 63 days for short period
        returns_short = self.returns.iloc[-63:]
        
        # For long period, use min(252, available data) but at least 126 days
        long_lookback = min(252, len(self.returns))
        if long_lookback < 126:
            long_lookback = len(self.returns)  # Use all available if less than 126
            
        returns_long = self.returns.iloc[-long_lookback:]
        
        var_short = returns_short.var()
        var_long = returns_long.var()
        
        if var_long == 0:
            return None
        
        variance_ratio = var_short / var_long
        return variance_ratio

    # ------------------------------------------------------------------
    # Skewness and Kurtosis
    # ------------------------------------------------------------------
    def skewness(self, lookback: int = 252) -> Optional[float]:
        """
        Skewness = scipy.stats.skew(returns) - uses available data, minimum 30 days
        """
        if len(self.returns) < 30:
            return None
        
        # Use up to lookback days if available, otherwise use what we have
        actual_lookback = min(lookback, len(self.returns))
        returns_period = self.returns.iloc[-actual_lookback:]
        skew = scipy.stats.skew(returns_period)
        return skew if not np.isnan(skew) else None

    def kurtosis(self, lookback: int = 252) -> Optional[float]:
        """
        Kurtosis = scipy.stats.kurtosis(returns) - uses available data, minimum 30 days
        """
        if len(self.returns) < 30:
            return None
        
        # Use up to lookback days if available, otherwise use what we have
        actual_lookback = min(lookback, len(self.returns))
        returns_period = self.returns.iloc[-actual_lookback:]
        kurt = scipy.stats.kurtosis(returns_period)
        return kurt if not np.isnan(kurt) else None

    # ------------------------------------------------------------------
    # GARCH Forecast
    # ------------------------------------------------------------------
    def garch_forecast(self) -> Optional[float]:
        """
        GARCH Forecast = σ²_t+1 from GARCH(1,1) model
        
        Simple GARCH(1,1) implementation:
        σ²_t+1 = ω + α*ε²_t + β*σ²_t
        """
        if len(self.returns) < 100:  # Need sufficient data for GARCH
            return None
        
        try:
            from arch import arch_model
            
            # Fit GARCH(1,1) model
            returns_pct = self.returns.iloc[-252:] * 100  # Convert to percentage returns
            model = arch_model(returns_pct, vol='Garch', p=1, q=1, rescale=False)
            fitted_model = model.fit(disp='off')
            
            # Get forecast for next period
            forecast = fitted_model.forecast(horizon=1)
            next_period_variance = forecast.variance.iloc[-1, 0]
            
            # Convert back to decimal form and annualize
            next_period_vol = np.sqrt(next_period_variance / 10000 * 252)
            
            return next_period_vol
            
        except ImportError:
            # Fallback to simple exponential smoothing if arch not available
            returns_squared = self.returns.iloc[-30:] ** 2
            # Simple exponential weighted moving average with alpha=0.1
            ewma_var = returns_squared.ewm(alpha=0.1).mean().iloc[-1]
            forecast_vol = np.sqrt(ewma_var * 252)
            return forecast_vol
        
        except Exception:
            # If GARCH fitting fails, return None
            return None

    # ------------------------------------------------------------------
    # Calculate All Metrics
    # ------------------------------------------------------------------
    def calc_all(self) -> VolatilityFactorMetrics:
        """
        Calculate all volatility factor metrics at once.
        
        Parameters
        ----------
        All parameters have defaults that enable all calculations.
        Set any *_enabled parameter to False to skip that calculation.
        
        Returns
        -------
        VolatilityFactorMetrics
            Pydantic model containing all calculated volatility metrics
        """
        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None"""
            
            return round(value, decimals) if value is not None else None

        return VolatilityFactorMetrics(
            realized_vol_30d=safe_round(self.realized_vol_30d()),
            realized_vol_90d=safe_round(self.realized_vol_90d()),
            beta_1yr=safe_round(self.beta_1yr()),
            idiosyncratic_vol=safe_round(self.idiosyncratic_vol()),
            downside_dev_30d=safe_round(self.downside_dev_30d()),
            max_drawdown_1yr=safe_round(self.max_drawdown_1yr()),
            atr_price_ratio=safe_round(self.atr_price_ratio(period=self.atr_period)),
            variance_ratio_3m_12m=safe_round(self.variance_ratio_3m_12m()),
            skewness=safe_round(self.skewness(lookback=self.skewness_lookback)),
            kurtosis=safe_round(self.kurtosis(lookback=self.kurtosis_lookback)),
            garch_forecast=safe_round(self.garch_forecast()),
            annualized_volatility=safe_round(self.annualized_volatility(lookback_days=self.annualized_volatility_lookback)),
            daily_return_volatility=safe_round(self.daily_return_volatility())
        )


if __name__ == "__main__":
    from backend.src.repositories.price_data import get_price_data_daily
    from datetime import datetime, timedelta
    
    print("Testing VolatilityFactors with sample data...")
    print("=" * 60)
    
    ticker = 'MSFT'  # Use uppercase
    start_date = datetime.now() - timedelta(days=500)
    end_date = datetime.now()

    # Fetch price data using the new function
    ticker_data = get_price_data_daily(ticker, start_date=start_date, end_date=end_date)
    
    if ticker_data.empty:
        print(f"No data found for {ticker}")
    else:
        price_data = ticker_data['close']
        
        # Fetch SPY data for beta calculation
        spy_df = get_price_data_daily('SPY', start_date=start_date, end_date=end_date)
        spy_price_data = spy_df['close'] if not spy_df.empty else None
        
        # Initialize VolatilityFactors
        volatility_factors = VolatilityFactors(price_data, spy_price_data)
        
        # Calculate all metrics
        all_metrics = volatility_factors.calc_all()
        print(all_metrics)
    

