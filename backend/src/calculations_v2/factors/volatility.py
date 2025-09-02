from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import scipy.stats


class VolatilityFactors:
    """Volatility-oriented factors from price series and optional market series.

    Metrics: realized vol (30/90/any), daily vol, beta(1y), idiosyncratic vol,
    downside deviation, max drawdown(1y), ATR/price ratio, variance ratio (3m/12m),
    skewness, kurtosis, GARCH(1,1) fallback to EWMA, and annualized volatility.
    """

    def __init__(self, price_series: pd.Series, spy_price_series: Optional[pd.Series] = None):
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

    def realized_vol(self, days: int) -> Optional[float]:
        if len(self.returns) < days:
            return None
        return float(self.returns.iloc[-days:].std() * np.sqrt(252))

    def realized_vol_30d(self) -> Optional[float]:
        return self.realized_vol(30)

    def realized_vol_90d(self) -> Optional[float]:
        return self.realized_vol(90)

    def annualized_volatility(self, lookback_days: int) -> Optional[float]:
        returns_period = self.returns.iloc[-lookback_days:]
        return float(returns_period.std() * np.sqrt(252))

    def daily_return_volatility(self) -> Optional[float]:
        if len(self.returns) < 2:
            return None
        return float(self.returns.std(ddof=1))

    def beta_1yr(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        combined = pd.concat([self.returns, self.spy_returns], axis=1, keys=["asset", "spy"]).dropna()
        if len(combined) < 30:
            return None
        lookback = min(252, len(combined))
        recent = combined.iloc[-lookback:]
        cov = np.cov(recent["asset"], recent["spy"])[0, 1]
        var = np.var(recent["spy"], ddof=1)
        return float(cov / var) if var != 0 else None

    def idiosyncratic_vol(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns, self.spy_returns], axis=1, keys=["asset", "spy"]).dropna()
        if len(combined) < 30:
            return None
        lookback = min(252, len(combined))
        recent = combined.iloc[-lookback:]
        y = recent["asset"]
        x = sm.add_constant(recent["spy"])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float(resid.std(ddof=1) * np.sqrt(252))

    def downside_dev_30d(self) -> Optional[float]:
        if len(self.returns) < 30:
            return None
        r = self.returns.iloc[-30:]
        downside = np.minimum(r, 0)
        return float(np.sqrt(np.mean(downside ** 2)) * np.sqrt(252))

    def max_drawdown_1yr(self) -> Optional[float]:
        if len(self.prices) < 30:
            return None
        lookback = min(252, len(self.prices))
        p = self.prices.iloc[-lookback:]
        cum_max = p.expanding().max()
        safe = cum_max.replace(0, np.nan)
        dd = (p - safe) / safe
        mdd = dd.min()
        return float(mdd) if not np.isnan(mdd) else None

    def atr_price_ratio(self, period: int = 14) -> Optional[float]:
        if len(self.prices) < period + 1:
            return None
        high = self.prices
        low = self.prices
        close = self.prices
        close_prev = close.shift(1)
        tr = np.maximum(high - low, np.maximum(abs(high - close_prev), abs(low - close_prev)))
        atr = tr.rolling(window=period).mean().iloc[-1]
        curr = self.prices.iloc[-1]
        if curr == 0:
            return None
        return float(atr / curr)

    def variance_ratio_3m_12m(self) -> Optional[float]:
        if len(self.returns) < 63:
            return None
        short = self.returns.iloc[-63:]
        long_lookback = min(252, len(self.returns))
        if long_lookback < 126:
            long_lookback = len(self.returns)
        long = self.returns.iloc[-long_lookback:]
        var_s = float(short.var())
        var_l = float(long.var())
        if var_l == 0:
            return None
        return float(var_s / var_l)

    def skewness(self, lookback: int = 252) -> Optional[float]:
        if len(self.returns) < 30:
            return None
        actual = min(lookback, len(self.returns))
        r = self.returns.iloc[-actual:]
        s = scipy.stats.skew(r)
        return float(s) if not np.isnan(s) else None

    def kurtosis(self, lookback: int = 252) -> Optional[float]:
        if len(self.returns) < 30:
            return None
        actual = min(lookback, len(self.returns))
        r = self.returns.iloc[-actual:]
        k = scipy.stats.kurtosis(r)
        return float(k) if not np.isnan(k) else None

    def garch_forecast(self) -> Optional[float]:
        if len(self.returns) < 100:
            return None
        try:
            from arch import arch_model
            r_pct = self.returns.iloc[-252:] * 100
            model = arch_model(r_pct, vol='Garch', p=1, q=1, rescale=False)
            fitted = model.fit(disp='off')
            f = fitted.forecast(horizon=1)
            next_var = f.variance.iloc[-1, 0]
            return float(np.sqrt(next_var / 10000 * 252))
        except Exception:
            # Fallback EWMA
            sq = self.returns.iloc[-30:] ** 2
            ewma_var = sq.ewm(alpha=0.1).mean().iloc[-1]
            return float(np.sqrt(ewma_var * 252))


