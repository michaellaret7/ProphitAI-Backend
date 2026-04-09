"""Risk control contract tests.

Validates that a strategy's risk controls conform to the ``RiskControl``
interface: instantiation, bool returns, and lifecycle hooks.

All tests skip when ``manifest.build_risk_controls`` is None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.risk.base import RiskControl
from prophitai_algo_trading.sizing.std_lib.equity.fixed_quantity import (
    FixedQuantitySizer,
)
from prophitai_shared import get_current_utc_time

from prophitai_algo_trading.testing.fixtures import uptrend

if TYPE_CHECKING:
    from prophitai_algo_trading.testing.manifest import StrategyTestManifest


# ================================
# --> Helper funcs
# ================================


def _make_portfolio(initial_capital: float = 100_000.0) -> PortfolioTracker:
    """Build a real PortfolioTracker with a simple fixed-quantity sizer."""
    sizer = FixedQuantitySizer(qty=10, cost_model=CostModel())

    return PortfolioTracker(
        initial_capital=initial_capital,
        sizer=sizer,
        cost_model=CostModel(),
    )


class RiskControlContract:
    """Mixin — inherit and set ``manifest`` to get risk control tests."""

    manifest: StrategyTestManifest

    def test_risk_controls_instantiate(self) -> None:
        """Each risk control factory returns a RiskControl instance."""
        if self.manifest.build_risk_controls is None:
            pytest.skip("No build_risk_controls declared in manifest")

        controls = self.manifest.build_risk_controls()

        assert len(controls) > 0, "build_risk_controls returned empty list"

        for control in controls:
            assert isinstance(control, RiskControl), (
                f"{type(control).__name__} is not a RiskControl"
            )

    def test_should_block_entry_returns_bool(self) -> None:
        """should_block_entry returns a bool without crashing."""
        if self.manifest.build_risk_controls is None:
            pytest.skip("No build_risk_controls declared in manifest")

        strategy = self.manifest.build_strategy()
        df = uptrend()
        enriched = strategy.calculate_indicators(df)

        portfolio = _make_portfolio()
        timestamp = enriched.index[-1].to_pydatetime()

        for control in self.manifest.build_risk_controls():
            result = control.should_block_entry(
                ticker="TEST",
                price=100.0,
                timestamp=timestamp,
                df=enriched,
                portfolio=portfolio,
            )

            assert isinstance(result, bool), (
                f"{type(control).__name__}.should_block_entry returned "
                f"{type(result).__name__}, not bool"
            )

    def test_should_force_exit_returns_bool(self) -> None:
        """should_force_exit returns a bool without crashing."""
        if self.manifest.build_risk_controls is None:
            pytest.skip("No build_risk_controls declared in manifest")

        strategy = self.manifest.build_strategy()
        df = uptrend()
        enriched = strategy.calculate_indicators(df)

        portfolio = _make_portfolio()
        timestamp = enriched.index[-1].to_pydatetime()

        for control in self.manifest.build_risk_controls():
            result = control.should_force_exit(
                ticker="TEST",
                price=100.0,
                timestamp=timestamp,
                df=enriched,
                portfolio=portfolio,
            )

            assert isinstance(result, bool), (
                f"{type(control).__name__}.should_force_exit returned "
                f"{type(result).__name__}, not bool"
            )

    def test_lifecycle_hooks_callable(self) -> None:
        """on_entry, on_exit, and on_bar run without raising."""
        if self.manifest.build_risk_controls is None:
            pytest.skip("No build_risk_controls declared in manifest")

        now = get_current_utc_time()

        for control in self.manifest.build_risk_controls():
            control.on_entry("TEST", 100.0, now, Direction.LONG)
            control.on_exit("TEST", 105.0, now, Direction.LONG)
            control.on_bar("TEST", 102.0, now)
