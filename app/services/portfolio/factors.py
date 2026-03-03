"""
Portfolio factor tilt calculation service.

Provides factor exposure analysis for portfolios considering position weights.
"""

from typing import Dict
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

from app.utils.time_utils import get_current_utc_time
from app.repositories.price_data import fetch_bulk_price_data_for_tickers
from app.repositories.fundamentals.fetchers import get_bulk_fundamentals
from app.core.calculations.factors import calc_all_factors
from app.core.calculations.models.factors import TickerFactors


# ================================
# --> Helper funcs
# ================================

# Reason: Maps factor name to (TickerFactors attribute, sub-metric names)
# so we can extract numeric values for z-scoring
FACTOR_METRIC_MAP: Dict[str, tuple[str, list[str]]] = {
    "momentum": ("momentum", ["r12_1", "r6_1", "r3_1", "risk_adj_momentum"]),
    "value": ("value", ["earnings_yield", "book_to_price", "fcf_yield", "ebitda_to_ev"]),
    "growth": ("growth", ["revenue_growth_yoy", "earnings_growth_yoy", "fcf_growth_yoy", "forward_eps_growth"]),
    "quality": ("quality", ["gross_profitability", "roe", "roa", "altman_z_score"]),
    "volatility": ("volatility", ["realized_vol_1y", "beta", "idiosyncratic_vol"]),
}


def _extract_factor_values(
    ticker_factors: Dict[str, TickerFactors],
    factor: str,
) -> Dict[str, float]:
    """Extract a composite factor score per ticker by averaging available sub-metrics.

    Returns dict of ticker -> raw composite score (before z-scoring).
    """
    attr_name, metric_names = FACTOR_METRIC_MAP[factor]
    result = {}

    for ticker, tf in ticker_factors.items():
        sub_model = getattr(tf, attr_name, None)
        if sub_model is None:
            continue

        values = []
        for metric in metric_names:
            val = getattr(sub_model, metric, None)
            if val is not None and np.isfinite(val):
                values.append(float(val))

        if values:
            result[ticker] = float(np.mean(values))

    return result


def _zscore_dict(raw: Dict[str, float]) -> Dict[str, float]:
    """Cross-sectional z-score a dict of ticker -> value."""
    if len(raw) < 2:
        return {t: 0.0 for t in raw}

    values = np.array(list(raw.values()))
    mean = np.nanmean(values)
    std = np.nanstd(values, ddof=1)

    if std == 0 or np.isnan(std):
        return {t: 0.0 for t in raw}

    return {t: float((v - mean) / std) for t, v in raw.items()}


def _nan_to_none(value) -> float | None:
    """Convert NaN/inf to None for JSON compliance."""
    if value is None:
        return None
    if isinstance(value, (float, np.floating, np.number)):
        if np.isnan(value) or np.isinf(value):
            return None
        return float(value)
    return value


class PortfolioFactorTiltService:
    """
    Service for calculating portfolio-level factor tilts.

    Analyzes portfolio exposure to specific factors (value, growth, momentum,
    quality, volatility) considering position weights (long/short).
    """

    def __init__(
        self,
        weights: Dict[str, float],
        factor: str,
        years: int = 1,
    ):
        """
        Initialize portfolio factor tilt service.

        Args:
            weights: Dictionary of ticker -> allocation (decimal, e.g., 0.25 = 25%).
                    Positive = long, negative = short.
            factor: Factor type — one of: value, growth, momentum, quality, volatility
            years: Number of years of historical data for price-based factors (default: 1)

        Raises:
            ValueError: If factor is invalid or weights is empty
        """
        if not weights:
            raise ValueError("weights cannot be empty")

        self.weights = weights
        self.factor = factor.lower()
        self.years = years

        valid_factors = list(FACTOR_METRIC_MAP.keys())
        if self.factor not in valid_factors:
            raise ValueError(f"Invalid factor: {self.factor}. Must be one of {valid_factors}")

    def calculate(self) -> Dict:
        """
        Calculate portfolio factor tilt.

        Returns:
            Dictionary with factor, net_tilt, long_tilt, short_tilt, per_ticker_exposure
        """
        end_dt = get_current_utc_time()
        start_dt = end_dt - timedelta(days=self.years * 365)

        tickers = [t.upper() for t in self.weights.keys()]

        # Fetch prices and fundamentals
        price_df = fetch_bulk_price_data_for_tickers(
            tickers + ["SPY"],
            start_dt.strftime('%Y-%m-%d'),
            end_dt.strftime('%Y-%m-%d'),
            frequency='daily'
        )
        fundamentals = get_bulk_fundamentals(tickers)

        # Build TickerFactors for each ticker
        spy_returns = None
        if "SPY" in price_df.columns:
            spy_returns = price_df["SPY"].pct_change(fill_method=None).dropna()

        ticker_factors: Dict[str, TickerFactors] = {}

        def _compute_factors(t: str) -> tuple[str, TickerFactors | None]:
            try:
                if t not in price_df.columns:
                    return t, None
                adj_close = price_df[t].dropna()
                daily_returns = adj_close.pct_change(fill_method=None).dropna()
                fund = fundamentals.get(t)
                return t, calc_all_factors(adj_close, daily_returns, spy_returns, fund)
            except Exception:
                return t, None

        with ThreadPoolExecutor(max_workers=min(8, len(tickers) or 1)) as pool:
            futures = {pool.submit(_compute_factors, t): t for t in tickers}
            for fut in as_completed(futures):
                t, tf = fut.result()
                if tf is not None:
                    ticker_factors[t] = tf

        # Extract raw factor values and z-score
        raw_values = _extract_factor_values(ticker_factors, self.factor)
        if not raw_values:
            return {"error": "failed to compute exposures"}

        z_scores = _zscore_dict(raw_values)

        # Align weights to available tickers
        w = pd.Series({t.upper(): float(self.weights[t]) for t in self.weights})
        avail = [t for t in w.index if t in z_scores]
        if not avail:
            return {"error": "no overlap between weights and exposure tickers"}

        ex = pd.Series({t: z_scores[t] for t in avail})
        w = w.loc[avail]

        # Net tilt (signed weights × exposure)
        net_tilt = float((w * ex).sum())

        # Long/short tilts (average exposure of each leg)
        long_mask = w > 0
        short_mask = w < 0
        long_sum = float(w[long_mask].sum()) if long_mask.any() else 0.0
        short_sum_abs = float((-w[short_mask]).sum()) if short_mask.any() else 0.0

        long_tilt = (
            float((w[long_mask] * ex.reindex(w[long_mask].index)).sum() / long_sum)
            if long_sum > 0 else np.nan
        )
        short_tilt = (
            float(((-w[short_mask]) * ex.reindex(w[short_mask].index)).sum() / short_sum_abs)
            if short_sum_abs > 0 else np.nan
        )

        per_ticker_exposure = {t: _nan_to_none(z_scores.get(t)) for t in avail}

        return {
            "factor": self.factor,
            "exposure_col": f"{self.factor}_exposure",
            "net_tilt": _nan_to_none(net_tilt),
            "long_tilt": _nan_to_none(long_tilt),
            "short_tilt": _nan_to_none(short_tilt),
            "per_ticker_exposure": per_ticker_exposure,
        }
