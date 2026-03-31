"""Position sizing policy for the strategy scaffold."""

from __future__ import annotations

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import EntryCandidate, PortfolioContext
from prophitai_algo_trading.sizing.base import BasePositionSizer


class TemplatePositionSizer(BasePositionSizer):
    """Scale notional size by conviction while capping per-position exposure."""

    def __init__(
        self,
        base_equity_pct: float,
        max_equity_pct: float,
        conviction_scale: float,
        cost_model: CostModel | None = None,
    ) -> None:
        self.base_equity_pct = base_equity_pct
        self.max_equity_pct = max_equity_pct
        self.conviction_scale = conviction_scale
        self._cost_model = cost_model or CostModel()

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: EntryCandidate | None = None,
    ) -> float:
        """Allocate more notional to higher-conviction entry candidates."""
        if price <= 0:
            return 0.0

        conviction = 0.0
        if candidate is not None:
            conviction = max(float(candidate.score), 0.0)

        scaled_conviction = min(conviction / max(self.conviction_scale, 1e-9), 1.0)
        target_pct = self.base_equity_pct * (1.0 + scaled_conviction)
        capped_pct = min(target_pct, self.max_equity_pct)
        target_value = min(context.equity * capped_pct, context.cash)
        return self._cost_model.max_units(price, target_value)
