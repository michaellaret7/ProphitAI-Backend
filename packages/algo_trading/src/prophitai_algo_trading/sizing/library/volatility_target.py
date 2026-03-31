"""Volatility-targeted position sizing."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import PortfolioContext, TradeCandidate
from prophitai_algo_trading.sizing.base import BasePositionSizer


class VolatilityTargetSizer(BasePositionSizer):
    """Target a fixed portfolio volatility contribution per position."""

    def __init__(
        self,
        target_volatility: float = 0.10,
        max_pct_equity: float = 0.25,
        cost_model: CostModel | None = None,
    ):
        self.target_volatility = target_volatility
        self.max_pct_equity = max_pct_equity
        self._cost_model = cost_model or CostModel()
        self._volatilities: dict[str, float] = {}

    def update_volatilities(self, volatilities: dict[str, float]) -> None:
        """Refresh cached volatility estimates."""
        self._volatilities = {k: v for k, v in volatilities.items() if v > 0}

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        """Refresh rolling volatilities from close series."""
        from prophitai_algo_trading.utils.math_utils import compute_rolling_volatilities

        vols = compute_rolling_volatilities(ticker_closes)
        if vols:
            self.update_volatilities(vols)

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: TradeCandidate | None = None,
    ) -> float:
        """Allocate less capital to more volatile assets."""
        volatility = None
        if candidate is not None:
            volatility = candidate.volatility
        if volatility is None:
            volatility = self._volatilities.get(symbol)
        if volatility is None or volatility <= 0:
            return 0.0

        weight = min(self.target_volatility / volatility, self.max_pct_equity)
        target_value = min(context.equity * weight, context.cash)
        return self._cost_model.max_units(price, target_value)
