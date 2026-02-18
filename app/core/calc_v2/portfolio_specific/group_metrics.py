"""Group-level VaR and concentration calculations by sector, industry, and sub-industry."""

import numpy as np
import pandas as pd

from app.core.calc_v2.risk.calc_risk_metrics import calc_var
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker as TickerModel


def fetch_ticker_classifications(tickers: list[str]) -> dict[str, dict[str, str | None]]:
    """Fetch sector, industry, and sub_industry for a list of tickers from the database."""
    with MarketSession() as session:
        rows = (
            session.query(
                TickerModel.ticker,
                TickerModel.sector,
                TickerModel.industry,
                TickerModel.sub_industry,
            )
            .filter(TickerModel.ticker.in_([t.upper() for t in tickers]))
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
) -> dict[str, dict]:
    """Calculate VaR and concentration for each group (sector/industry/sub_industry).

    Returns a dict keyed by group name with var_99, concentration, and tickers.
    """
    # Reason: Build {group_name: [(ticker, weight)]} mapping
    groups: dict[str, list[tuple[str, float]]] = {}
    for i, ticker in enumerate(tickers):
        classification = classifications.get(ticker.upper(), {})
        group_name = classification.get(group_type) or 'Unknown'
        groups.setdefault(group_name, []).append((ticker, float(weights[i])))

    results = {}
    for group_name, members in sorted(groups.items()):
        member_tickers = [t for t, _ in members]
        member_weights = np.array([w for _, w in members])
        concentration = float(member_weights.sum())

        # Reason: Compute weighted returns for this group at portfolio-level weights
        # to measure this group's contribution to overall portfolio risk.
        group_returns = (asset_returns[member_tickers] * member_weights).sum(axis=1)
        var_99 = calc_var(group_returns, confidence=0.99)

        results[group_name] = {
            'var_99': round(var_99, 4),
            'concentration': round(concentration, 4),
            'tickers': member_tickers,
        }

    return results
