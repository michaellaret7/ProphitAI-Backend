"""Gross-exposure-capped wrapper for any base position sizer.

Fixes the chronic under-deployment pattern: with ``PercentOfEquitySizer(pct=1/N)``
and ``max_positions=N``, the portfolio converges to ~100% gross only when every
slot is full — typical L/S runs sit at 40-60% deployed because slots open and
close asymmetrically. Strategies that intend 150% gross (e.g. 100% long + 50%
short) never hit that target.

``GrossExposureSizer`` wraps a base sizer and re-scales every sizing decision
so the cumulative gross-exposure target is actually achieved: each new position
is sized to bring the portfolio to ``target_gross_pct`` proportionally, up to
``max_name_pct`` per name.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import EntryCandidate, PortfolioContext
from prophitai_algo_trading.sizing.base import BasePositionSizer


class GrossExposureSizer(BasePositionSizer):
    """Scale a base sizer's output to hit a target portfolio gross exposure.

    Args:
        base_sizer: The underlying sizer whose share count is the starting
            point. Any BasePositionSizer works — typically
            ``PercentOfEquitySizer(pct=max_name_pct)`` or a volatility sizer.
        target_gross_pct: Desired portfolio gross exposure as a fraction of
            equity. ``1.0`` = 100% (long-only fully invested);
            ``1.5`` = 150% (e.g. 100% long + 50% short);
            ``2.0`` = 200% (full L/S at 1x per leg).
        max_name_pct: Hard cap on any single position's notional as fraction
            of equity, applied AFTER the gross-exposure rescale. Enforces
            diversification regardless of target exposure. Default ``0.10``.
        cost_model: Cost model used to convert notional to share count. If
            None, uses a default zero-cost model.

    Example:
        >>> base = PercentOfEquitySizer(pct=0.06)
        >>> sizer = GrossExposureSizer(base, target_gross_pct=1.5, max_name_pct=0.06)
        # With 20 open positions averaging 5% notional each, gross=100% and
        # headroom=50% — each new entry targets up to 5% notional (capped at
        # max_name_pct) until gross hits 150%.
    """

    def __init__(
        self,
        base_sizer: BasePositionSizer,
        target_gross_pct: float = 1.0,
        max_name_pct: float = 0.10,
        cost_model: CostModel | None = None,
    ):
        if target_gross_pct <= 0:
            raise ValueError(
                f"target_gross_pct must be > 0, got {target_gross_pct}"
            )

        if not 0 < max_name_pct <= 1.0:
            raise ValueError(
                f"max_name_pct must be in (0, 1.0], got {max_name_pct}"
            )

        self.base_sizer = base_sizer
        self.target_gross_pct = target_gross_pct
        self.max_name_pct = max_name_pct
        self._cost_model = cost_model or CostModel()

    def prepare_for_bar(
        self,
        ticker_closes: dict[str, pd.Series],
        latest_prices: dict[str, float] | None = None,
        strategy_data: dict[str, pd.DataFrame] | None = None,
        timestamp: datetime | pd.Timestamp | None = None,
    ) -> None:
        """Forward market prep to the wrapped sizer."""

        self.base_sizer.prepare_for_bar(
            ticker_closes,
            latest_prices=latest_prices,
            strategy_data=strategy_data,
            timestamp=timestamp,
        )

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate: EntryCandidate | None = None,
    ) -> float:
        """Size the trade so cumulative gross targets ``target_gross_pct``.

        Algorithm:
        1. Ask the base sizer for a share count.
        2. Compute remaining gross-exposure headroom vs. target.
        3. Cap the notional at both the headroom and ``max_name_pct * equity``.
        4. Convert capped notional back to shares using the cost model.
        """

        base_shares = self.base_sizer.calculate_shares(
            symbol, price, context, candidate=candidate,
        )

        if pd.isna(base_shares) or base_shares <= 0:
            return 0.0

        if context.equity <= 0 or price <= 0:
            return 0.0

        base_notional = base_shares * price

        # Reason: gross_exposure is a dollar amount on PortfolioContext. Convert
        # target to dollars using current equity so the cap tracks equity growth.
        target_gross_dollars = self.target_gross_pct * context.equity
        headroom = target_gross_dollars - context.gross_exposure

        if headroom <= 0:
            # Reason: already at or above target — reject the entry. Forced
            # zero rather than a negative headroom clamp so the portfolio
            # doesn't overshoot by accident when multiple entries fire on
            # the same bar.
            return 0.0

        name_cap_dollars = self.max_name_pct * context.equity
        capped_notional = min(base_notional, headroom, name_cap_dollars, context.cash)

        if capped_notional <= 0:
            return 0.0

        return self._cost_model.max_units(price, capped_notional)
