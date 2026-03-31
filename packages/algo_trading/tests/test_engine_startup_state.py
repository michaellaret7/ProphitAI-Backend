"""Engine-level tests for live startup state hydration.

Validates the full hydration flow from BrokerStartupSnapshot through
to PortfolioTracker and PositionTracker state. Uses lightweight fake
data — no mocking framework, no broker connections.
"""

from datetime import datetime

import pytest

from prophitai_algo_trading.broker.models import (
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerStartupSnapshot,
)
from prophitai_algo_trading.engines.live.reconciliation import (
    hydrate_live_state,
    partition_positions,
    validate_open_orders,
)
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_tracker import PositionTracker
from prophitai_algo_trading.sizing import AllInSizer


CAPITAL = 100_000.0
T0 = datetime(2025, 6, 1, 14, 30, 0)


# ================================
# --> Helper funcs
# ================================

def _make_tracker(initial_capital: float = CAPITAL) -> PortfolioTracker:
    """Build a PortfolioTracker with zero-cost defaults for testing."""
    cost_model = CostModel()
    return PortfolioTracker(
        initial_capital=initial_capital,
        sizer=AllInSizer(cost_model=cost_model),
        cost_model=cost_model,
    )


def _make_position_trackers(tickers: list[str]) -> dict[str, PositionTracker]:
    """Build a fresh PositionTracker for each ticker."""
    return {t: PositionTracker() for t in tickers}


def _make_snapshot(
    cash: float = 85_000.0,
    equity: float = 100_000.0,
    positions: list[BrokerPositionSnapshot] | None = None,
    open_orders: list[BrokerOrderSnapshot] | None = None,
) -> BrokerStartupSnapshot:
    """Build a BrokerStartupSnapshot with sensible defaults."""
    return BrokerStartupSnapshot(
        cash=cash,
        equity=equity,
        positions=positions or [],
        open_orders=open_orders or [],
        captured_at=T0,
    )


# ================================
# --> Partition tests
# ================================

class TestPartitionPositions:
    """Verify managed vs unmanaged partitioning logic."""

    def test_all_managed(self):
        positions = [
            BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0),
            BrokerPositionSnapshot("MSFT", 50, Direction.LONG, 300.0),
        ]
        managed, unmanaged = partition_positions(positions, ["AAPL", "MSFT", "NVDA"])

        assert len(managed) == 2
        assert len(unmanaged) == 0

    def test_mixed_managed_and_unmanaged(self):
        positions = [
            BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0),
            BrokerPositionSnapshot("GOOG", 25, Direction.LONG, 2800.0),
        ]
        managed, unmanaged = partition_positions(positions, ["AAPL", "MSFT"])

        assert [p.symbol for p in managed] == ["AAPL"]
        assert [p.symbol for p in unmanaged] == ["GOOG"]

    def test_no_positions(self):
        managed, unmanaged = partition_positions([], ["AAPL"])

        assert managed == []
        assert unmanaged == []


# ================================
# --> Open order validation tests
# ================================

class TestValidateOpenOrders:
    """Verify open order detection for managed symbols."""

    def test_no_orders_passes(self):
        validate_open_orders([], ["AAPL", "MSFT"])

    def test_unmanaged_orders_pass(self):
        """Orders for symbols not in the universe should not block startup."""
        orders = [
            BrokerOrderSnapshot("ord-1", "GOOG", "buy", 10, "new", "market"),
        ]
        validate_open_orders(orders, ["AAPL", "MSFT"])

    def test_managed_order_raises(self):
        """An open order for a managed symbol should block startup."""
        orders = [
            BrokerOrderSnapshot("ord-1", "AAPL", "buy", 10, "new", "limit"),
        ]
        with pytest.raises(RuntimeError, match="open orders exist for managed symbols"):
            validate_open_orders(orders, ["AAPL", "MSFT"])


# ================================
# --> Full hydration tests
# ================================

class TestHydrateLiveState:
    """End-to-end hydration from snapshot to tracker state."""

    def test_hydrate_long_position(self):
        """A broker long should appear in both trackers with correct state."""
        universe = ["AAPL", "MSFT"]
        snapshot = _make_snapshot(
            positions=[BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0)],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        summary = hydrate_live_state(
            snapshot=snapshot,
            portfolio_tracker=tracker,
            position_trackers=pos_trackers,
            latest_prices={"AAPL": 155.0, "MSFT": 310.0},
            active_universe=universe,
        )

        assert summary.success is True
        assert summary.hydrated_count == 1
        assert summary.hydrated_symbols == ["AAPL"]
        assert tracker.cash == pytest.approx(85_000.0)
        assert tracker.open_position_count == 1

        pos = tracker.get_position("AAPL")
        assert pos is not None
        assert pos.direction == Direction.LONG
        assert pos.shares == 100

        assert pos_trackers["AAPL"].position == 1
        assert pos_trackers["MSFT"].position == 0

    def test_hydrate_short_position(self):
        """A broker short should hydrate with position=-1."""
        universe = ["TSLA"]
        snapshot = _make_snapshot(
            cash=100_000.0,
            equity=100_000.0,
            positions=[BrokerPositionSnapshot("TSLA", 50, Direction.SHORT, 200.0)],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        summary = hydrate_live_state(
            snapshot=snapshot,
            portfolio_tracker=tracker,
            position_trackers=pos_trackers,
            latest_prices={"TSLA": 195.0},
            active_universe=universe,
        )

        assert summary.hydrated_count == 1
        assert pos_trackers["TSLA"].position == -1

        pos = tracker.get_position("TSLA")
        assert pos is not None
        assert pos.direction == Direction.SHORT

    def test_no_duplicate_entry_after_hydration(self):
        """After hydrating a long, PositionTracker should suppress a duplicate long signal."""
        universe = ["AAPL"]
        snapshot = _make_snapshot(
            positions=[BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0)],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        hydrate_live_state(
            snapshot=snapshot,
            portfolio_tracker=tracker,
            position_trackers=pos_trackers,
            latest_prices={"AAPL": 155.0},
            active_universe=universe,
        )

        # Reason: position is already 1 (long), so signal=1 produces no instructions
        instructions = pos_trackers["AAPL"].plan_transition(
            signal=1, price=155.0, timestamp=T0,
        )
        assert instructions == []

    def test_unmanaged_positions_raise(self):
        """Broker positions outside the universe should fail startup."""
        universe = ["AAPL"]
        snapshot = _make_snapshot(
            positions=[
                BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0),
                BrokerPositionSnapshot("GOOG", 25, Direction.LONG, 2800.0),
            ],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        with pytest.raises(RuntimeError, match="unmanaged broker positions"):
            hydrate_live_state(
                snapshot=snapshot,
                portfolio_tracker=tracker,
                position_trackers=pos_trackers,
                latest_prices={"AAPL": 155.0},
                active_universe=universe,
            )

    def test_open_orders_raise(self):
        """Open orders for managed symbols should fail startup."""
        universe = ["AAPL"]
        snapshot = _make_snapshot(
            positions=[],
            open_orders=[
                BrokerOrderSnapshot("ord-1", "AAPL", "buy", 10, "new", "limit"),
            ],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        with pytest.raises(RuntimeError, match="open orders exist for managed symbols"):
            hydrate_live_state(
                snapshot=snapshot,
                portfolio_tracker=tracker,
                position_trackers=pos_trackers,
                latest_prices={"AAPL": 155.0},
                active_universe=universe,
            )

    def test_flat_start_when_no_broker_positions(self):
        """With no broker positions, hydration should succeed with zero hydrated."""
        universe = ["AAPL", "MSFT"]
        snapshot = _make_snapshot(cash=100_000.0, equity=100_000.0, positions=[])
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        summary = hydrate_live_state(
            snapshot=snapshot,
            portfolio_tracker=tracker,
            position_trackers=pos_trackers,
            latest_prices={"AAPL": 155.0, "MSFT": 310.0},
            active_universe=universe,
        )

        assert summary.success is True
        assert summary.hydrated_count == 0
        assert tracker.cash == pytest.approx(100_000.0)
        assert tracker.open_position_count == 0

    def test_exit_signal_closes_hydrated_position(self):
        """A flat signal after hydration should produce a close instruction."""
        universe = ["AAPL"]
        snapshot = _make_snapshot(
            positions=[BrokerPositionSnapshot("AAPL", 100, Direction.LONG, 150.0)],
        )
        tracker = _make_tracker(initial_capital=snapshot.equity)
        pos_trackers = _make_position_trackers(universe)

        hydrate_live_state(
            snapshot=snapshot,
            portfolio_tracker=tracker,
            position_trackers=pos_trackers,
            latest_prices={"AAPL": 155.0},
            active_universe=universe,
        )

        # Reason: signal=0 on a hydrated long should produce a close_long instruction
        instructions = pos_trackers["AAPL"].plan_transition(
            signal=0, price=160.0, timestamp=T0,
        )
        assert len(instructions) == 1
        assert instructions[0]["reason"] == "close_long"
