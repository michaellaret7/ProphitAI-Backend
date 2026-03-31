"""ATR-aware risk-budget position sizing."""

from __future__ import annotations

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import EntryCandidate, PortfolioContext
from prophitai_algo_trading.sizing.base import BasePositionSizer


class ATRRiskSizer(BasePositionSizer):
    """Size positions from a fixed risk budget per trade.

    Position size is computed from:
        risk_budget = equity * risk_pct
        shares = risk_budget / risk_per_share

    ``risk_per_share`` comes from the trade candidate's explicit
    ``risk_per_share`` or ``stop_distance``. When those are absent, this sizer
    can fall back to ``atr * atr_multiple``.
    """

    def __init__(
        self,
        risk_pct: float = 0.01,
        atr_multiple: float = 1.0,
        max_pct_equity: float | None = 0.20,
        cost_model: CostModel | None = None,
    ):
        self.risk_pct = risk_pct
        self.atr_multiple = atr_multiple
        self.max_pct_equity = max_pct_equity
        self._cost_model = cost_model or CostModel()

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: EntryCandidate | None = None,
    ) -> float:
        """Allocate shares from a risk-per-share estimate."""
        if candidate is None:
            raise ValueError("ATRRiskSizer requires an EntryCandidate.")

        risk_per_share = candidate.risk_per_share or candidate.stop_distance
        if risk_per_share is None and candidate.atr is not None:
            risk_per_share = candidate.atr * self.atr_multiple
        if risk_per_share is None or risk_per_share <= 0:
            return 0.0

        risk_budget = context.equity * self.risk_pct
        raw_shares = risk_budget / risk_per_share
        target_value = raw_shares * price

        if self.max_pct_equity is not None:
            target_value = min(target_value, context.equity * self.max_pct_equity)

        capped_value = min(target_value, context.cash)
        return self._cost_model.max_units(price, capped_value)
