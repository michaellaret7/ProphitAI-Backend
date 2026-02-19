"""Ticker Classification Module.

Classifies tickers into equity, fixed income, and commodity buckets based on database records.
"""

from typing import Dict, List, Tuple

from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker

from app.core.calc_v2.portfolio_allocator.models import (
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
        "crypto_weight_target": 0.0,
    }


def classify_tickers(tickers: List[str]) -> Tuple[List[str], List[str], List[str], List[str]]:
    """Classify tickers into equity, fixed income, commodity, and crypto categories.

    Returns:
        Tuple of (equity_tickers, fixed_income_tickers, commodity_tickers, crypto_tickers).

    Raises:
        ValueError: If any tickers are not found in the database.
    """
    fixed_income = []
    commodities = []
    crypto = []
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
            elif ticker_obj.is_etf and ticker_obj.industry == "cryptocurrency_etfs":
                crypto.append(ticker_obj.ticker)
            else:
                equities.append(ticker_obj.ticker)

    if not_found:
        raise ValueError(f"Tickers not found in database: {not_found}")

    return equities, fixed_income, commodities, crypto


def build_classified_tickers(tickers: List[str]) -> ClassifiedTickers:
    """Build a ClassifiedTickers object from a list of tickers."""
    equities, bonds, commodities, crypto = classify_tickers(tickers)
    return ClassifiedTickers(
        equities=set(equities),
        bonds=set(bonds),
        commodities=set(commodities),
        crypto=set(crypto),
        all_tickers=tickers,
    )


def auto_adjust_bucket_targets(
    config: OptimizerConfig,
    classified: ClassifiedTickers,
) -> OptimizerConfig:
    """Auto-adjust bucket targets based on which asset classes are present.

    Redistributes weight targets proportionally among present asset classes.
    If only one asset class is present, it gets 100%.
    """
    # Build list of present asset classes with their configured targets
    bucket_map = [
        (classified.has_equities, "equity_weight_target", config.equity_weight_target),
        (classified.has_bonds, "bond_weight_target", config.bond_weight_target),
        (classified.has_commodities, "commodity_weight_target", config.commodity_weight_target),
        (classified.has_crypto, "crypto_weight_target", config.crypto_weight_target),
    ]

    present = [(key, target) for has, key, target in bucket_map if has]
    total_buckets = len(bucket_map)

    # All buckets present - validate targets sum to 1.0
    if len(present) == total_buckets:
        total = sum(t for _, t in present)
        if abs(total - 1.0) > WEIGHT_TOLERANCE:
            raise ValueError(f"Bucket weight targets must sum to 1.0, got {total}")
        return config

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
        for key, target in present:
            updates[key] = target / total_configured
    else:
        equal_weight = 1.0 / len(present)
        for key, _ in present:
            updates[key] = equal_weight

    return config.model_copy(update=updates)
