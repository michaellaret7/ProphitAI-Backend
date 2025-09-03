from __future__ import annotations

from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import scipy.stats
from backend.src.calculations_v2.factors.growth import GrowthFactors


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
        return float(r.std(ddof=1) * np.sqrt(252))

    def realized_vol_30d(self) -> Optional[float]:
        return self.realized_vol(30)

    def realized_vol_90d(self) -> Optional[float]:
        return self.realized_vol(90)

    def annualized_volatility(self, lookback_days: int) -> Optional[float]:
        r = self.returns.iloc[-lookback_days:]
        if len(r) < max(20, int(lookback_days * 0.2)):
            return None
        return float(r.std(ddof=1) * np.sqrt(252))

    def daily_return_volatility(self) -> Optional[float]:
        if len(self.returns) < 2:
            return None
        return float(self.returns.std(ddof=1))

    def realized_vol_252(self) -> Optional[float]:
        return self.realized_vol(252)

    def beta_1yr(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        combined = pd.concat([self.returns.rename("asset"), self.spy_returns.rename("spy")], axis=1).dropna()
        if len(combined) < 30:
            return None
        lookback = min(252, len(combined))
        recent = combined.iloc[-lookback:]
        cov = np.cov(recent["asset"], recent["spy"], ddof=1)[0, 1]
        var = np.var(recent["spy"], ddof=1)
        return float(cov / var) if var != 0 else None

    def idiosyncratic_vol(self) -> Optional[float]:
        if self.spy_returns is None:
            return None
        import statsmodels.api as sm
        combined = pd.concat([self.returns.rename("asset"), self.spy_returns.rename("spy")], axis=1).dropna()
        if len(combined) < 30:
            return None
        lookback = min(252, len(combined))
        recent = combined.iloc[-lookback:]
        y = recent["asset"]
        x = sm.add_constant(recent["spy"])
        model = sm.OLS(y, x, missing="drop").fit()
        resid = model.resid
        return float(resid.std(ddof=1) * np.sqrt(252))

    def downside_dev(self, days: int = 252, hurdle: float = 0.0) -> Optional[float]:
        r = self.returns.iloc[-days:]
        if len(r) < max(20, int(days * 0.2)):
            return None
        downside = np.minimum(r - float(hurdle), 0.0)
        return float(np.sqrt(np.mean(np.square(downside))) * np.sqrt(252))

    def downside_dev_30d(self) -> Optional[float]:
        return self.downside_dev(days=30, hurdle=0.0)

    def downside_dev_252(self) -> Optional[float]:
        return self.downside_dev(days=252, hurdle=0.0)

    def max_drawdown_1yr(self) -> Optional[float]:
        if len(self.prices) < 30:
            return None
        lookback = min(252, len(self.prices))
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

    def short_long_vol_ratio(self, short_days: int = 63, long_days: int = 252) -> Optional[float]:
        short_vol = self.realized_vol(short_days)
        long_vol = self.realized_vol(long_days)
        if short_vol is None or long_vol is None or long_vol <= 0:
            return None
        ratio = float(short_vol / long_vol)
        # Clip extremes for stability
        return float(min(max(ratio, 0.25), 4.0))

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
            return self.ewma_vol(lam=0.94, days=252)

    def ewma_vol(self, lam: float = 0.94, days: int = 252) -> Optional[float]:
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
        return float(np.sqrt(ewma_var) * np.sqrt(252))

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
        sector_col: str = "sector",
        winsor_limits: tuple[float, float] = (0.025, 0.025),
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
        for c in base_cols + ["beta"]:
            if c not in df.columns:
                df[c] = np.nan
        lw, uw = winsor_limits
        # Winsorize then sector z-score
        for c in base_cols:
            df[f"{c}_w"] = GrowthFactors.winsorize_series(df[c].astype(float), lower=lw, upper=uw)
            df[f"{c}_z"] = GrowthFactors.sector_zscore(df, f"{c}_w", sector_col=sector_col)
        # Default weights
        if not weights:
            weights = {"idio_vol": 0.60, "realized_vol": 0.30, "downside_dev": 0.10, "svlr": 0.00}
        # Weighted sum
        df[output_col] = 0.0
        for key, w in weights.items():
            zcol = f"{key}_z"
            if zcol in df.columns:
                df[output_col] = df[output_col].fillna(0.0) + float(w) * df[zcol].fillna(0.0)
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
        exp_z = GrowthFactors.zscore_series(df[exposure_col].astype(float))
        # If beta missing entirely, fallback
        if df[beta_col].isna().all():
            df[output_col] = exp_z
            return df
        # Build design matrix
        X_cols = {"const": 1.0, "beta_z": GrowthFactors.zscore_series(df[beta_col].astype(float))}
        if size_col and size_col in df.columns:
            X_cols["size_z"] = GrowthFactors.zscore_series(df[size_col].astype(float))
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

if __name__ == "__main__":
    # Lightweight smoke test for attributes and composite
    from backend.src.calculations_v2.core.data_service import DataService
    try:
        test_tickers = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA"]
        ds = DataService()
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=400)
        series_map = ds.get_bulk_close_series(test_tickers + ["SPY"], start, end)
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


