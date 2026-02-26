"""Group-level metrics: exposures, VaR, and concentration by sector/industry/sub-industry."""

import numpy as np
import pandas as pd

from app.core.calc_v2.models.group_metrics import GroupMetrics
from app.core.calc_v2.risk.distribution import calc_var
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker as TickerModel


# ---------------------------------------------------------------------------
# Exposure helpers
# ---------------------------------------------------------------------------


def calc_net_exposure(weights: np.ndarray) -> float:
    """Calculate net exposure — sum of all weights (long minus short).

    +1.0 = fully long, 0.0 = market-neutral, negative = net short.
    """
    return float(weights.sum())


def calc_gross_exposure(weights: np.ndarray) -> float:
    """Calculate gross exposure — sum of absolute weights.

    Measures total capital deployed regardless of direction.
    A 130/30 portfolio has gross exposure of 1.6.
    """
    return float(np.abs(weights).sum())


def calc_long_exposure(weights: np.ndarray) -> float:
    """Calculate long exposure — sum of all positive weights."""
    return float(weights[weights > 0].sum())


def calc_short_exposure(weights: np.ndarray) -> float:
    """Calculate short exposure — sum of negative weights as a positive number."""
    return float(np.abs(weights[weights < 0]).sum())


def fetch_ticker_classifications(tickers: list[str]) -> dict[str, dict[str, str | None]]:
    """Fetch sector, industry, and sub_industry for a list of tickers from the database."""
    from app.utils.cache.data_cache import get_cache

    tickers_upper = [t.upper() for t in tickers]
    cache = get_cache()

    cached, missing = cache.get_classifications(tickers_upper)
    if not missing:
        return cached
    fetched = _query_classifications(missing)
    cache.put_classifications(fetched)
    return {**cached, **fetched}


def _query_classifications(tickers: list[str]) -> dict[str, dict[str, str | None]]:
    """Query ticker classifications from the database."""
    with MarketSession() as session:
        rows = (
            session.query(
                TickerModel.ticker,
                TickerModel.sector,
                TickerModel.industry,
                TickerModel.sub_industry,
            )
            .filter(TickerModel.ticker.in_(tickers))
            .all()
        )
    return {
        row.ticker: {
            'sector': row.sector,
            'industry': row.industry,
            'sub_industry': row.sub_industry,
        }
        for row in rows
    }


def calc_group_metrics(
    group_type: str,
    classifications: dict[str, dict[str, str | None]],
    tickers: list[str],
    weights: np.ndarray,
    asset_returns: pd.DataFrame,
) -> dict[str, GroupMetrics]:
    """Calculate VaR and concentration for each group (sector/industry/sub_industry).

    Returns a dict keyed by group name with GroupMetrics (var_99, concentration, tickers).
    """
    # Reason: Build {group_name: [(ticker, weight)]} mapping
    groups: dict[str, list[tuple[str, float]]] = {}
    for i, ticker in enumerate(tickers):
        classification = classifications.get(ticker.upper(), {})
        group_name = classification.get(group_type) or 'Unknown'
        groups.setdefault(group_name, []).append((ticker, float(weights[i])))

    results: dict[str, GroupMetrics] = {}
    for group_name, members in sorted(groups.items()):
        member_tickers = [t for t, _ in members]
        member_weights = np.array([w for _, w in members])
        concentration = float(member_weights.sum())

        # Reason: Compute weighted returns for this group at portfolio-level weights
        # to measure this group's contribution to overall portfolio risk.
        group_returns = (asset_returns[member_tickers] * member_weights).sum(axis=1)
        var_99 = calc_var(group_returns, confidence=0.99)

        results[group_name] = GroupMetrics(
            var_99=var_99,
            concentration=concentration,
            tickers=member_tickers,
        )

    return results
