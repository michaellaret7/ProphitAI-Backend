"""Fixed-quantity position sizing policy."""

from __future__ import annotations

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import PortfolioContext, TradeCandidate
from prophitai_algo_trading.sizing.base import BasePositionSizer


class FixedQuantitySizer(BasePositionSizer):
    """Always trade a fixed number of shares.

    Args:
        qty: Number of shares per trade.
        cost_model: Transaction cost model for cash validation.
    """

    def __init__(self, qty: float, cost_model: CostModel | None = None):
        self.qty = qty
        self._cost_model = cost_model or CostModel()

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        """Return the fixed quantity, raising if insufficient cash after costs."""
        required = self._cost_model.total_outlay(price, self.qty)
        if required > context.cash:
            raise ValueError(
                f"Insufficient cash for {self.qty} shares of {symbol} at ${price:.2f}: "
                f"need ${required:.2f} (incl. costs), have ${context.cash:.2f}"
            )
        return self.qty
