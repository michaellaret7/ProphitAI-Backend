from typing import Optional, Tuple
import numpy as np
import pandas as pd
import requests
from io import StringIO
from pydantic import BaseModel
from backend.src.data_models.style_factors_models import MomentumFactorMetrics

class MomentumFactors:
    def __init__(self, price_series: pd.Series, volume_series: Optional[pd.Series] = None, spy_price_series: Optional[pd.Series] = None, sector_price_series: Optional[pd.Series] = None):
        
        self.prices = price_series.astype(float)

        if self.prices is not None:
            self.returns = self.prices.pct_change().dropna()

        self.volumes = volume_series.astype(float).reindex(self.prices.index)

        self.sector_prices = sector_price_series.astype(float).reindex(self.prices.index)
        if self.sector_prices is not None:
            self.sector_returns = self.sector_prices.pct_change().dropna()

        self.spy_prices = spy_price_series.astype(float).reindex(self.prices.index)

        if self.spy_prices is not None:
            self.spy_returns = self.spy_prices.pct_change().dropna()

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def _total_return(self, lookback: int, skip: int = 21) -> Optional[float]:
        """
        Total return over `lookback` days **excluding** the most recent `skip`
        days (default 1 month ≈ 21 trading days).

        Returns None if insufficient history.

        """
        idx = len(self.prices)
        if idx < lookback + skip:
            return None
        past_price = self.prices.iloc[-(lookback + skip)]
        recent_price = self.prices.iloc[-1]
        return (recent_price / past_price) - 1.0

    # ------------------------------------------------------------------
    # 1-, 3-, 6-, 12-month returns
    # ------------------------------------------------------------------
    def one_month_return(self) -> Optional[float]:
        """1-month total return (no skip)."""
        return round(self._total_return(lookback=21, skip=0), 4) 

    def three_month_return(self, skip: int = 21) -> Optional[float]:
        """
        3-month (≈63 trading-day) return, default *skipping* last 21 days.

        Parameters
        ----------
        skip : int, default 21
            Trading days to exclude at the end of the window—set to 0 if you
            **do want** the most recent month included.
        """
        return round(self._total_return(lookback=63, skip=skip), 4)

    def six_month_return(self, skip: int = 21) -> Optional[float]:
        """6-month total return (≈126 days), skipping `skip` most recent days."""
        return round(self._total_return(lookback=126, skip=skip), 4)

    def twelve_month_return_ex1m(self) -> Optional[float]:
        """12-month return **excluding** the last 1 month (lookback 252, skip 21)."""
        return round(self._total_return(lookback=252, skip=21), 4)

    # ------------------------------------------------------------------
    # % from 52-week high
    # ------------------------------------------------------------------
    def pct_from_52w_high(self, window: int = 252) -> Optional[float]:
        """
        Distance from 52-week high.

        Parameters
        ----------
        window : int, default 252
            Number of trading days to define "52-week" period.

        Returns `None` if < `window` observations.
        """
        if len(self.prices) < window:
            return None
        highest = self.prices.iloc[-window:].max()
        current = self.prices.iloc[-1]
        return round((current / highest) - 1.0, 4)

    # ------------------------------------------------------------------
    # SMA ratio (Golden-Cross style)
    # ------------------------------------------------------------------
    def sma_ratio(self, fast: int = 50, slow: int = 200, latest_only: bool = True) -> Optional[float]:
        """
        Simple Moving Average **ratio** (SMA_fast / SMA_slow − 1).

        Parameters
        ----------
        fast : int, default 50
            Lookback for the faster SMA.
        slow : int, default 200
            Lookback for the slower SMA. Must be > `fast`.
        latest_only : bool, default True
            If `True`, returns the latest ratio; otherwise returns a
            pandas Series for the entire history.

        """
        if slow <= fast:
            raise ValueError("`slow` must be > `fast`")

        sma_fast = self.prices.rolling(fast).mean()
        sma_slow = self.prices.rolling(slow).mean()
        ratio_series = (sma_fast / sma_slow) - 1.0

        if latest_only:
            return round(ratio_series.iloc[-1], 4) if not np.isnan(ratio_series.iloc[-1]) else None
        return round(ratio_series, 4)

    # ------------------------------------------------------------------
    # MACD (EMA-12, EMA-26, signal = EMA-9 of MACD)
    # ------------------------------------------------------------------
    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[Optional[float], Optional[float]]:
        """
        Moving Average Convergence–Divergence.

        Returns
        -------
        macd_value, signal_value : tuple(float | None, float | None)
            Latest MACD and its 9-period signal line. `None` if history short.
        """
        if len(self.prices) < slow_period + signal_period:
            return None, None

        ema_fast = self.prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = self.prices.ewm(span=slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

        return round(macd_line.iloc[-1], 4), round(signal_line.iloc[-1], 4)

    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------
    def rsi(self, window: int = 14) -> Optional[float]:
        """
        Relative Strength Index (Wilder's 1978).

        Parameters
        ----------
        window : int, default 14
            Lookback window for average gains/losses.

        Returns
        -------
        float | None
            Latest RSI value (0–100). None if insufficient history.
        """
        if len(self.returns) < window + 1:
            return None

        delta = self.prices.diff().dropna()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)

        avg_up = up.rolling(window).mean()
        avg_down = down.rolling(window).mean()

        rs = avg_up / avg_down.replace(0, np.nan)
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        return round(rsi_series.iloc[-1], 4)

    # ------------------------------------------------------------------
    # Idiosyncratic Momentum (CAPM residuals)
    # ------------------------------------------------------------------
    def idiosyncratic_momentum(self, lookback: int = 60) -> Optional[float]:
        """
        Cumulative CAPM residual return over `lookback` days.

        Requires `spy_price_series` supplied at construction.

        Returns
        -------
        float | None
            Sum of daily residuals. Higher ⇒ positive idiosyncratic trend.
        """
        if self.spy_prices is None:
            raise ValueError("spy_price_series is required for this metric")

        if len(self.returns) < lookback + 1:
            return None

        import statsmodels.api as sm

        y = self.returns.iloc[-lookback:]
        x = sm.add_constant(self.spy_returns.loc[y.index])

        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        # Sum of residuals for OLS with an intercept is always 0.
        # Instead, we calculate the cumulative compounded return of the residuals.
        return round((1 + resid).prod() - 1, 4)
    
    def sector_idiosyncratic_momentum(self, lookback: int = 60) -> Optional[float]:
        """
        Cumulative CAPM residual return over `lookback` days.

        Requires `sector_price_series` supplied at construction.
        """
        if self.sector_prices is None:
            raise ValueError("sector_price_series is required for this metric")
        
        if len(self.returns) < lookback + 1:
            return None
        
        import statsmodels.api as sm

        y = self.returns.iloc[-lookback:]
        x = sm.add_constant(self.sector_returns.loc[y.index])

        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        # Sum of residuals for OLS with an intercept is always 0.
        # Instead, we calculate the cumulative compounded return of the residuals.
        return round((1 + resid).prod() - 1, 4)

    # ------------------------------------------------------------------
    # Volume-Adjusted Momentum
    # ------------------------------------------------------------------
    def volume_adjusted_momentum(self, lookback: int = 60) -> Optional[float]:
        """
        Volume-weighted average return over `lookback` days.

        Parameters
        ----------
        lookback : int, default 60
            Number of recent trading days to include.

        Returns
        -------
        float | None
            Σ(r_t * vol_t) / Σ(vol_t).  Requires `volume_series`.
        """
        if self.volumes is None:
            raise ValueError("volume_series is required for this metric")

        if len(self.returns) < lookback + 1:
            return None

        window_ret = self.returns.iloc[-lookback:]
        window_vol = self.volumes.loc[window_ret.index]

        vw_return = (window_ret * window_vol).sum() / window_vol.sum()
        return round(vw_return, 4)

    def calc_all(
        self, 
        three_month_skip: int = 21,
        six_month_skip: int = 21,
        window_52w: int = 252,
        sma_fast: int = 50,
        sma_slow: int = 200,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        rsi_window: int = 14,
        idio_lookback: int = 60,
        sector_idio_lookback: int = 60,
        vol_adj_lookback: int = 60
    ) -> MomentumFactorMetrics:
        """
        Calculate all momentum factor metrics at once.
        
        Parameters
        ----------
        All parameters are optional and use default values from individual methods.
        
        Returns
        -------
        MomentumFactorMetrics
            Pydantic model containing all calculated momentum metrics
        """
        
        # Calculate MACD values (returns tuple)
        macd_result = self.macd(macd_fast, macd_slow, macd_signal)
        macd_value = macd_result[0] if macd_result[0] is not None else None
        macd_signal_value = macd_result[1] if macd_result[1] is not None else None

        idiosyncratic_momentum_value = self.idiosyncratic_momentum(idio_lookback)
        sector_idiosyncratic_momentum_value = self.sector_idiosyncratic_momentum(sector_idio_lookback)
        volume_adjusted_momentum_value = self.volume_adjusted_momentum(vol_adj_lookback)
        
        return MomentumFactorMetrics(
            one_month_return=self.one_month_return(),
            three_month_return=self.three_month_return(skip=three_month_skip),
            six_month_return=self.six_month_return(skip=six_month_skip),
            twelve_month_return_ex1m=self.twelve_month_return_ex1m(),
            pct_from_52w_high=self.pct_from_52w_high(window=window_52w),
            sma_ratio=self.sma_ratio(fast=sma_fast, slow=sma_slow),
            macd_value=macd_value,
            macd_signal=macd_signal_value,
            rsi=self.rsi(window=rsi_window),
            idiosyncratic_momentum=idiosyncratic_momentum_value,
            sector_idiosyncratic_momentum=sector_idiosyncratic_momentum_value,
            volume_adjusted_momentum=volume_adjusted_momentum_value,
        )


if __name__ == "__main__":
    import random
    
    # Set seed for reproducible results
    np.random.seed(42)
    random.seed(42)
    
    n_days = 500
    
    # Generate realistic stock price series with drift and volatility
    initial_price = 100.0
    daily_returns = np.random.normal(0.0008, 0.02, n_days)  # ~0.08% daily return, 2% volatility
    cumulative_returns = np.cumsum(daily_returns)
    price_series = pd.Series(initial_price * np.exp(cumulative_returns))
    
    # Generate volume series with realistic variation (mean reversion around average volume)
    base_volume = 2000000  # 2M shares average
    volume_noise = np.random.lognormal(0, 0.5, n_days)  # Log-normal for realistic volume spikes
    volume_series = pd.Series(base_volume * volume_noise)
    
    # Generate SPY price series (market benchmark) - slightly less volatile than individual stock
    spy_initial = 400.0
    spy_returns = np.random.normal(0.0005, 0.015, n_days)  # Lower volatility than individual stock
    spy_cumulative_returns = np.cumsum(spy_returns)
    spy_price_series = pd.Series(spy_initial * np.exp(spy_cumulative_returns))
    
    # Generate sector price series - correlated with individual stock but with own dynamics
    sector_initial = 150.0
    # Make sector somewhat correlated with the stock (0.6 correlation)
    sector_specific_returns = np.random.normal(0.0006, 0.018, n_days)
    combined_sector_returns = 0.6 * daily_returns + 0.4 * sector_specific_returns
    sector_cumulative_returns = np.cumsum(combined_sector_returns)
    sector_price_series = pd.Series(sector_initial * np.exp(sector_cumulative_returns))
    
    # Create date index for more realistic time series
    dates = pd.date_range(start='2022-01-01', periods=n_days, freq='D')
    price_series.index = dates
    volume_series.index = dates
    spy_price_series.index = dates
    sector_price_series.index = dates
    
    # Initialize MomentumFactors class
    momentum_calc = MomentumFactors(
        price_series=price_series,
        volume_series=volume_series,
        spy_price_series=spy_price_series,
        sector_price_series=sector_price_series
    )
    
    # Calculate all momentum metrics
    momentum_metrics = momentum_calc.calc_all()
    
    # Create MomentumMetrics instance
    momentum_metrics = momentum_metrics
    
    print("Generated Momentum Metrics:")
    print(momentum_metrics)

