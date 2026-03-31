"""Inverse-volatility position sizing policy."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import EntryCandidate, PortfolioContext
from prophitai_algo_trading.sizing.base import BasePositionSizer


class InverseVolatilitySizer(BasePositionSizer):
    """Allocate capital inversely proportional to each ticker's volatility.

    Less volatile assets get larger allocations, more volatile assets get
    smaller ones. Weights are computed as (1/vol_i) / sum(1/vol_j) so they
    sum to 1.0 across the full universe.

    Engines call ``prepare_for_bar(ticker_closes)`` each bar, which computes
    rolling volatilities internally and refreshes weights. If a ticker has no
    volatility entry, it falls back to equal-weight (1/max_positions).

    Args:
        max_positions: Maximum concurrent positions (used for fallback weight).
        max_weight: Maximum allocation weight for any single ticker (e.g. 0.10 = 10%).
        cost_model: Transaction cost model for cost-aware sizing.
    """

    def __init__(
        self,
        max_positions: int = 10,
        max_weight: float = 0.10,
        cost_model: CostModel | None = None,
    ):
        self._max_positions = max_positions
        self._max_weight = max_weight
        self._cost_model = cost_model or CostModel()
        self._volatilities: dict[str, float] = {}
        self._weights: dict[str, float] = {}

    # ================================
    # --> Helper funcs
    # ================================

    def _apply_weight_cap(self, raw_weights: dict[str, float]) -> dict[str, float]:
        """Apply a hard per-name cap without forcing full reinvestment."""
        capped_weights: dict[str, float] = {}
        remaining_symbols = set(raw_weights)
        remaining_budget = 1.0

        while remaining_symbols and remaining_budget > 0:
            raw_total = sum(raw_weights[symbol] for symbol in remaining_symbols)
            if raw_total <= 0:
                break

            provisional = {
                symbol: remaining_budget * (raw_weights[symbol] / raw_total)
                for symbol in remaining_symbols
            }
            breached = {
                symbol for symbol, weight in provisional.items()
                if weight > self._max_weight
            }

            if not breached:
                capped_weights.update(provisional)
                break

            for symbol in breached:
                capped_weights[symbol] = self._max_weight
                remaining_budget -= self._max_weight
                remaining_symbols.remove(symbol)

        return capped_weights

    def update_volatilities(self, volatilities: dict[str, float]) -> None:
        """Refresh volatility estimates and recompute allocation weights.

        Args:
            volatilities: Mapping of ticker → annualized volatility (std of returns).
                          Zero or negative values are ignored.
        """
        self._volatilities = {k: v for k, v in volatilities.items() if v > 0}
        inv = {k: 1.0 / v for k, v in self._volatilities.items()}
        total = sum(inv.values())
        if total > 0:
            raw = {k: v / total for k, v in inv.items()}
            # Reason: max_weight is a hard cap; residual allocation may remain in cash.
            self._weights = self._apply_weight_cap(raw)
        else:
            self._weights = {}

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        """Recompute inverse-vol weights from latest close prices."""
        from prophitai_algo_trading.utils.math_utils import compute_rolling_volatilities

        vols = compute_rolling_volatilities(ticker_closes)
        
        if vols:
            self.update_volatilities(vols)

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: EntryCandidate | None = None,
    ) -> float:
        """Allocate vol-weighted fraction of equity, capped at available cash."""
        weight = self._weights.get(symbol, 1.0 / self._max_positions)
        target_value = context.equity * weight
        capped_value = min(target_value, context.cash)
        return self._cost_model.max_units(price, capped_value)
