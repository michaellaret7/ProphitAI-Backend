"""
Portfolio detection functions.

Each detection function computes all result fields explicitly, including `triggered`.
"""
from typing import Dict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker
from app.db.jobs.portfolio.models import (
    DRIFT_THRESHOLD,
    DRAWDOWN_THRESHOLD,
    PORTFOLIO_CORR_ZSCORE_THRESHOLD,
    PORTFOLIO_CORR_HIGH_THRESHOLD,
    PORTFOLIO_CORR_DISPERSION_THRESHOLD,
    PRICE_TARGET_CHANGE_THRESHOLD,
    DriftDetails,
    DriftResult,
    DrawdownDetails,
    DrawdownResult,
    PortfolioCorrelationResult,
    PriceTargetChangeDetails,
    PriceTargetChangeResult,
)
from app.db.jobs.portfolio.utils import classify_and_add_tickers, get_median_price_targets
from app.repositories.price_data import build_returns_df
from app.utils.time_utils import get_current_utc_time

def detect_allocation_drift(
    positions: Dict[str, float],
    preferences: Dict[str, float],
    market_session: MarketSession
) -> DriftResult:
    """
    Detect if portfolio allocations have drifted from target preferences.

    Returns:
        DriftResult with:
            - triggered: True if any sector has drifted beyond threshold
            - threshold: The drift threshold used
            - flagged_sectors: Dict of sectors with drift details
    """
    allocations = classify_and_add_tickers(positions, market_session)

    flagged_sectors: Dict[str, DriftDetails] = {}

    for sector, allocation in allocations.items():
        preference = preferences.get(sector, 0.0)
        diff = allocation - preference

        if abs(diff) > DRIFT_THRESHOLD:
            flagged_sectors[sector] = DriftDetails(
                current_allocation=allocation,
                target_allocation=preference,
                drift=diff
            )

    return DriftResult(
        flagged_sectors=flagged_sectors,
        triggered=len(flagged_sectors) > 0
    )

def detect_price_target_changes(
    positions: Dict[str, float],
    market_session: MarketSession
) -> PriceTargetChangeResult:
    """
    Detect price target changes for all portfolio positions.
    """
    flagged_positions: Dict[str, PriceTargetChangeDetails] = {}

    tickers = list(positions.keys())

    median_price_targets = get_median_price_targets(market_session, tickers)
    ticker_objs = market_session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    current_prices = {t.ticker: t.price for t in ticker_objs}

    for ticker, median_price_target in median_price_targets.items():
        if median_price_target and current_prices[ticker]/median_price_target > (1 + PRICE_TARGET_CHANGE_THRESHOLD):
            flagged_positions[ticker] = PriceTargetChangeDetails(
                current_price=float(current_prices[ticker]),
                target_price=float(median_price_target),
                deviation=float((current_prices[ticker]/median_price_target) - 1)
            )

    return PriceTargetChangeResult(
        flagged_positions=flagged_positions,
        triggered=len(flagged_positions) > 0
    )

def detect_drawdowns(
    positions: Dict[str, float],
    portfolio_created_date: datetime,
    returns_df: pd.DataFrame | None = None
) -> DrawdownResult:
    """
    Detect positions currently in drawdown below threshold.

    Args:
        positions: Dict mapping tickers to allocations.
        portfolio_created_date: Portfolio inception date for filtering.
        returns_df: Optional pre-fetched returns DataFrame (from batch cache).

    Returns:
        DrawdownResult with:
            - triggered: True if any position has breached threshold
            - threshold: The drawdown threshold used
            - flagged_positions: Dict of positions with drawdown details
    """
    tickers = list(positions.keys())

    if returns_df is None:
        returns_df = build_returns_df(tickers, portfolio_created_date.strftime('%Y-%m-%d'), get_current_utc_time().strftime('%Y-%m-%d'))
    else:
        # Filter to tickers that exist in the cached DataFrame
        available_tickers = [t for t in tickers if t in returns_df.columns]
        if not available_tickers:
            return DrawdownResult(flagged_positions={}, triggered=False)
        returns_df = returns_df[available_tickers].loc[portfolio_created_date:].dropna()

    # Return early if no data after filtering
    if returns_df.empty:
        return DrawdownResult(flagged_positions={}, triggered=False)

    # Cumulative wealth index
    cumulative_wealth = (1 + returns_df).cumprod()

    # High water mark and drawdown series
    high_water_mark = cumulative_wealth.cummax()
    drawdown_series = (cumulative_wealth - high_water_mark) / high_water_mark

    # Current and max drawdowns
    current_drawdowns = drawdown_series.iloc[-1]
    max_drawdowns = drawdown_series.min()

    # Only flagged positions (convert to native Python floats)
    flagged_positions: Dict[str, DrawdownDetails] = {
        ticker: DrawdownDetails(
            current_drawdown=float(current_drawdowns[ticker]),
            max_drawdown=float(max_drawdowns[ticker]),
            peak_date=cumulative_wealth[ticker].idxmax().strftime('%Y-%m-%d'),
        )
        for ticker in current_drawdowns.index
        if current_drawdowns[ticker] < DRAWDOWN_THRESHOLD
    }

    return DrawdownResult(
        flagged_positions=flagged_positions,
        triggered=len(flagged_positions) > 0
    )

def detect_portfolio_correlation_change(
    positions: Dict[str, float],
    returns_df: pd.DataFrame | None = None,
    lookback_days: int = 180,
    short_span: int = 21,  # ~1 trading month
    long_span: int = 63    # ~1 trading quarter
) -> PortfolioCorrelationResult:
    """
    Portfolio-level correlation analysis using pairwise correlation.

    Computes average pairwise correlation over recent and baseline periods,
    calculates statistical significance via z-score, and determines if
    correlation levels pose a risk (everything moving together).

    Args:
        positions: Dict mapping tickers to their allocations.
        returns_df: Optional pre-fetched returns DataFrame (from batch cache).
        lookback_days: Total days of price history to use.
        short_span: Days for recent correlation window (~1 trading month).
        long_span: Days for baseline correlation window (~1 trading quarter).

    Returns:
        PortfolioCorrelationResult with all metrics and triggered status.
    """
    tickers = list(positions.keys())

    if len(tickers) < 2:
        return PortfolioCorrelationResult(
            recent_avg=0.0,
            baseline_avg=0.0,
            change=0.0,
            dispersion=0.0,
            z_score=0.0,
            trend="N/A",
            triggered=False
        )

    if returns_df is None:
        returns_df = build_returns_df(tickers, start_date=(get_current_utc_time() - timedelta(days=270)).strftime('%Y-%m-%d'), end_date=get_current_utc_time().strftime('%Y-%m-%d'), frequency='daily')
        returns_df = returns_df.tail(lookback_days).dropna()
    else:
        # Filter to tickers that exist in the cached DataFrame
        available_tickers = [t for t in tickers if t in returns_df.columns]
        if len(available_tickers) < 2:
            return PortfolioCorrelationResult(
                recent_avg=0.0,
                baseline_avg=0.0,
                change=0.0,
                dispersion=0.0,
                z_score=0.0,
                trend="N/A",
                triggered=False
            )
        returns_df = returns_df[available_tickers].tail(lookback_days).dropna()

    # Return early if insufficient data after filtering
    if returns_df.empty or len(returns_df) < short_span:
        return PortfolioCorrelationResult(
            recent_avg=0.0,
            baseline_avg=0.0,
            change=0.0,
            dispersion=0.0,
            z_score=0.0,
            trend="N/A",
            triggered=False
        )

    # 2. Calculate EWMA Correlation Matrices
    # Institutional preference: EWMA reacts faster to shocks
    recent_corr_matrix = returns_df.tail(short_span).corr()
    long_term_corr_matrix = returns_df.tail(long_span).corr()
    
    # 3. Extract the upper triangle (exclude self-correlation diagonal)
    mask = np.triu(np.ones_like(recent_corr_matrix, dtype=bool), k=1)
    recent_values = recent_corr_matrix.where(mask).stack()
    long_term_values = long_term_corr_matrix.where(mask).stack()

    # 4. Compute Advanced Metrics
    recent_avg = float(recent_values.mean())
    baseline_avg = float(long_term_values.mean())
    change = recent_avg - baseline_avg
    
    # Dispersion: High avg correlation + Low dispersion = "Everything is one trade" (Dangerous)
    dispersion = float(recent_values.std())

    # 5. Trend Significance (Z-Score)
    # We look at the rolling history of the average correlation to see if the current move is an outlier
    rolling_avg_history = []
    for i in range(len(returns_df) - short_span):
        window = returns_df.iloc[i : i + short_span].corr().where(mask).stack().mean()
        rolling_avg_history.append(window)
    
    hist_mean = np.mean(rolling_avg_history)
    hist_std = np.std(rolling_avg_history)
    z_score = (recent_avg - hist_mean) / hist_std if hist_std > 0 else 0

    # 6. Determine Signal
    trend = "Rising" if change > 0.05 else "Falling" if change < -0.05 else "Stable"
    
    high_level = recent_avg > PORTFOLIO_CORR_HIGH_THRESHOLD
    abnormal_spike = z_score > PORTFOLIO_CORR_ZSCORE_THRESHOLD
    low_dispersion = dispersion < PORTFOLIO_CORR_DISPERSION_THRESHOLD

    triggered = bool(
        high_level or (abnormal_spike and low_dispersion)
    )

    return PortfolioCorrelationResult(
        recent_avg=round(recent_avg, 4),
        baseline_avg=round(baseline_avg, 4),
        change=round(change, 4),
        dispersion=round(dispersion, 4),
        z_score=round(float(z_score), 2),
        trend=trend,
        triggered=triggered
    )

