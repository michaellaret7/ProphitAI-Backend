"""Equity-based sizers: PercentOfEquity, AllIn, FixedQuantity."""

from __future__ import annotations

from prophitai_algo_trading.cost_model import CostModel
from prophitai_algo_trading.sizing.base import BaseSizer, SizingInput


class PercentOfEquitySizer(BaseSizer):
    """Allocate a fixed percentage of total equity to each trade.

    Args:
        pct: Fraction of equity (0.10 = 10%).
        cost_model: Transaction costs.
    """

    def __init__(self, pct: float, cost_model: CostModel | None = None):
        super().__init__(cost_model)
        self.pct = pct

    def size(self, request: SizingInput) -> float:
        target_value = request.equity * self.pct
        capped_value = min(target_value, request.cash) if request.direction == 1 else target_value

        return self.cost_model.max_shares(request.price, capped_value)


class AllInSizer(BaseSizer):
    """Spend all available cash on one position."""

    def size(self, request: SizingInput) -> float:
        return self.cost_model.max_shares(request.price, request.cash)


class FixedQuantitySizer(BaseSizer):
    """Always trade a fixed share count.

    Args:
        shares: Constant share count.
    """

    def __init__(self, shares: float, cost_model: CostModel | None = None):
        super().__init__(cost_model)
        self.shares = shares

    def size(self, request: SizingInput) -> float:
        return float(self.shares)
