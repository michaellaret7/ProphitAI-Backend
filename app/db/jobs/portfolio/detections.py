from itertools import combinations
from typing import Dict
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from app.db.core.db_config import MarketSession
from app.db.jobs.portfolio.models import (
    DRIFT_THRESHOLD,
    DRAWDOWN_THRESHOLD,
    PAIR_CORR_HIGH_THRESHOLD,
    PAIR_CORR_SPIKE_THRESHOLD,
    DriftDetails,
    DriftResult,
    DrawdownDetails,
    DrawdownResult,
    PairCorrelationDetails,
    PairCorrelationResult,
    PortfolioCorrelationResult,
)
from app.db.jobs.portfolio.utils import classify_and_add_tickers
from app.repositories.price_data import fetch_bulk_ohlcv_data_for_tickers
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

    return DriftResult(flagged_sectors=flagged_sectors)

def detect_drawdowns(
    positions: Dict[str, float],
    portfolio_created_date: datetime
) -> DrawdownResult:
    """
    Detect positions currently in drawdown below threshold.

    Returns:
        DrawdownResult with:
            - triggered: True if any position has breached threshold
            - threshold: The drawdown threshold used
            - flagged_positions: Dict of positions with drawdown details
    """
    price_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers=positions.keys(),
        start_date_str=portfolio_created_date.strftime('%Y-%m-%d'),
        end_date_str=get_current_utc_time().strftime('%Y-%m-%d'),
        frequency='daily',
        returns=True
    )

    returns_df = pd.DataFrame()

    for ticker, data in price_data.items():
        returns_df[ticker] = data['returns']

    returns_df = returns_df.dropna()

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

    return DrawdownResult(flagged_positions=flagged_positions)

def detect_portfolio_correlation_change(
    positions: Dict[str, float],
    recent_window: int = 30,
    baseline_window: int = 90
) -> PortfolioCorrelationResult:
    """
    Monitor portfolio-level average pairwise correlation.

    Returns:
        PortfolioCorrelationResult with:
            - triggered: True if avg correlation is high or spiked
            - recent/baseline/change: Correlation values
    """
    tickers = list(positions.keys())

    if len(tickers) < 2:
        return PortfolioCorrelationResult(recent=0.0, baseline=0.0, change=0.0)

    today = get_current_utc_time()

    price_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers=tickers,
        start_date_str=(today - timedelta(days=baseline_window)).strftime('%Y-%m-%d'),
        end_date_str=today.strftime('%Y-%m-%d'),
        frequency='daily',
        returns=True
    )

    returns_df = pd.DataFrame({
        ticker: data['returns'] for ticker, data in price_data.items()
    }).dropna()

    recent_corr = returns_df.iloc[-recent_window:].corr()
    baseline_corr = returns_df.iloc[-baseline_window:-recent_window].corr()

    mask = np.triu(np.ones_like(recent_corr, dtype=bool), k=1)
    recent_avg = float(recent_corr.where(mask).stack().mean())
    baseline_avg = float(baseline_corr.where(mask).stack().mean())

    return PortfolioCorrelationResult(
        recent=recent_avg,
        baseline=baseline_avg,
        change=recent_avg - baseline_avg
    )


def detect_pair_correlation_changes(
    positions: Dict[str, float],
    recent_window: int = 30,
    baseline_window: int = 90
) -> PairCorrelationResult:
    """
    Monitor individual pair correlation changes.

    Returns:
        PairCorrelationResult with:
            - triggered: True if any pair has high correlation or spiked
            - pairs: All pair correlations sorted by change
            - flagged_pairs: Pairs exceeding thresholds
    """
    tickers = list(positions.keys())

    if len(tickers) < 2:
        return PairCorrelationResult(pairs=[], flagged_pairs=[])

    today = get_current_utc_time()

    price_data = fetch_bulk_ohlcv_data_for_tickers(
        tickers=tickers,
        start_date_str=(today - timedelta(days=baseline_window)).strftime('%Y-%m-%d'),
        end_date_str=today.strftime('%Y-%m-%d'),
        frequency='daily',
        returns=True
    )

    returns_df = pd.DataFrame({
        ticker: data['returns'] for ticker, data in price_data.items()
    }).dropna()

    recent_corr = returns_df.iloc[-recent_window:].corr()
    baseline_corr = returns_df.iloc[-baseline_window:-recent_window].corr()

    pairs: list[PairCorrelationDetails] = []
    for t1, t2 in combinations(tickers, 2):
        pairs.append(PairCorrelationDetails(
            pair=f"{t1}/{t2}",
            recent=float(recent_corr.loc[t1, t2]),
            baseline=float(baseline_corr.loc[t1, t2]),
            change=float(recent_corr.loc[t1, t2] - baseline_corr.loc[t1, t2])
        ))

    pairs.sort(key=lambda x: x.change, reverse=True)

    # Flag pairs based on:
    # 1. Spike: correlation increased significantly (always flag regardless of levels)
    # 2. Newly high: correlation is now high BUT wasn't already high at baseline
    flagged_pairs = [
        p for p in pairs
        if p.change > PAIR_CORR_SPIKE_THRESHOLD
        or (p.recent > PAIR_CORR_HIGH_THRESHOLD and p.baseline < PAIR_CORR_HIGH_THRESHOLD)
    ]

    return PairCorrelationResult(pairs=pairs, flagged_pairs=flagged_pairs)