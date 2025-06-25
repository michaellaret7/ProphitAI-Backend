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
        self.prices = price_series.astype(float)
        self.returns = self.prices.pct_change(fill_method=None).dropna()
        
        if spy_price_series is not None:
            self.spy_prices = spy_price_series.astype(float).reindex(self.prices.index)
            self.spy_returns = self.spy_prices.pct_change(fill_method=None).dropna()
        else:
            self.spy_prices = None
            self.spy_returns = None

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
        
        Parameters
        ----------
        lookback_days : int
            Number of days to look back for volatility calculation
            
        Returns
        -------
        float or None
            Annualized volatility, or None if insufficient data
        """
        if len(self.returns) < lookback_days:
            return None
        
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
        1-Year Beta (CAPM) = cov(returns, spy) / var(spy) over 252 days
        """
        if self.spy_returns is None:
            return None
        
        # Align returns and get last 252 days
        combined_df = pd.concat([self.returns, self.spy_returns], axis=1, keys=['asset', 'spy']).dropna()
        
        if len(combined_df) < 252:
            return None
        
        recent_data = combined_df.iloc[-252:]
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
        Idiosyncratic Volatility = std(residuals) from CAPM over 252 days
        """
        if self.spy_returns is None:
            return None
        
        import statsmodels.api as sm
        
        # Align returns and get last 252 days
        combined_df = pd.concat([self.returns, self.spy_returns], axis=1, keys=['asset', 'spy']).dropna()
        
        if len(combined_df) < 252:
            return None
        
        recent_data = combined_df.iloc[-252:]
        y = recent_data['asset']
        x_market = recent_data['spy']
        x = sm.add_constant(x_market)
        
        model = sm.OLS(y, x, missing="drop").fit()
        residuals = model.resid
        
        # Annualize the residual volatility
        idio_vol = residuals.std() * np.sqrt(252)
        return idio_vol

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
        Max Drawdown (1 yr) = (peak − trough) / peak over rolling 252 days
        """
        if len(self.prices) < 252:
            return None
        
        prices_1yr = self.prices.iloc[-252:]
        
        # Calculate cumulative maximum (running peak)
        cumulative_max = prices_1yr.expanding().max()
        
        # Calculate drawdown at each point
        drawdown = (prices_1yr - cumulative_max) / cumulative_max
        
        # Maximum drawdown is the most negative value
        max_dd = drawdown.min()
        return max_dd

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
        Variance Ratio (3m / 12m) = var_63d / var_252d
        """
        if len(self.returns) < 252:
            return None
        
        returns_63d = self.returns.iloc[-63:]
        returns_252d = self.returns.iloc[-252:]
        
        var_63d = returns_63d.var()
        var_252d = returns_252d.var()
        
        if var_252d == 0:
            return None
        
        variance_ratio = var_63d / var_252d
        return variance_ratio

    # ------------------------------------------------------------------
    # Skewness and Kurtosis
    # ------------------------------------------------------------------
    def skewness(self, lookback: int = 252) -> Optional[float]:
        """
        Skewness = scipy.stats.skew(returns_252d)
        """
        if len(self.returns) < lookback:
            return None
        
        returns_period = self.returns.iloc[-lookback:]
        skew = scipy.stats.skew(returns_period)
        return skew

    def kurtosis(self, lookback: int = 252) -> Optional[float]:
        """
        Kurtosis = scipy.stats.kurtosis(returns_252d)
        """
        if len(self.returns) < lookback:
            return None
        
        returns_period = self.returns.iloc[-lookback:]
        kurt = scipy.stats.kurtosis(returns_period)
        return kurt

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
    def calc_all(
        self,
        realized_vol_30d_enabled: bool = True,
        realized_vol_90d_enabled: bool = True,
        beta_enabled: bool = True,
        idio_vol_enabled: bool = True,
        downside_dev_enabled: bool = True,
        max_drawdown_enabled: bool = True,
        atr_enabled: bool = True,
        variance_ratio_enabled: bool = True,
        skewness_enabled: bool = True,
        kurtosis_enabled: bool = True,
        garch_enabled: bool = True,
        atr_period: int = 14,
        skewness_lookback: int = 252,
        kurtosis_lookback: int = 252,
        annualized_volatility_enabled: bool = True,
        annualized_volatility_lookback: int = 252,
        daily_return_volatility_enabled: bool = True
    ) -> VolatilityFactorMetrics:
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
        
        return VolatilityFactorMetrics(
            realized_vol_30d=self.realized_vol_30d() if realized_vol_30d_enabled else None,
            realized_vol_90d=self.realized_vol_90d() if realized_vol_90d_enabled else None,
            beta_1yr=self.beta_1yr() if beta_enabled else None,
            idiosyncratic_vol=self.idiosyncratic_vol() if idio_vol_enabled else None,
            downside_dev_30d=self.downside_dev_30d() if downside_dev_enabled else None,
            max_drawdown_1yr=self.max_drawdown_1yr() if max_drawdown_enabled else None,
            atr_price_ratio=self.atr_price_ratio(period=atr_period) if atr_enabled else None,
            variance_ratio_3m_12m=self.variance_ratio_3m_12m() if variance_ratio_enabled else None,
            skewness=self.skewness(lookback=skewness_lookback) if skewness_enabled else None,
            kurtosis=self.kurtosis(lookback=kurtosis_lookback) if kurtosis_enabled else None,
            garch_forecast=self.garch_forecast() if garch_enabled else None,
            annualized_volatility=self.annualized_volatility(lookback_days=annualized_volatility_lookback) if annualized_volatility_enabled else None,
            daily_return_volatility=self.daily_return_volatility() if daily_return_volatility_enabled else None,
        )


if __name__ == "__main__":
    from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
    from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
    from backend.src.utils.determine_etf import is_etf_ticker
    from datetime import datetime, timedelta
    
    print("Testing VolatilityFactors with sample data...")
    print("=" * 60)
    
    # Initialize repositories
    equity_prices = EquityPriceDataRepository()
    etf_prices = ETFPriceDataRepository()

    ticker = 'msft'

    if is_etf_ticker(ticker):
        etf_data = etf_prices.fetch_etf_price_data(
            ticker, 
            start_date=datetime.now() - timedelta(days=500), 
            end_date=datetime.now(), 
            interval='1d'
        )
        price_data = etf_data['close']
    else:
        equity_data = equity_prices.fetch_equity_price_data(
            ticker, 
            start_date=datetime.now() - timedelta(days=500), 
            end_date=datetime.now(), 
            interval='1d'
        )
        price_data = equity_data['close']
        

    # Fetch SPY data for beta calculation
    spy_df = etf_prices.fetch_etf_price_data(
        'spy', 
        start_date=datetime.now() - timedelta(days=500), 
        end_date=datetime.now(), 
        interval='1d'
    )
    spy_price_data = spy_df['close']
    
    # Initialize VolatilityFactors
    volatility_factors = VolatilityFactors(price_data, spy_price_data)
    
    # Calculate all metrics
    all_metrics = volatility_factors.calc_all()
    print(all_metrics)
    

