"""Portfolio-level factor exposure via universe-relative z-scoring.

Steps:
1. Extract each factor metric into a Series (one value per ticker)
2. Merge portfolio + universe values into one reference population
3. Winsorize at 2.5th/97.5th percentile (handles outliers)
4. Z-score cross-sectionally (mean=0, std=1 across universe)
5. Portfolio-weighted sum: Σ(w_i × z_i) for each metric
6. Composite scores: mean of sub-factor exposures per category

Z-scoring against a market universe ensures that portfolio exposures reflect
absolute positioning (e.g. mega-caps score high on size) rather than
misleading intra-portfolio tilts.
"""

from __future__ import annotations

from typing import Callable

import numpy as np

import pandas as pd

from app.repositories.fundamentals.models import FundamentalsResult
from app.core.calc_v2.factors.calc_all import calc_all_factors
from app.core.calc_v2.models.factors import (
    TickerFactors,
    FactorExposureDetail,
    PortfolioFactorExposure,
)
from app.core.calculations.core.helpers import winsorize_series, zscore_series


# ================================
# --> Helper funcs
# ================================

# Reason: each tuple defines (metric_name, category, extraction_function)
# Category is used to group sub-factors into composite scores.
_METRIC_EXTRACTORS: list[tuple[str, str, Callable[[TickerFactors], float | None]]] = [
    # Momentum
    ('r12_1', 'momentum', lambda f: f.momentum.r12_1),
    ('r6_1', 'momentum', lambda f: f.momentum.r6_1),
    ('risk_adj_momentum', 'momentum', lambda f: f.momentum.risk_adj_momentum),
    # Value
    ('earnings_yield', 'value', lambda f: f.value.earnings_yield if f.value else None),
    ('book_to_price', 'value', lambda f: f.value.book_to_price if f.value else None),
    ('fcf_yield', 'value', lambda f: f.value.fcf_yield if f.value else None),
    ('ebitda_to_ev', 'value', lambda f: f.value.ebitda_to_ev if f.value else None),
    # Quality
    ('gross_profitability', 'quality', lambda f: f.quality.gross_profitability if f.quality else None),
    ('roe', 'quality', lambda f: f.quality.roe if f.quality else None),
    ('accrual_ratio', 'quality', lambda f: f.quality.accrual_ratio if f.quality else None),
    ('altman_z_score', 'quality', lambda f: f.quality.altman_z_score if f.quality else None),
    # Growth
    ('revenue_growth_yoy', 'growth', lambda f: f.growth.revenue_growth_yoy if f.growth else None),
    ('forward_eps_growth', 'growth', lambda f: f.growth.forward_eps_growth if f.growth else None),
    # Volatility
    ('realized_vol_1y', 'volatility', lambda f: f.volatility.realized_vol_1y),
    ('beta', 'volatility', lambda f: f.volatility.beta),
    # Size
    ('log_market_cap', 'size', lambda f: f.size.log_market_cap if f.size else None),
]


def _weighted_zscore(
    raw_values: dict[str, float | None],
    weights: dict[str, float],
    universe_values: dict[str, float | None],
) -> float | None:
    """Winsorize → z-score → portfolio-weighted sum for a single metric.

    Args:
        raw_values: Dict mapping portfolio ticker → raw metric value.
        weights: Dict mapping portfolio ticker → portfolio weight.
        universe_values: Dict mapping universe ticker → raw metric value.
            Portfolio + universe values are merged into one reference
            population for z-scoring, so scores reflect positioning
            relative to the market rather than intra-portfolio tilts.

    Returns None if fewer than 2 tickers in the reference population.
    """
    # Reason: build reference population — universe first, then portfolio overrides
    reference = {t: v for t, v in universe_values.items() if v is not None and not np.isnan(v)}
    portfolio_clean = {t: v for t, v in raw_values.items() if v is not None and not np.isnan(v)}
    reference.update(portfolio_clean)

    if len(reference) < 2:
        return None

    series = pd.Series(reference, dtype=float)
    winsorized = winsorize_series(series)
    zscored = zscore_series(winsorized)

    if zscored is None or (isinstance(zscored, pd.Series) and zscored.empty):
        return None

    # Portfolio-weighted sum: Σ(w_i × z_i) — only portfolio tickers
    total = 0.0
    weight_sum = 0.0
    for ticker, z_val in zscored.items():
        w = weights.get(str(ticker), 0.0)
        if w != 0 and not np.isnan(z_val):
            total += w * z_val
            weight_sum += abs(w)

    if weight_sum == 0:
        return None

    # Reason: normalize by weight sum so partial coverage doesn't deflate scores
    return total / weight_sum

# ================================
# --> Universe builder
# ================================

def build_universe_factors(
    tickers: list[str],
    ohlcv_data: dict[str, pd.DataFrame],
    benchmark_prices: pd.Series,
    fundamentals: dict[str, FundamentalsResult] | None = None,
) -> dict[str, TickerFactors]:
    """Build TickerFactors for each ticker in the universe.

    Used to create the reference population for universe-relative z-scoring.

    Args:
        tickers: Universe ticker symbols.
        ohlcv_data: Dict mapping ticker → OHLCV DataFrame.
        benchmark_prices: Benchmark adj_close series (e.g. SPY).
        fundamentals: Optional dict mapping ticker → FundamentalsResult.

    Returns:
        Dict mapping ticker → TickerFactors. Tickers missing from
        ohlcv_data are silently skipped.
    """
    benchmark_returns = benchmark_prices.pct_change().dropna()
    fund_map = fundamentals or {}
    result: dict[str, TickerFactors] = {}

    for ticker in tickers:
        if ticker not in ohlcv_data:
            continue

        ohlcv = ohlcv_data[ticker]
        adj_close = ohlcv['adj_close']
        daily_returns = adj_close.pct_change().dropna()

        result[ticker] = calc_all_factors(
            adj_close=adj_close,
            daily_returns=daily_returns,
            benchmark_returns=benchmark_returns,
            fundamentals=fund_map.get(ticker),
        )

    return result


# ================================
# --> Main exposure function
# ================================

def calc_portfolio_factor_exposure(
    ticker_factors: dict[str, TickerFactors],
    weights: dict[str, float],
    universe_factors: dict[str, TickerFactors],
) -> PortfolioFactorExposure:
    """Calculate portfolio factor exposure via cross-sectional z-scoring.

    Z-scores each metric against the full universe so portfolio exposures
    reflect absolute market positioning rather than intra-portfolio tilts.

    Args:
        ticker_factors: Dict mapping ticker → TickerFactors (from Ticker.factors).
        weights: Dict mapping ticker → portfolio weight (decimal, e.g. 0.30).
        universe_factors: Dict mapping universe ticker → TickerFactors.

    Returns:
        PortfolioFactorExposure with composite scores and granular detail.
    """
    # Step 1-4: Compute weighted z-score for each metric
    metric_exposures: dict[str, float | None] = {}
    for metric_name, category, extractor in _METRIC_EXTRACTORS:
        raw = {t: extractor(f) for t, f in ticker_factors.items()}
        univ_vals = {t: extractor(f) for t, f in universe_factors.items()}
        metric_exposures[metric_name] = _weighted_zscore(raw, weights, univ_vals)

    # Step 5: Composite scores (mean of sub-factor exposures per category)
    category_metrics: dict[str, list[float]] = {}
    for metric_name, category, _ in _METRIC_EXTRACTORS:
        val = metric_exposures.get(metric_name)
        if val is not None:
            category_metrics.setdefault(category, []).append(val)

    def _composite(category: str) -> float | None:
        vals = category_metrics.get(category)
        if not vals:
            return None
        return float(np.mean(vals))

    detail = FactorExposureDetail(**{
        name: metric_exposures.get(name)
        for name, _, _ in _METRIC_EXTRACTORS
    })

    return PortfolioFactorExposure(
        momentum=_composite('momentum') or 0.0,
        value=_composite('value'),
        quality=_composite('quality'),
        growth=_composite('growth'),
        volatility=_composite('volatility') or 0.0,
        size=_composite('size'),
        detail=detail,
    )
    