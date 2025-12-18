from typing import Dict, List
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass(frozen=True)
class OptimizerConfig:
    # Bucket targets (configurable)
    equity_weight: float = 0.60
    bond_weight: float = 0.40

    # Data params
    lookback_days: int = 504
    frequency: str = "daily"
    trading_days: int = 252

    # Solver params
    risk_free_rate: float = 0.02

    # Position constraints (configurable)
    min_weight: float = 0.005                 # strictly positive -> no zeros
    max_weight: Optional[float] = None        # if set, use directly
    max_weight_multiple: float = 1.5          # else max = multiple * (1/n)


def assert_weights_ok(
    cleaned: Dict[str, float],
    tickers: List[str],
    min_w: float,
    max_w: float,
):
    assert set(cleaned.keys()) == set(tickers)
    ws = np.array([cleaned[t] for t in tickers], dtype=float)

    assert np.isfinite(ws).all()
    assert abs(ws.sum() - 1.0) <= 1e-4
    assert (ws >= (min_w - 1e-4)).all(), f"Found weight below min_w={min_w}: {cleaned}"
    assert (ws <= (max_w + 1e-4)).all(), f"Found weight above max_w={max_w}: {cleaned}"


def suggested_max_weight(n_assets: int, multiple: float) -> float:
    return float(multiple / n_assets)