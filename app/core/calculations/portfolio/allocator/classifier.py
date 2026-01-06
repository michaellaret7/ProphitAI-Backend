"""
Ticker Classification Module

Classifies tickers into equity and fixed income buckets based on database records.
"""

from typing import List, Tuple

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

from app.core.calculations.portfolio.allocator.models import (
    ClassifiedTickers,
    OptimizerConfig,
)


def classify_tickers(tickers: List[str]) -> Tuple[List[str], List[str]]:
    """
    Classify tickers into equity and fixed income categories.

    Args:
        tickers: List of ticker symbols to classify

    Returns:
        Tuple of (equity_tickers, fixed_income_tickers)

    Raises:
        ValueError: If any tickers are not found in the database
    """
    fixed_income = []
    equities = []
    not_found = []

    with MarketSession() as session:
        ticker_objs = session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
        ticker_map = {t.ticker: t for t in ticker_objs}

        for ticker in tickers:
            ticker_obj = ticker_map.get(ticker)

            if not ticker_obj:
                not_found.append(ticker)
                continue

            if ticker_obj.is_etf and ticker_obj.industry == "fixed_income_etfs":
                fixed_income.append(ticker_obj.ticker)
            else:
                equities.append(ticker_obj.ticker)

    if not_found:
        raise ValueError(f"Tickers not found in database: {not_found}")

    return equities, fixed_income


def build_classified_tickers(tickers: List[str]) -> ClassifiedTickers:
    """
    Build a ClassifiedTickers object from a list of tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        ClassifiedTickers with equities and bonds sets populated
    """
    equities, bonds = classify_tickers(tickers)
    return ClassifiedTickers(
        equities=set(equities),
        bonds=set(bonds),
        all_tickers=tickers,
    )


def auto_adjust_bucket_targets(
    config: OptimizerConfig,
    classified: ClassifiedTickers,
) -> OptimizerConfig:
    """
    Auto-adjust bucket targets when only one asset class is present.

    If all tickers are equities → set equity_weight_target=1, bond_weight_target=0
    If all tickers are bonds → set equity_weight_target=0, bond_weight_target=1

    Args:
        config: Original optimizer configuration
        classified: Classified tickers

    Returns:
        Adjusted OptimizerConfig (or original if both asset classes present)
    """
    # If both asset classes present, use config as-is
    if classified.has_equities and classified.has_bonds:
        return config

    # Equity-only portfolio
    if classified.has_equities and not classified.has_bonds:
        return config.model_copy(update={
            "equity_weight_target": 1.0,
            "bond_weight_target": 0.0,
        })

    # Bond-only portfolio
    if classified.has_bonds and not classified.has_equities:
        return config.model_copy(update={
            "equity_weight_target": 0.0,
            "bond_weight_target": 1.0,
        })

    return config
