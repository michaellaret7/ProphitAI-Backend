from typing import Optional, Tuple
import numpy as np
import pandas as pd
import requests
from io import StringIO
from pydantic import BaseModel
from backend.src.data_models.style_factors_models import MomentumFactorMetrics

ROUND_PRECISION = 6

class MomentumFactors:
    def __init__(self, price_series: pd.Series, volume_series: Optional[pd.Series] = None, spy_price_series: Optional[pd.Series] = None, sector_price_series: Optional[pd.Series] = None):
        
        self.prices = price_series.astype(float)

        if self.prices is not None:
            self.returns = self.prices.pct_change(fill_method=None).dropna()

        self.volumes = volume_series.astype(float).reindex(self.prices.index)

        self.sector_prices = sector_price_series.astype(float).reindex(self.prices.index)
        if self.sector_prices is not None:
            self.sector_returns = self.sector_prices.pct_change(fill_method=None).dropna()

        self.spy_prices = spy_price_series.astype(float).reindex(self.prices.index)

        if self.spy_prices is not None:
            self.spy_returns = self.spy_prices.pct_change(fill_method=None).dropna()

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
        
        if past_price is None or past_price == 0:
            return None
        return (recent_price / past_price) - 1.0

    # ------------------------------------------------------------------
    # 1-, 3-, 6-, 12-month returns
    # ------------------------------------------------------------------
    def one_month_return(self) -> Optional[float]:
        """1-month total return (no skip)."""
        return self._total_return(lookback=21, skip=0) 

    def three_month_return(self, skip: int = 21) -> Optional[float]:
        """
        3-month (≈63 trading-day) return, default *skipping* last 21 days.

        Parameters
        ----------
        skip : int, default 21
            Trading days to exclude at the end of the window—set to 0 if you
            **do want** the most recent month included.
        """
        return self._total_return(lookback=63, skip=skip)

    def six_month_return(self, skip: int = 21) -> Optional[float]:
        """6-month total return (≈126 days), skipping `skip` most recent days."""
        return self._total_return(lookback=126, skip=skip)

    def twelve_month_return_ex1m(self) -> Optional[float]:
        """12-month return **excluding** the last 1 month (lookback 252, skip 21)."""
        return self._total_return(lookback=252, skip=21)

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
        
        if highest is None or highest == 0:
            return None
        return (current / highest) - 1.0

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
            return ratio_series.iloc[-1] if not np.isnan(ratio_series.iloc[-1]) else None
        return ratio_series

    # ------------------------------------------------------------------
    # Simple Moving Averages
    # ------------------------------------------------------------------
    def simple_moving_average(self, window: int, latest_only: bool = True) -> Optional[float]:
        """
        Calculate Simple Moving Average for a given window.

        Parameters
        ----------
        window : int
            Number of periods for the moving average calculation.
        latest_only : bool, default True
            If `True`, returns the latest SMA value; otherwise returns a
            pandas Series for the entire history.

        Returns
        -------
        float | None
            Latest SMA value if latest_only=True, or pandas Series if False.
            Returns None if insufficient data.
        """
        if len(self.prices) < window:
            return None

        sma_series = self.prices.rolling(window=window).mean()

        if latest_only:
            latest_value = sma_series.iloc[-1]
            return latest_value if not np.isnan(latest_value) else None
        return sma_series

    def sma_50(self) -> Optional[float]:
        """
        50-day Simple Moving Average.

        Returns
        -------
        float | None
            Latest 50-day SMA value. None if insufficient history.
        """
        return self.simple_moving_average(window=50)

    def sma_200(self) -> Optional[float]:
        """
        200-day Simple Moving Average.

        Returns
        -------
        float | None
            Latest 200-day SMA value. None if insufficient history.
        """
        return self.simple_moving_average(window=200)

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

        return macd_line.iloc[-1], signal_line.iloc[-1]

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

        # Wilder's smoothing
        avg_up = up.ewm(com=window - 1, adjust=False).mean()
        avg_down = down.ewm(com=window - 1, adjust=False).mean()

        # Replace 0 with a very small number to avoid division by zero
        safe_avg_down = avg_down.replace(0, np.nan)
        if safe_avg_down.isnull().all(): # a check in case all values are 0
            return 0.0 # can be 0 or 50, depends on how you want to see it, I'll put 0

        rs = avg_up / safe_avg_down
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        return rsi_series.iloc[-1]

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

        import statsmodels.api as sm
        
        # Combine and align returns, dropping any non-overlapping dates
        combined_df = pd.concat([self.returns, self.spy_returns], axis=1, keys=['asset', 'market']).dropna()
        
        if len(combined_df) < lookback:
            return None

        y = combined_df['asset'].iloc[-lookback:]
        x_market = combined_df['market'].iloc[-lookback:]
        x = sm.add_constant(x_market)

        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid

        return (1 + resid).prod() - 1
    
    def sector_idiosyncratic_momentum(self, lookback: int = 60) -> Optional[float]:
        """
        Cumulative CAPM residual return over `lookback` days.

        Requires `sector_price_series` supplied at construction.
        """
        if self.sector_prices is None:
            raise ValueError("sector_price_series is required for this metric")
        
        import statsmodels.api as sm

        # Combine and align returns, dropping any non-overlapping dates
        combined_df = pd.concat([self.returns, self.sector_returns], axis=1, keys=['asset', 'sector']).dropna()
        
        if len(combined_df) < lookback:
            return None
        
        y = combined_df['asset'].iloc[-lookback:]
        x_sector = combined_df['sector'].iloc[-lookback:]
        x = sm.add_constant(x_sector)

        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        # Sum of residuals for OLS with an intercept is always 0.
        # Instead, we calculate the cumulative compounded return of the residuals.
        return (1 + resid).prod() - 1

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

        total_volume = window_vol.sum()
        if total_volume is None or total_volume == 0:
            return None

        vw_return = (window_ret * window_vol).sum() / total_volume
        return vw_return

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
        def safe_round(value, decimals=4):
            """Safely round a value, returning None if value is None"""
            return round(value, decimals) if value is not None else None

        # Calculate MACD values (returns tuple)
        macd_result = self.macd(macd_fast, macd_slow, macd_signal)

        return MomentumFactorMetrics(
            one_month_return=safe_round(self.one_month_return()),
            three_month_return=safe_round(self.three_month_return(skip=three_month_skip)),
            six_month_return=safe_round(self.six_month_return(skip=six_month_skip)),
            twelve_month_return_ex1m=safe_round(self.twelve_month_return_ex1m()),
            pct_from_52w_high=safe_round(self.pct_from_52w_high(window=window_52w)),
            sma_ratio=safe_round(self.sma_ratio(fast=sma_fast, slow=sma_slow)),
            sma_50=safe_round(self.sma_50()),
            sma_200=safe_round(self.sma_200()),
            macd_value=safe_round(macd_result[0]),
            macd_signal=safe_round(macd_result[1]),
            rsi=safe_round(self.rsi(window=rsi_window)),
            idiosyncratic_momentum=safe_round(self.idiosyncratic_momentum(idio_lookback)),
            sector_idiosyncratic_momentum=safe_round(self.sector_idiosyncratic_momentum(sector_idio_lookback)),
            volume_adjusted_momentum=safe_round(self.volume_adjusted_momentum(vol_adj_lookback))
        )


if __name__ == "__main__":
    from backend.src.repositories.price_data import get_price_data_daily
    from datetime import datetime, timedelta
    
    # Fetch equity data - use uppercase ticker
    ticker = 'AAPL'  # Changed to uppercase
    start_date = datetime.now() - timedelta(days=730)
    end_date = datetime.now()
    
    print(f"Fetching data for {ticker} from {start_date} to {end_date}")
    
    equity_data = get_price_data_daily(ticker, start_date=start_date, end_date=end_date)
    
    if equity_data.empty:
        print(f"Error: No equity data found for '{ticker}'")
        # Try with lowercase
        ticker_lower = ticker.lower()
        print(f"Trying with lowercase: '{ticker_lower}'")
        equity_data = get_price_data_daily(ticker_lower, start_date=start_date, end_date=end_date)
        
    if not equity_data.empty:
        price_data = equity_data['close']
        volume_data = equity_data['volume']
        
        # Fetch SPY data
        spy_df = get_price_data_daily('SPY', start_date=start_date, end_date=end_date)
        spy_price_data = spy_df['close'] if not spy_df.empty else None
        
        # Fetch sector ETF data  
        sector_df = get_price_data_daily('XLF', start_date=start_date, end_date=end_date)
        sector_price_data = sector_df['close'] if not sector_df.empty else None

        momentum_factors = MomentumFactors(price_data, volume_data, spy_price_data, sector_price_data)
        mf = momentum_factors.calc_all()
        print(mf.model_dump())
        print(type(mf.model_dump()))
    else:
        print("No data found for ticker")


