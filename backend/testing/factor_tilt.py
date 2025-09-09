from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

from backend.src.calculations_v2.core.data_service import DataService
from backend.src.calculations_v2.factors import (
    ValueFactors,
    GrowthFactors,
    MomentumFactors,
    QualityFactors,
    VolatilityFactors,
)
import warnings; warnings.filterwarnings("ignore", category=FutureWarning)


def _compute_exposure_frame(
    factor: str,
    tickers: list[str],
    ds: DataService,
    start: datetime,
    end: datetime,
    price_map: Optional[Dict[str, pd.Series]] = None,
) -> Tuple[pd.DataFrame, str]:
    """Return a DataFrame with per-ticker attributes and an exposure column for the requested factor.

    Returns (frame, exposure_col_name).
    """
    factor_l = factor.strip().lower()

    if factor_l == "value":
        # Bulk prefetch fundamentals (ValueFactors will hit cache quickly)
        try:
            ds.get_bulk_fundamentals(tickers)
        except Exception:
            pass
        rows = []
        def compute_value_attrs(t: str) -> dict:
            try:
                vf = ValueFactors(ticker=t, data_service=ds, as_of_date=end)
                attrs = vf.compute_attributes()
                return {"ticker": t, **attrs}
            except Exception:
                return {"ticker": t}
        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as ex_pool:
            futures = {ex_pool.submit(compute_value_attrs, t): t for t in tickers}
            for fut in as_completed(futures):
                rows.append(fut.result())
        df = pd.DataFrame(rows)
        df = ValueFactors.compose_value_exposure(df)
        df = ValueFactors.orthogonalize_value(df)
        return df, "value_exposure"

    if factor_l == "growth":
        # Bulk prefetch fundamentals and inject to GrowthFactors to avoid per-ticker fetch
        try:
            fundamentals = ds.get_bulk_fundamentals(tickers)
        except Exception:
            fundamentals = {}
        rows = []
        def compute_growth_attrs(t: str) -> dict:
            try:
                if t in fundamentals:
                    gf = GrowthFactors(ticker=t, data_service=ds, fundamental_data=fundamentals[t])
                else:
                    gf = GrowthFactors(ticker=t, data_service=ds)
                attrs = gf.compute_attributes()
                return {"ticker": t, **attrs}
            except Exception:
                return {"ticker": t}
        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as ex_pool:
            futures = {ex_pool.submit(compute_growth_attrs, t): t for t in tickers}
            for fut in as_completed(futures):
                rows.append(fut.result())
        df = pd.DataFrame(rows)
        df = GrowthFactors.compose_growth_exposure(df)
        df = GrowthFactors.orthogonalize_growth(df)
        return df, "growth_exposure"

    if factor_l == "momentum":
        # Fetch prices once (or reuse provided)
        series_map = price_map or ds.get_bulk_close_series(list(tickers) + ["SPY"], start, end)
        spy_px = series_map.get("SPY")
        rows = []
        def compute_mom_attrs(t: str) -> dict:
            try:
                px = series_map.get(t)
                if px is None or px.empty:
                    return {"ticker": t}
                divs = None  # price-only for speed
                mkt = spy_px.reindex(px.index) if spy_px is not None else None
                mf = MomentumFactors(price_series=px, dividends_series=divs, market_price_series=mkt)
                attrs = mf.compute_attributes()
                return {"ticker": t, **attrs}
            except Exception:
                return {"ticker": t}
        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as ex_pool:
            futures = {ex_pool.submit(compute_mom_attrs, t): t for t in tickers}
            for fut in as_completed(futures):
                rows.append(fut.result())
        df = pd.DataFrame(rows)
        df = MomentumFactors.compose_momentum_exposure(df)
        df = MomentumFactors.orthogonalize_momentum(df)
        return df, "momentum_exposure"

    if factor_l == "quality":
        # Bulk prefetch fundamentals (QualityFactors will read from cache)
        try:
            ds.get_bulk_fundamentals(tickers)
        except Exception:
            pass
        rows = []
        def compute_quality_attrs(t: str) -> dict:
            try:
                qf = QualityFactors(ticker=t, data_service=ds)
                attrs = qf.compute_attributes()
                return {"ticker": t, **attrs}
            except Exception:
                return {"ticker": t}
        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as ex_pool:
            futures = {ex_pool.submit(compute_quality_attrs, t): t for t in tickers}
            for fut in as_completed(futures):
                rows.append(fut.result())
        df = pd.DataFrame(rows)
        df = QualityFactors.compose_quality_exposure(df)
        df = QualityFactors.orthogonalize_quality(df)
        return df, "quality_exposure"

    if factor_l == "volatility" or factor_l == "vol":
        # Prices for tickers and SPY for beta/idiosyncratic calculations
        series_map = price_map or ds.get_bulk_close_series(list(tickers) + ["SPY"], start, end)
        spy_px = series_map.get("SPY")
        rows = []
        def compute_vol_attrs(t: str) -> dict:
            try:
                px = series_map.get(t)
                if px is None or px.empty:
                    return {"ticker": t}
                vf = VolatilityFactors(price_series=px, spy_price_series=spy_px)
                attrs = vf.compute_attributes()
                return {"ticker": t, **attrs}
            except Exception:
                return {"ticker": t}
        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as ex_pool:
            futures = {ex_pool.submit(compute_vol_attrs, t): t for t in tickers}
            for fut in as_completed(futures):
                rows.append(fut.result())
        df = pd.DataFrame(rows)
        df = VolatilityFactors.compose_volatility_exposure(df)
        # Provide beta column when available to improve orthogonalization
        beta_col = "beta" if "beta" in df.columns else "beta"
        df[beta_col] = df.get(beta_col, np.nan)
        df = VolatilityFactors.orthogonalize_volatility(df, exposure_col="vol_exposure_raw", beta_col=beta_col)
        return df, "vol_exposure"

    raise ValueError(f"Unsupported factor: {factor}")


def portfolio_factor_tilts(
    weights: Dict[str, float],
    factor: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> Dict:
    """Compute portfolio style tilt for a given factor using calculations_v2.

    - weights: mapping of ticker -> signed portfolio weight (positive=long, negative=short)
    - factor: one of {value, growth, momentum, quality, volatility}
    - start/end: lookback window for price-based factors (defaults to ~1y)
    Returns dict with net/long/short tilts and per-ticker exposures.
    """
    if not weights:
        return {"error": "weights is empty"}

    end_dt = end or datetime.now(timezone.utc)
    start_dt = start or (end_dt - timedelta(days=365))

    ds = DataService()
    tickers = [t.upper() for t in weights.keys()]

    # Pre-fetch prices once to reuse across price-based branches
    price_map = ds.get_bulk_close_series(list(tickers) + ["SPY"], start_dt, end_dt)

    # Build exposure frame for the requested factor (reuse price_map)
    frame, exposure_col = _compute_exposure_frame(factor, tickers, ds, start_dt, end_dt, price_map)
    if frame is None or frame.empty or exposure_col not in frame.columns:
        return {"error": "failed to compute exposures"}

    # Align weights to available tickers
    w = pd.Series({t.upper(): float(weights[t]) for t in weights})
    avail = [t for t in w.index if t in set(frame.get("ticker", pd.Series(dtype=str)).astype(str))]
    if not avail:
        return {"error": "no overlap between weights and exposure tickers"}

    frame = frame.set_index("ticker").loc[[t for t in avail if t in frame.set_index("ticker").index]]
    ex = frame[exposure_col].astype(float)
    w = w.loc[avail].astype(float)

    # Net tilt (signed weights)
    net_tilt = float((w * ex.reindex(w.index)).sum()) if not w.empty else np.nan

    # Long/short tilts (leg-average exposure)
    long_mask = w > 0
    short_mask = w < 0
    long_sum = float(w[long_mask].sum()) if long_mask.any() else 0.0
    short_sum_abs = float((-w[short_mask]).sum()) if short_mask.any() else 0.0

    long_tilt = (
        float((w[long_mask] * ex.reindex(w[long_mask].index)).sum() / long_sum)
        if long_sum > 0
        else np.nan
    )
    short_tilt = (
        float(((-w[short_mask]) * ex.reindex(w[short_mask].index)).sum() / short_sum_abs)
        if short_sum_abs > 0
        else np.nan
    )

    return {
        "factor": factor,
        "exposure_col": exposure_col,
        "net_tilt": net_tilt,
        "long_tilt": long_tilt,
        "short_tilt": short_tilt,
        "per_ticker_exposure": {t: float(ex.get(t)) if t in ex.index else np.nan for t in avail},
    }


if __name__ == "__main__":
    # Simple smoke test with a few names (adjust weights as needed)
    # test_weights = {
    #     "AAPL": 0.15,
    #     "MSFT": 0.15,
    #     "NVDA": 0.10,
    #     "TSLA": -0.10,
    #     "WMT": 0.10,
    #     "XOM": -0.10,
    #     "JPM": -0.10,
    #     "META": 0.10,
    #     "AMZN": 0.10,
    # }

    portfolio_weights = {
        # Long positions
        "CL": 0.015,
        "PM": 0.07,
        "KO": 0.01,
        "WMT": 0.045,
        "BJ": 0.052,
        "MNST": 0.05,
        "INGR": 0.007,
        "ODC": 0.07,
        "CASY": 0.045,
        "SFM": 0.01,
        "VITL": 0.035,
        "DOLE": 0.018,
        "PPC": 0.025,
        "COCO": 0.03,
        "CELH": 0.027,
        "IPAR": 0.01,
        "TPB": 0.02,
        "ODD": 0.017,
        "CENT": 0.012,
        "CHEF": 0.01,
        
        # Short positions (negative weights)
        "COTY": -0.03,
        "SPB": -0.03,
        "TGT": -0.015,
        "ENR": -0.015,
        "PEP": -0.02,
        "KVUE": -0.015,
        "KLG": -0.015,
        "JJSF": -0.02,
        "MGPI": -0.01,
        "STZ": -0.01,
        "WBA": -0.025,
        "ANDE": -0.03,
        "FRPT": -0.015,
        "CPB": -0.02,
    }

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365)

    for f in ["value", "growth", "momentum", "quality", "volatility"]:
        try:
            res = portfolio_factor_tilts(portfolio_weights, f, start=start, end=end)
            print(f"\n=== {f.upper()} ===")
            if "error" in res:
                print("Error:", res["error"])    
            else:
                print(f"net: {res['net_tilt']:.3f} | long: {res['long_tilt']:.3f} | short: {res['short_tilt']:.3f}")
        except Exception as e:
            print(f"[{f}] failed: {e}")


