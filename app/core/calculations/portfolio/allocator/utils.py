from typing import Dict, List
import numpy as np
from app.db.core.pull_fmp_data import FMP_API_DATA
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class OptimizerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    # Bucket targets with bands (soft constraints)
    equity_weight_target: float = 0.60
    bond_weight_target: float = 0.40
    bucket_band: float = 0.05                 # ±5% flexibility around targets

    initial_portfolio_value: float = 10_000

    # Data params
    lookback_days: int = 504
    frequency: str = "daily"
    trading_days: int = 252

    # Solver params
    risk_free_rate: float = 0.02

    # Position constraints (hybrid hard/soft)
    min_weight: float = 0.01                  # HARD floor - every ticker gets at least 1%
    soft_max_weight: float = 0.08             # Soft cap - penalty kicks in above 8%
    hard_max_weight: float = 0.15             # HARD ceiling - absolute max 15%

    # Regularization penalties
    l2_gamma: float = 0.1                     # L2 regularization for diversification
    concentration_gamma: float = 0.5          # Penalty for exceeding soft_max

class Allocation(BaseModel):
    ticker: str
    weight: float
    num_shares: int

class FinalOutput(BaseModel):
    allocations: List[Allocation]
    performance: Dict[str, float]
    strategy: str

# Tolerance for numerical precision in weight comparisons
WEIGHT_TOLERANCE = 1e-4


def validate_weights(
    cleaned: Dict[str, float],
    tickers: List[str],
    min_w: float,
    hard_max_w: float,
) -> None:
    """
    Validate portfolio weights against hard bounds.
    Soft constraints are handled via penalties in the objective, not validated here.

    Args:
        cleaned: Dict mapping ticker symbols to weight fractions
        tickers: List of ticker symbols that should be in cleaned
        min_w: Minimum weight floor (hard constraint)
        hard_max_w: Maximum weight ceiling (hard constraint)

    Raises:
        ValueError: If weights violate any hard constraints
    """
    if set(cleaned.keys()) != set(tickers):
        raise ValueError(
            f"Weight keys {set(cleaned.keys())} do not match tickers {set(tickers)}"
        )

    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    if not np.isfinite(ws).all():
        raise ValueError("Weights contain non-finite values")
    if abs(ws.sum() - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(f"Weights sum to {ws.sum()}, expected 1.0")
    if not (ws >= (min_w - WEIGHT_TOLERANCE)).all():
        raise ValueError(f"Found weight below min_w={min_w}: {cleaned}")
    if not (ws <= (hard_max_w + WEIGHT_TOLERANCE)).all():
        raise ValueError(f"Found weight above hard_max_w={hard_max_w}: {cleaned}")


def calc_num_shares(weights: Dict[str, float], portfolio_value: float) -> Dict[str, int]:
    """
    Calculate the number of shares for each ticker based on weights and portfolio value.

    Args:
        weights: Dict mapping ticker symbols to weight fractions (must sum to ~1.0)
        portfolio_value: Total portfolio value in dollars

    Returns:
        Dict mapping ticker symbols to number of whole shares

    Raises:
        ValueError: If price data is unavailable or invalid for any ticker
    """
    fmp_data = FMP_API_DATA()
    live_prices = fmp_data.get_batch_quote(list(weights.keys()))

    if not live_prices:
        raise ValueError("Failed to fetch live prices from FMP API")

    prices = {}
    for quote in live_prices:
        symbol = quote.get("symbol")
        price = quote.get("price")
        if symbol and price is not None and price > 0:
            prices[symbol] = price

    # Validate all tickers have prices
    missing = set(weights.keys()) - set(prices.keys())
    if missing:
        raise ValueError(f"Missing price data for tickers: {sorted(missing)}")

    num_shares = {}
    for ticker, weight in weights.items():
        num_shares[ticker] = int(weight * portfolio_value / prices[ticker])

    return num_shares
