"""Position sizing strategies for the execution layer.

Sizers determine how many shares to buy/sell based on price and portfolio
context. Injected into executors to decouple sizing logic from execution.
"""

from abc import ABC, abstractmethod

import pandas as pd

from prophitai_algo_trading.execution.models import PortfolioContext
from prophitai_algo_trading.execution.cost_model import CostModel


class BasePositionSizer(ABC):
    """Abstract base for position sizing strategies."""

    def prepare_for_bar(self, ticker_closes: dict[str, pd.Series]) -> None:
        """Optional hook called once per bar before sizing decisions.

        Allows sizers to refresh internal state (e.g., volatility estimates)
        from current price data. Default does nothing.

        Args:
            ticker_closes: Mapping of ticker -> close price Series up to current bar.
        """
        pass

    @abstractmethod
    def calculate_shares(self, symbol: str, price: float, context: PortfolioContext) -> float:
        """Calculate the number of shares to trade.

        Args:
            symbol: Ticker symbol being traded.
            price: Current price per share.
            context: Current portfolio state (equity, cash, positions).

        Returns:
            Number of shares to trade.
        """


class AllInSizer(BasePositionSizer):
    """Allocate all available cash to a single position.

    Args:
        cost_model: Transaction cost model for sizing calculations.
    """

    def __init__(self, cost_model: CostModel | None = None):
        self._cost_model = cost_model or CostModel()

    def calculate_shares(self, symbol: str, price: float, context: PortfolioContext) -> float:
        """Buy as many shares as cash allows, accounting for costs."""
        return self._cost_model.max_units(price, context.cash)


class FixedQuantitySizer(BasePositionSizer):
    """Always trade a fixed number of shares.

    Args:
        qty: Number of shares per trade.
        cost_model: Transaction cost model for cash validation.
    """

    def __init__(self, qty: float, cost_model: CostModel | None = None):
        self.qty = qty
        self._cost_model = cost_model or CostModel()

    def calculate_shares(self, symbol: str, price: float, context: PortfolioContext) -> float:
        """Return the fixed quantity, raising if insufficient cash after costs."""
        required = self._cost_model.total_outlay(price, self.qty)
        if required > context.cash:
            raise ValueError(
                f"Insufficient cash for {self.qty} shares of {symbol} at ${price:.2f}: "
                f"need ${required:.2f} (incl. costs), have ${context.cash:.2f}"
            )
        return self.qty


class PercentOfEquitySizer(BasePositionSizer):
    """Allocate a percentage of total equity to each position.

    Args:
        pct: Fraction of equity to allocate (e.g. 0.25 = 25%).
        cost_model: Transaction cost model for cost-aware sizing.
    """

    def __init__(self, pct: float, cost_model: CostModel | None = None):
        self.pct = pct
        self._cost_model = cost_model or CostModel()

    def calculate_shares(self, symbol: str, price: float, context: PortfolioContext) -> float:
        """Allocate pct of equity, capped at available cash, accounting for costs."""
        target_value = context.equity * self.pct
        capped_value = min(target_value, context.cash)
        return self._cost_model.max_units(price, capped_value)


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
            # Reason: clamp to max_weight and renormalize so weights still sum to 1.0
            clamped = {k: min(w, self._max_weight) for k, w in raw.items()}
            clamp_total = sum(clamped.values())
            self._weights = {k: v / clamp_total for k, v in clamped.items()} if clamp_total > 0 else {}
        else:
            self._weights = {}

    def prepare_for_bar(self, ticker_closes: dict[str, pd.Series]) -> None:
        """Recompute inverse-vol weights from latest close prices."""
        from prophitai_algo_trading.utils.math_utils import compute_rolling_volatilities

        vols = compute_rolling_volatilities(ticker_closes)
        if vols:
            self.update_volatilities(vols)

    def calculate_shares(self, symbol: str, price: float, context: PortfolioContext) -> float:
        """Allocate vol-weighted fraction of equity, capped at available cash."""
        weight = self._weights.get(symbol, 1.0 / self._max_positions)
        target_value = context.equity * weight
        capped_value = min(target_value, context.cash)
        return self._cost_model.max_units(price, capped_value)
