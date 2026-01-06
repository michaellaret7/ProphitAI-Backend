"""
Ticker Classification Module

Classifies tickers into equity, fixed income, and commodity buckets based on database records.
"""

from typing import Dict, List, Tuple

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

from app.core.calculations.portfolio.allocator.models import (
    ClassifiedTickers,
    OptimizerConfig,
    WEIGHT_TOLERANCE,
)


def _zero_weight_targets() -> Dict[str, float]:
    """Return a dict with all weight targets set to zero."""
    return {
        "equity_weight_target": 0.0,
        "bond_weight_target": 0.0,
        "commodity_weight_target": 0.0,
    }


def classify_tickers(tickers: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Classify tickers into equity, fixed income, and commodity categories.

    Args:
        tickers: List of ticker symbols to classify

    Returns:
        Tuple of (equity_tickers, fixed_income_tickers, commodity_tickers)

    Raises:
        ValueError: If any tickers are not found in the database
    """
    fixed_income = []
    commodities = []
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
            elif ticker_obj.is_etf and ticker_obj.industry == "commodity_etfs":
                commodities.append(ticker_obj.ticker)
            else:
                equities.append(ticker_obj.ticker)

    if not_found:
        raise ValueError(f"Tickers not found in database: {not_found}")

    return equities, fixed_income, commodities


def build_classified_tickers(tickers: List[str]) -> ClassifiedTickers:
    """
    Build a ClassifiedTickers object from a list of tickers.

    Args:
        tickers: List of ticker symbols

    Returns:
        ClassifiedTickers with equities, bonds, and commodities sets populated
    """
    equities, bonds, commodities = classify_tickers(tickers)
    return ClassifiedTickers(
        equities=set(equities),
        bonds=set(bonds),
        commodities=set(commodities),
        all_tickers=tickers,
    )


def auto_adjust_bucket_targets(
    config: OptimizerConfig,
    classified: ClassifiedTickers,
) -> OptimizerConfig:
    """
    Auto-adjust bucket targets based on which asset classes are present.

    Redistributes weight targets proportionally among present asset classes.
    If only one asset class is present, it gets 100%.
    If two are present, weights are redistributed proportionally.

    Args:
        config: Original optimizer configuration
        classified: Classified tickers

    Returns:
        Adjusted OptimizerConfig with targets summing to 1.0
    """
    has_eq = classified.has_equities
    has_bnd = classified.has_bonds
    has_cmd = classified.has_commodities

    # All three present - validate targets sum to 1.0
    if has_eq and has_bnd and has_cmd:
        total = config.equity_weight_target + config.bond_weight_target + config.commodity_weight_target
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(f"Bucket weight targets must sum to 1.0, got {total}")
        return config

    # Build list of present classes with their configured targets
    present = []
    if has_eq:
        present.append(("equity_weight_target", config.equity_weight_target))
    if has_bnd:
        present.append(("bond_weight_target", config.bond_weight_target))
    if has_cmd:
        present.append(("commodity_weight_target", config.commodity_weight_target))

    if not present:
        raise ValueError("No asset classes present in portfolio")

    # Single asset class - gets 100%
    if len(present) == 1:
        updates = _zero_weight_targets()
        updates[present[0][0]] = 1.0
        return config.model_copy(update=updates)

    # Two asset classes - redistribute proportionally
    total_configured = sum(t[1] for t in present)
    updates = _zero_weight_targets()

    if total_configured > 0:
        # Proportional redistribution
        for key, target in present:
            updates[key] = target / total_configured
    else:
        # Equal split if all configured targets are 0
        equal_weight = 1.0 / len(present)
        for key, _ in present:
            updates[key] = equal_weight

    return config.model_copy(update=updates)
