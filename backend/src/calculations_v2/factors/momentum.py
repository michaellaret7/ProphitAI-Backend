from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
import pandas as pd


class MomentumFactors:
    """Price-based momentum factors operating on simple Series inputs.

    Computes: 1/3/6/12-month returns (with optional 1M skip), % from 52w high,
    SMA ratio (fast/slow), SMA_50, SMA_200, MACD (value/signal), RSI,
    idiosyncratic momentum vs market or sector (optional), volume-adjusted momentum (optional).
    """

    def __init__(
        self,
        price_series: pd.Series,
        volume_series: Optional[pd.Series] = None,
        market_price_series: Optional[pd.Series] = None,
        sector_price_series: Optional[pd.Series] = None,
    ):
        self.prices = price_series.astype(float)
        self.returns = self.prices.pct_change(fill_method=None).dropna()
        self.volumes = volume_series.astype(float).reindex(self.prices.index) if volume_series is not None else None

        self.market_prices = market_price_series.astype(float).reindex(self.prices.index) if market_price_series is not None else None
        self.market_returns = self.market_prices.pct_change(fill_method=None).dropna() if self.market_prices is not None else None

        self.sector_prices = sector_price_series.astype(float).reindex(self.prices.index) if sector_price_series is not None else None
        self.sector_returns = self.sector_prices.pct_change(fill_method=None).dropna() if self.sector_prices is not None else None

    # ------------------------- helpers ------------------------- #
    def _total_return(self, lookback: int, skip: int = 0) -> Optional[float]:
        if len(self.prices) < lookback + skip:
            return None
        past = self.prices.iloc[-(lookback + skip)]
        curr = self.prices.iloc[-1]
        if past is None or past == 0:
            return None
        return float(curr / past - 1.0)

    # ------------------------- returns windows ------------------------- #
    def one_month_return(self) -> Optional[float]:
        return self._total_return(lookback=21, skip=0)

    def three_month_return(self, skip: int = 21) -> Optional[float]:
        return self._total_return(lookback=63, skip=skip)

    def six_month_return(self, skip: int = 21) -> Optional[float]:
        return self._total_return(lookback=126, skip=skip)

    def twelve_month_return_ex1m(self) -> Optional[float]:
        return self._total_return(lookback=252, skip=21)

    # ------------------------- 52w high ------------------------- #
    def pct_from_52w_high(self, window: int = 252) -> Optional[float]:
        if len(self.prices) < window:
            return None
        highest = self.prices.iloc[-window:].max()
        curr = self.prices.iloc[-1]
        if highest == 0:
            return None
        return float(curr / highest - 1.0)

    # ------------------------- SMA ratio ------------------------- #
    def sma_ratio(self, fast: int = 50, slow: int = 200, latest_only: bool = True):
        if slow <= fast:
            raise ValueError("slow must be > fast")
        sma_f = self.prices.rolling(fast).mean()
        sma_s = self.prices.rolling(slow).mean()
        ratio = sma_f / sma_s - 1.0
        return ratio.iloc[-1] if latest_only else ratio

    def sma_50(self) -> Optional[float]:
        if len(self.prices) < 50:
            return None
        return float(self.prices.rolling(50).mean().iloc[-1])

    def sma_200(self) -> Optional[float]:
        if len(self.prices) < 200:
            return None
        return float(self.prices.rolling(200).mean().iloc[-1])

    # ------------------------- MACD ------------------------- #
    def macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[Optional[float], Optional[float]]:
        if len(self.prices) < slow_period + signal_period:
            return None, None
        ema_fast = self.prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = self.prices.ewm(span=slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])

    # ------------------------- RSI ------------------------- #
    def rsi(self, window: int = 14) -> Optional[float]:
        if len(self.prices) < window + 1:
            return None
        delta = self.prices.diff().dropna()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        avg_up = up.ewm(com=window - 1, adjust=False).mean()
        avg_down = down.ewm(com=window - 1, adjust=False).mean().replace(0, np.nan)
        if avg_down.isnull().all():
            return 0.0
        rs = avg_up / avg_down
        rsi_series = 100.0 - (100.0 / (1.0 + rs))
        return float(rsi_series.iloc[-1])

    # ------------------------- Idiosyncratic Momentum ------------------------- #
    def idiosyncratic_momentum(self, lookback: int = 60) -> Optional[float]:
        if self.market_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns, self.market_returns], axis=1, keys=["asset", "market"]).dropna()
        if len(combined) < lookback:
            return None
        y = combined["asset"].iloc[-lookback:]
        x = sm.add_constant(combined["market"].iloc[-lookback:])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float((1 + resid).prod() - 1)

    def sector_idiosyncratic_momentum(self, lookback: int = 60) -> Optional[float]:
        if self.sector_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns, self.sector_returns], axis=1, keys=["asset", "sector"]).dropna()
        if len(combined) < lookback:
            return None
        y = combined["asset"].iloc[-lookback:]
        x = sm.add_constant(combined["sector"].iloc[-lookback:])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float((1 + resid).prod() - 1)

    # ------------------------- Volume-Adjusted Momentum ------------------------- #
    def volume_adjusted_momentum(self, lookback: int = 60) -> Optional[float]:
        if self.volumes is None:
            return None
        if len(self.returns) < lookback + 1:
            return None
        window_ret = self.returns.iloc[-lookback:]
        window_vol = self.volumes.loc[window_ret.index]
        total_vol = window_vol.sum()
        if total_vol == 0 or total_vol is None:
            return None
        vw_return = float((window_ret * window_vol).sum() / total_vol)
        return vw_return


