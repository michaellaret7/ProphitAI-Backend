"""Base sizer contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from prophitai_algo_trading.cost_model import CostModel


@dataclass
class SizingInput:
    """Everything a sizer needs to compute share count.

    Attributes:
        symbol: Ticker being sized.
        direction: 1 (long) or -1 (short).
        price: Trade price.
        equity: Current total equity.
        cash: Available cash.
        df: Ticker's indicator-enriched frame up to and including the current bar.
            Sizers that need ATR, volatility, etc. read from the last row.
    """

    symbol: str
    direction: int
    price: float
    equity: float
    cash: float
    df: pd.DataFrame


class BaseSizer(ABC):
    """Abstract base for position sizers."""

    def __init__(self, cost_model: CostModel | None = None):
        self.cost_model = cost_model or CostModel()

    @abstractmethod
    def size(self, request: SizingInput) -> float:
        """Return the share count for this entry. Return 0 to skip."""
