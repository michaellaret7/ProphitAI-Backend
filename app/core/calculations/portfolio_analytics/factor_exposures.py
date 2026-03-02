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

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np
import pandas as pd

from app.core.calculations.config import UNIVERSE_TICKERS
from app.core.calculations.factors.calc_all import calc_all_factors
from app.core.calculations.models.factors import (
    TickerFactors,
    FactorExposureDetail,
    PortfolioFactorExposure,
)
from app.core.calculations.utils import winsorize_series, zscore_series
from app.utils.time_utils import get_utc_date_str, get_utc_days_ago

logger = logging.getLogger(__name__)

# Reason: module-level lock prevents multiple threads from computing
# universe factors simultaneously on the first call of the day.
# Stored as a single tuple so the fast-path read is one atomic reference load.
_universe_lock = threading.Lock()
_universe_cache_entry: tuple[str, dict[str, TickerFactors]] | None = None


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
# --> Universe factor cache
# ================================

def get_universe_factors() -> dict[str, TickerFactors]:
    """Return cached universe factor exposures, computing once per calendar day.

    Checks in-memory cache first, then Redis (survives server restarts),
    then computes from scratch. Thread-safe via double-checked locking
    with a single-tuple cache entry for atomic reads.

    Returns:
        Dict mapping UNIVERSE_TICKERS ticker -> TickerFactors.
    """
    global _universe_cache_entry

    today = get_utc_date_str()

    # Fast path: single atomic read — no lock needed
    entry = _universe_cache_entry
    if entry is not None and entry[0] == today:
        return entry[1]

    with _universe_lock:
        # Double-check after acquiring lock
        entry = _universe_cache_entry
        if entry is not None and entry[0] == today:
            return entry[1]

        # Reason: try Redis before expensive compute, inside lock to avoid race
        result = _load_from_redis(today)
        if result is not None:
            _universe_cache_entry = (today, result)
            return result

        logger.info("Computing universe factors for %s (%d tickers)...", today, len(UNIVERSE_TICKERS))
        result = _compute_universe_factors()
        _universe_cache_entry = (today, result)
        _save_to_redis(today, result)
        logger.info("Universe factors cached (%d tickers computed)", len(result))
        return result


def clear_universe_cache() -> None:
    """Reset the in-memory universe factor cache.

    Acquires _universe_lock so concurrent readers see a consistent state.
    Called by the EOD job after new price data is written.
    """
    global _universe_cache_entry
    with _universe_lock:
        _universe_cache_entry = None


def _load_from_redis(date_key: str) -> dict[str, TickerFactors] | None:
    """Attempt to load universe factors from Redis."""
    from app.redis.sync_client import sync_cache

    raw = sync_cache.get(f"universe_factors:{date_key}")
    if raw is None:
        return None

    try:
        return {ticker: TickerFactors(**data) for ticker, data in raw.items()}
    except Exception as e:
        logger.warning("Failed to deserialize universe factors from Redis: %s", e)
        return None


def _save_to_redis(date_key: str, factors: dict[str, TickerFactors]) -> None:
    """Persist universe factors to Redis with 24-hour TTL."""
    from app.redis.sync_client import sync_cache

    try:
        serialized = {ticker: tf.model_dump() for ticker, tf in factors.items()}
        sync_cache.set(f"universe_factors:{date_key}", serialized, ttl=86400)
    except Exception as e:
        logger.warning("Failed to save universe factors to Redis: %s", e)


def _compute_universe_factors() -> dict[str, TickerFactors]:
    """Fetch data and compute universe factors from scratch.

    Uses a 5-year lookback to provide sufficient history for all
    factor calculations (momentum needs 12mo, fundamentals are quarterly).
    """
    # Reason: imports inside function to avoid circular imports (repositories → calculations boundary)
    from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
    from app.repositories.fundamentals.fetchers import get_bulk_fundamentals

    end_date = get_utc_date_str()
    start_date = get_utc_days_ago(5 * 365).strftime("%Y-%m-%d")
    fetch_tickers = list(UNIVERSE_TICKERS) + ["SPY"]

    # Reason: OHLCV and fundamentals fetches are independent I/O — run in parallel.
    # Note: OHLCV and fundamentals fetched here are also written to the process-level
    # DataCache by the repository layer, benefiting subsequent agent tool calls.
    with ThreadPoolExecutor(max_workers=2) as pool:
        ohlcv_future = pool.submit(fetch_bulk_ohlcv_data_for_tickers, fetch_tickers, start_date, end_date)
        fund_future = pool.submit(get_bulk_fundamentals, UNIVERSE_TICKERS)
        ohlcv_data = ohlcv_future.result()
        fundamentals = fund_future.result()

    benchmark_returns = ohlcv_data["SPY"]["adj_close"].pct_change(fill_method=None).dropna()
    fund_map = fundamentals or {}
    result: dict[str, TickerFactors] = {}

    for ticker in UNIVERSE_TICKERS:
        if ticker not in ohlcv_data:
            continue

        ohlcv = ohlcv_data[ticker]
        adj_close = ohlcv["adj_close"]
        daily_returns = adj_close.pct_change(fill_method=None).dropna()

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
    