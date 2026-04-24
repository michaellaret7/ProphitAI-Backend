"""MaxDrawdownRiskModel — peak-to-trough drawdown circuit breaker.

When portfolio equity falls ``max_drawdown_pct`` below its running peak,
scale every target's share count by ``delever_factor`` for
``cooldown_days``. After cooldown, reset the peak to current equity so
the strategy resumes from a fresh baseline (otherwise a strategy stuck
underwater would re-trigger the same drawdown forever).

Permanently-latching "halt" behavior was deliberately avoided after
seeing Lean's equivalent freeze a 5-year backtest on the 2020-11-26 gap.
Cooldown + delever keeps the algorithm alive through regime shifts.

Not a ``RiskRule`` — operates on the *list* of targets (scales them),
which falls outside the per-symbol hook surface. Lives alongside the
rules as a standalone ``RiskManagementModel``.
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.core.models import (
    AlgorithmContext,
    PortfolioTarget,
)
from prophitai_algo_trading.risk.base import PeakEquityTracker


class MaxDrawdownRiskModel:
    """Drawdown-triggered delever + cooldown.

    Args:
        max_drawdown_pct: Peak-to-trough threshold (0.15 = 15%).
        delever_factor: Multiplier applied to targets during cooldown
            (0.5 = cut gross in half). Must be in (0, 1].
        cooldown_days: Duration of the delever window in days. On
            expiry, the peak resets to current equity.
    """

    def __init__(
        self,
        max_drawdown_pct: float = 0.15,
        delever_factor: float = 0.5,
        cooldown_days: int = 30,
    ):
        if max_drawdown_pct <= 0:
            raise ValueError("max_drawdown_pct must be > 0")
        if not 0.0 < delever_factor <= 1.0:
            raise ValueError("delever_factor must be in (0, 1]")
        if cooldown_days <= 0:
            raise ValueError("cooldown_days must be > 0")

        self._max_dd = max_drawdown_pct
        self._delever = delever_factor
        self._cooldown_days = cooldown_days

        self._peak_tracker = PeakEquityTracker()
        self._cooldown_until = None

    def manage(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> list[PortfolioTarget]:
        equity = ctx.portfolio.equity()

        peak = self._peak_tracker.update(equity)

        now = ctx.timestamp

        # Reason: cooldown expiry — reset peak so we don't re-trigger
        # on the same prolonged drawdown.
        if self._cooldown_until is not None and now >= self._cooldown_until:
            self._cooldown_until = None
            self._peak_tracker.reset(equity)
            peak = equity

        # Reason: new breach — only trigger once per cooldown window.
        if self._cooldown_until is None and peak > 0.0:
            drawdown = (equity - peak) / peak

            if drawdown <= -self._max_dd:
                self._cooldown_until = now + timedelta(days=self._cooldown_days)

        if self._cooldown_until is not None:
            return [
                PortfolioTarget(
                    symbol=t.symbol,
                    target_shares=t.target_shares * self._delever,
                )
                for t in targets
            ]

        return list(targets)
