"""All-in position sizing policy."""

from __future__ import annotations

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import EntryCandidate, PortfolioContext
from prophitai_algo_trading.sizing.base import BasePositionSizer


class AllInSizer(BasePositionSizer):
    """Allocate all available cash to a single position.

    Args:
        cost_model: Transaction cost model for sizing calculations.
    """

    def __init__(self, cost_model: CostModel | None = None):
        self._cost_model = cost_model or CostModel()

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: EntryCandidate | None = None,
    ) -> float:
        """Buy as many shares as cash allows, accounting for costs."""
        return self._cost_model.max_units(price, context.cash)
