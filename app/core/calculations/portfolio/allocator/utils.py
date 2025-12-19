from typing import Dict, List
import numpy as np
from dataclasses import dataclass
from app.db.core.pull_fmp_data import FMP_API_DATA

@dataclass(frozen=True)
class OptimizerConfig:
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


def assert_weights_ok(
    cleaned: Dict[str, float],
    tickers: List[str],
    min_w: float,
    hard_max_w: float,
):
    """
    Validate portfolio weights against hard bounds.
    Soft constraints are handled via penalties in the objective, not validated here.
    """
    assert set(cleaned.keys()) == set(tickers)
    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    assert np.isfinite(ws).all()
    assert abs(ws.sum() - 1.0) <= 1e-4
    assert (ws >= (min_w - 1e-4)).all(), f"Found weight below min_w={min_w}: {cleaned}"
    assert (ws <= (hard_max_w + 1e-4)).all(), f"Found weight above hard_max_w={hard_max_w}: {cleaned}"


def calc_num_shares(weights: Dict[str, float], portfolio_value: float) -> Dict[str, float]:
    fmp_data = FMP_API_DATA()

    prices = {}

    live_prices = fmp_data.get_batch_quote(list(weights.keys()))

    for price in live_prices:
        prices[price["symbol"]] = price["price"]

    num_shares = {}
    for ticker, weight in weights.items():
        num_shares[ticker] = int(weight * portfolio_value / prices[ticker])

    return num_shares
