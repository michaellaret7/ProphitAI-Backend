"""Percent-of-equity position sizing policy."""

from __future__ import annotations

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import PortfolioContext, TradeCandidate
from prophitai_algo_trading.sizing.base import BasePositionSizer


class PercentOfEquitySizer(BasePositionSizer):
    """Allocate a percentage of total equity to each position.

    Args:
        pct: Fraction of equity to allocate (e.g. 0.25 = 25%).
        cost_model: Transaction cost model for cost-aware sizing.
    """

    def __init__(self, pct: float, cost_model: CostModel | None = None):
        self.pct = pct
        self._cost_model = cost_model or CostModel()

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        """Allocate pct of equity, capped at available cash, accounting for costs."""
        target_value = context.equity * self.pct
        capped_value = min(target_value, context.cash)
        return self._cost_model.max_units(price, capped_value)
