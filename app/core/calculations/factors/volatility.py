from __future__ import annotations

from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import scipy.stats
from app.core.calculations.core.helpers import zscore_series, compose_exposure
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.core.config import DEFAULT_TRADING_DAYS, DEFAULT_SECTOR_COL, DEFAULT_WINSOR_LIMITS
from app.core.calculations.factors.config import VOLATILITY_WEIGHTS, VOLATILITY_WINDOWS, MIN_SAMPLE_SIZE, MOMENTUM_LOOKBACK


class VolatilityFactors:
    """Volatility-oriented factors from price series and optional market series.

    Metrics: realized vol (30/90/any), daily vol, beta(1y), idiosyncratic vol,
    downside deviation, max drawdown(1y), ATR/price ratio, variance ratio (3m/12m),
    skewness, kurtosis, GARCH(1,1) fallback to EWMA, and annualized volatility.
    """

    def __init__(
        self,
        price_series: pd.Series,
        spy_price_series: Optional[pd.Series] = None,
        as_of_date: Optional[datetime] = None,
        filing_lag_days: int = 0,
    ):
        if price_series is None or price_series.empty:
            raise ValueError("Price series cannot be None or empty.")
        # As-of alignment
        cutoff_dt: Optional[datetime] = None
        if as_of_date is not None:
            cutoff_dt = as_of_date - timedelta(days=int(filing_lag_days) if filing_lag_days and filing_lag_days > 0 else 0)
        p = price_series.astype(float).copy()
        if cutoff_dt is not None:
            try:
                p = p.loc[p.index <= cutoff_dt]
            except Exception:
                pass
        self.prices = p
        # Log returns
        self.returns = np.log(self.prices).diff().dropna()
        if spy_price_series is not None and not spy_price_series.empty:
            sp = spy_price_series.astype(float).copy()
            if cutoff_dt is not None:
                try:
                    sp = sp.loc[sp.index <= cutoff_dt]
                except Exception:
                    pass
            self.spy_prices = sp
            self.spy_returns = np.log(self.spy_prices).diff().dropna()
        else:
            self.spy_prices = None
            self.spy_returns = None

    def realized_vol(self, days: int) -> Optional[float]:
        r = self.returns.iloc[-days:]
        if len(r) < max(20, int(days * 0.2)):
            return None
        return float(r.std(ddof=1) * np.sqrt(DEFAULT_TRADING_DAYS))

    def realized_vol_30d(self) -> Optional[float]:
        return self.realized_vol(VOLATILITY_WINDOWS["30D"])

    def realized_vol_90d(self) -> Optional[float]:
        return self.realized_vol(VOLATILITY_WINDOWS["90D"])

    def annualized_volatility(self, lookback_days: int) -> Optional[float]:
        r = self.returns.iloc[-lookback_days:]
        if len(r) < max(20, int(lookback_days * 0.2)):
            return None
        vol = RiskCalculator.annualized_volatility(r)
        return float(vol) if np.isfinite(vol) else None

    def daily_return_volatility(self) -> Optional[float]:
        if len(self.returns) < 2:
            return None
        return float(self.returns.std(ddof=1))

    def realized_vol_252(self) -> Optional[float]:
        return self.realized_vol(VOLATILITY_WINDOWS["252D"])

    def beta_1yr(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        combined = pd.concat([self.returns.rename("asset"), self.spy_returns.rename("spy")], axis=1).dropna()
        if len(combined) < MIN_SAMPLE_SIZE:
            return None
        lookback = min(VOLATILITY_WINDOWS["BETA_LOOKBACK"], len(combined))
        recent = combined.iloc[-lookback:]
        b = RiskCalculator.beta(recent["asset"], recent["spy"])
        return float(b) if np.isfinite(b) else None

    def idiosyncratic_vol(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns.rename("asset"), self.spy_returns.rename("spy")], axis=1).dropna()
        if len(combined) < MIN_SAMPLE_SIZE:
            return None
        lookback = min(DEFAULT_TRADING_DAYS, len(combined))
        recent = combined.iloc[-lookback:]
        y = recent["asset"]
        x = sm.add_constant(recent["spy"])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float(resid.std(ddof=1) * np.sqrt(DEFAULT_TRADING_DAYS))

    def downside_dev(self, days: int = DEFAULT_TRADING_DAYS, hurdle: float = 0.0) -> Optional[float]:
        r = self.returns.iloc[-days:]
        if len(r) < max(20, int(days * 0.2)):
            return None
        downside = np.minimum(r - float(hurdle), 0.0)
        return float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(DEFAULT_TRADING_DAYS))

    def downside_dev_30d(self) -> Optional[float]:
        return self.downside_dev(days=VOLATILITY_WINDOWS["30D"], hurdle=0.0)

    def downside_dev_252(self) -> Optional[float]:
        return self.downside_dev(days=VOLATILITY_WINDOWS["252D"], hurdle=0.0)

    def max_drawdown_1yr(self) -> Optional[float]:
        if len(self.prices) < MIN_SAMPLE_SIZE:
            return None
        lookback = min(DEFAULT_TRADING_DAYS, len(self.prices))
        p = self.prices.iloc[-lookback:]
        cum_max = p.expanding().max()
        safe = cum_max.replace(0, np.nan)
        dd = (p - safe) / safe
        mdd = dd.min()
        return float(abs(mdd)) if not np.isnan(mdd) else None

    def atr_price_ratio(
        self,
        period: int = 14,
        high: Optional[pd.Series] = None,
        low: Optional[pd.Series] = None,
        close: Optional[pd.Series] = None,
    ) -> Optional[float]:
        # Require real OHLC; do not approximate from close-only
        if high is None or low is None or close is None:
            return None
        if len(close) < period + 1:
            return None
        high = high.astype(float).reindex(close.index)
        low = low.astype(float).reindex(close.index)
        close = close.astype(float)
        close_prev = close.shift(1)
        tr = np.maximum(high - low, np.maximum(abs(high - close_prev), abs(low - close_prev)))
        atr = tr.rolling(window=period).mean().iloc[-1]
        curr = close.iloc[-1]
        if curr == 0 or np.isnan(atr):
            return None
        return float(atr / curr)

    def variance_ratio_3m_12m(self) -> Optional[float]:
        if len(self.returns) < MOMENTUM_LOOKBACK["3M"]:
            return None
        short = self.returns.iloc[-MOMENTUM_LOOKBACK["3M"]:]
        long_lookback = min(DEFAULT_TRADING_DAYS, len(self.returns))
        if long_lookback < MOMENTUM_LOOKBACK["6M"]:
            long_lookback = len(self.returns)
        long = self.returns.iloc[-long_lookback:]
        var_s = float(short.var())
        var_l = float(long.var())
        if var_l == 0:
            return None
        return float(var_s / var_l)

    def short_long_vol_ratio(self, short_days: int = None, long_days: int = None) -> Optional[float]:
        if short_days is None:
            short_days = MOMENTUM_LOOKBACK["3M"]
        if long_days is None:
            long_days = DEFAULT_TRADING_DAYS
        short_vol = self.realized_vol(short_days)
        long_vol = self.realized_vol(long_days)
        if short_vol is None or long_vol is None or long_vol <= 0:
            return None
        ratio = float(short_vol / long_vol)
        # Clip extremes for stability
        return float(min(max(ratio, 0.25), 4.0))

    def skewness(self, lookback: int = DEFAULT_TRADING_DAYS) -> Optional[float]:
        if len(self.returns) < MIN_SAMPLE_SIZE:
            return None
        actual = min(lookback, len(self.returns))
        r = self.returns.iloc[-actual:]
        s = scipy.stats.skew(r)
        return float(s) if not np.isnan(s) else None

    def kurtosis(self, lookback: int = DEFAULT_TRADING_DAYS) -> Optional[float]:
        if len(self.returns) < MIN_SAMPLE_SIZE:
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
            r_pct = self.returns.iloc[-DEFAULT_TRADING_DAYS:] * 100
            model = arch_model(r_pct, vol='Garch', p=1, q=1, rescale=False)
            fitted = model.fit(disp='off')
            f = fitted.forecast(horizon=1)
            next_var = f.variance.iloc[-1, 0]
            return float(np.sqrt(next_var / 10000 * DEFAULT_TRADING_DAYS))
        except Exception:
            # Fallback EWMA
            return self.ewma_vol(lam=0.94, days=DEFAULT_TRADING_DAYS)

    def ewma_vol(self, lam: float = 0.94, days: int = DEFAULT_TRADING_DAYS) -> Optional[float]:
        r = self.returns.iloc[-days:]
        if len(r) < 20:
            return None
        # Compute EWMA variance via decay lambda
        sq = np.square(r.values)
        var = 0.0
        weight = 1.0
        norm = 0.0
        # Oldest to newest
        for x in sq:
            var = lam * var + (1.0 - lam) * x
            norm = lam * norm + (1.0 - lam)
        if norm <= 0.0:
            return None
        ewma_var = var  # Already incorporates normalization via recursion
        return float(np.sqrt(ewma_var) * np.sqrt(DEFAULT_TRADING_DAYS))
    
    # ------------------------- Cross-sectional API ------------------------- #
    def compute_attributes(self) -> Dict[str, float]:
        attrs: Dict[str, float] = {
            "beta": np.nan,
            "idio_vol": np.nan,
            "realized_vol": np.nan,
            "downside_dev": np.nan,
            "svlr": np.nan,
        }
        try:
            b = self.beta_1yr()
            if b is not None:
                attrs["beta"] = float(b)
        except Exception:
            pass
        try:
            iv = self.idiosyncratic_vol()
            if iv is not None:
                attrs["idio_vol"] = float(iv)
        except Exception:
            pass
        try:
            rv = self.realized_vol_252()
            if rv is not None:
                attrs["realized_vol"] = float(rv)
        except Exception:
            pass
        try:
            dd = self.downside_dev_252()
            if dd is not None:
                attrs["downside_dev"] = float(dd)
        except Exception:
            pass
        try:
            ratio = self.short_long_vol_ratio()
            if ratio is not None:
                attrs["svlr"] = float(ratio)
        except Exception:
            pass
        # Normalize invalids
        for k, v in list(attrs.items()):
            if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                attrs[k] = np.nan
        return attrs

    @classmethod
    def compose_volatility_exposure(
        cls,
        df: pd.DataFrame,
        sector_col: str = DEFAULT_SECTOR_COL,
        winsor_limits: tuple[float, float] = DEFAULT_WINSOR_LIMITS,
        weights: Optional[Dict[str, float]] = None,
        mode: str = "Vol",
        output_col: str = "vol_exposure_raw",
    ) -> pd.DataFrame:
        """Compose Volatility exposure with winsorization and sector z-score.

        Expected columns: beta, idio_vol, realized_vol, downside_dev, svlr, sector.
        """
        if df is None or df.empty:
            return df
        base_cols = ["idio_vol", "realized_vol", "downside_dev", "svlr"]
        if not weights:
            weights = VOLATILITY_WEIGHTS
        df = compose_exposure(
            df,
            cols=base_cols,
            weights=weights,
            sector_col=sector_col,
            winsor_limits=winsor_limits,
            output_col=output_col,
        )
        # LowVol option flips sign
        if isinstance(mode, str) and mode.lower().startswith("low"):
            df[output_col] = -df[output_col]
        return df

    @classmethod
    def orthogonalize_volatility(
        cls,
        df: pd.DataFrame,
        exposure_col: str = "vol_exposure_raw",
        beta_col: str = "beta",
        size_col: Optional[str] = None,
        output_col: str = "vol_exposure",
    ) -> pd.DataFrame:
        """Orthogonalize volatility exposure against Beta (and Size if provided)."""
        if df is None or df.empty or exposure_col not in df.columns or beta_col not in df.columns:
            return df
        exp_z = zscore_series(df[exposure_col].astype(float))
        # If beta missing entirely, fallback
        if df[beta_col].isna().all():
            df[output_col] = exp_z
            return df
        # Build design matrix
        X_cols = {"const": 1.0, "beta_z": zscore_series(df[beta_col].astype(float))}
        if size_col and size_col in df.columns:
            X_cols["size_z"] = zscore_series(df[size_col].astype(float))
        X0 = pd.DataFrame(X_cols)
        m = pd.concat([exp_z.rename("y"), X0], axis=1).dropna()
        if m.empty:
            df[output_col] = exp_z
            return df
        Y = m["y"].values
        X = m.drop(columns=["y"]).values
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
            fitted = X @ beta
            resid = Y - fitted
            df[output_col] = np.nan
            df.loc[m.index, output_col] = resid
        except Exception:
            df[output_col] = exp_z
        return df

    def calc_all(self) -> Dict[str, float]:
        """Calculate all volatility factors for the ticker.
        
        Returns:
            Dictionary containing all volatility factor metrics (as decimals).
        """
        round_factor = 4
        results = {
            # Realized volatility
            "realized_vol_30d": round(self.realized_vol_30d() or np.nan, round_factor),
            "realized_vol_90d": round(self.realized_vol_90d() or np.nan, round_factor),
            "realized_vol_252d": round(self.realized_vol_252() or np.nan, round_factor),
            "daily_return_volatility": round(self.daily_return_volatility() or np.nan, round_factor),
            
            # Annualized volatility
            "annualized_vol_30d": round(self.annualized_volatility(VOLATILITY_WINDOWS["30D"]) or np.nan, round_factor),
            "annualized_vol_90d": round(self.annualized_volatility(VOLATILITY_WINDOWS["90D"]) or np.nan, round_factor),
            "annualized_vol_252d": round(self.annualized_volatility(VOLATILITY_WINDOWS["252D"]) or np.nan, round_factor),
            
            # Market-related
            "beta_1yr": round(self.beta_1yr() or np.nan, round_factor),
            "idiosyncratic_vol": round(self.idiosyncratic_vol() or np.nan, round_factor),
            
            # Downside risk
            "downside_dev_30d": round(self.downside_dev_30d() or np.nan, round_factor),
            "downside_dev_252d": round(self.downside_dev_252() or np.nan, round_factor),
            
            # Drawdown
            "max_drawdown_1yr": round(self.max_drawdown_1yr() or np.nan, round_factor),
            
            # Volatility ratios
            "variance_ratio_3m_12m": round(self.variance_ratio_3m_12m() or np.nan, round_factor),
            "short_long_vol_ratio": round(self.short_long_vol_ratio() or np.nan, round_factor),
            
            # Higher moments
            "skewness": round(self.skewness() or np.nan, round_factor),
            "kurtosis": round(self.kurtosis() or np.nan, round_factor),
            
            # GARCH/EWMA forecast
            "garch_forecast": round(self.garch_forecast() or np.nan, round_factor),
            "ewma_vol": round(self.ewma_vol() or np.nan, round_factor),
        }
        
        # Clean up NaN/Inf values
        for key, value in results.items():
            if value is None or np.isinf(value) or (isinstance(value, float) and np.isnan(value)):
                results[key] = np.nan
                
        return results
    
    @classmethod
    def calc_all_bulk(
        cls,
        tickers: list[str],
        start_date: datetime,
        end_date: datetime,
        market_ticker: str = "SPY",
        as_of_date: Optional[datetime] = None,
        filing_lag_days: int = 0
    ) -> pd.DataFrame:
        """Calculate all volatility factors for multiple tickers using bulk data fetching.

        Args:
            tickers: List of ticker symbols
            start_date: Start date for price data
            end_date: End date for price data
            market_ticker: Market benchmark ticker for beta calculations
            as_of_date: Optional as-of date for calculations
            filing_lag_days: Filing lag in days

        Returns:
            DataFrame with tickers as rows and volatility metrics as columns
        """
        from app.repositories.price_data import fetch_bulk_price_data_for_tickers

        # Bulk fetch price data for all tickers plus market
        all_tickers = list(tickers) + [market_ticker]
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        price_map = fetch_bulk_price_data_for_tickers(all_tickers, start_str, end_str, frequency='daily')

        # Get market prices
        spy_px = price_map.get(market_ticker)

        # Calculate volatility factors for each ticker
        all_results = {}
        for ticker in tickers:
            ticker = ticker.upper()
            if ticker in price_map:
                try:
                    px = price_map[ticker]

                    # Create VolatilityFactors instance
                    vf = cls(
                        price_series=px,
                        spy_price_series=spy_px,
                        as_of_date=as_of_date,
                        filing_lag_days=filing_lag_days
                    )
                    all_results[ticker] = vf.calc_all()
                except Exception as e:
                    print(f"Error calculating volatility factors for {ticker}: {e}")
                    all_results[ticker] = {}

        # Convert to DataFrame
        df = pd.DataFrame(all_results).T
        return df

if __name__ == "__main__":
    # Lightweight smoke test for attributes and composite
    from app.repositories.price_data import fetch_bulk_price_data_for_tickers
    from app.utils.time_utils import get_current_utc_time
    try:
        test_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        end = get_current_utc_time()
        start = end - timedelta(days=400)
        start_str = start.strftime('%Y-%m-%d')
        end_str = end.strftime('%Y-%m-%d')
        series_map = fetch_bulk_price_data_for_tickers(test_tickers + ["SPY"], start_str, end_str, frequency='daily')
        rows = []
        for t in test_tickers:
            try:
                px = series_map.get(t)
                mkt = series_map.get("SPY")
                if px is None or mkt is None:
                    continue
                vf = VolatilityFactors(px, mkt)
                attrs = vf.compute_attributes()
                rows.append({"ticker": t, **attrs})
            except Exception as e:
                print(f"[warn] Failed computing attributes for {t}: {e}")
        frame = pd.DataFrame(rows)
        frame = VolatilityFactors.compose_volatility_exposure(frame)
        frame = VolatilityFactors.orthogonalize_volatility(frame, exposure_col="vol_exposure_raw", beta_col="beta")
        cols = [
            "ticker",
            "beta",
            "idio_vol",
            "realized_vol",
            "downside_dev",
            "svlr",
            "vol_exposure_raw",
            "vol_exposure",
        ]
        print(frame[cols].to_string(index=False))
    except Exception as e:
        print(f"[error] Smoke test failed: {e}")


