"""Unit tests for PortfolioTracker cash and P&L accounting."""

from datetime import datetime

import pytest

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.models import Direction, PortfolioContext
from prophitai_algo_trading.sizing import AllInSizer, BasePositionSizer


CAPITAL = 100_000.0
COMMISSION = 0.001  # 0.1%
T0 = datetime(2025, 1, 1)
T1 = datetime(2025, 1, 2)


def _make_tracker(commission_pct: float = 0.0) -> PortfolioTracker:
    cost_model = CostModel(ptc=commission_pct)
    return PortfolioTracker(
        initial_capital=CAPITAL,
        sizer=AllInSizer(cost_model=cost_model),
        cost_model=cost_model,
    )


class ZeroShareSizer(BasePositionSizer):
    """Sizer that intentionally skips entries."""

    def calculate_shares(
        self,
        symbol: str,
        price: float,
        context: PortfolioContext,
        candidate=None,
    ) -> float:
        return 0.0


# ================================
# --> Long position tests
# ================================

class TestLongPosition:
    """Verify long position cash accounting."""

    def test_long_entry_skips_when_sizer_returns_zero_shares(self):
        """A skipped long entry should leave cash and positions unchanged."""
        tracker = PortfolioTracker(
            initial_capital=CAPITAL,
            sizer=ZeroShareSizer(),
            cost_model=CostModel(),
        )

        tracker.open_long("AAPL", 50.0, T0)

        assert tracker.cash == pytest.approx(CAPITAL)
        assert tracker.get_position("AAPL") is None
        assert tracker.open_position_count == 0

    def test_long_round_trip_no_commission(self):
        """Open long at $50, close at $60 — expect 20% profit on full capital."""
        tracker = _make_tracker()
        tracker.open_long("AAPL", 50.0, T0)

        assert tracker.cash == pytest.approx(0.0, abs=0.01)

        tracker.close_position("AAPL", 60.0, T1)
        shares = CAPITAL / 50.0
        expected_pnl = (60.0 - 50.0) * shares

        assert tracker.cash == pytest.approx(CAPITAL + expected_pnl, abs=0.01)
        assert len(tracker._trades) == 1
        assert tracker._trades[0].pnl == pytest.approx(expected_pnl, abs=0.01)

    def test_long_round_trip_with_commission(self):
        """Long round-trip with commission deducted on both entry and exit."""
        tracker = _make_tracker(commission_pct=COMMISSION)
        tracker.open_long("AAPL", 50.0, T0)

        # Reason: AllInSizer accounts for commission: shares = cash / (price * (1 + comm))
        shares = CAPITAL / (50.0 * (1 + COMMISSION))
        entry_comm = shares * 50.0 * COMMISSION
        assert tracker.cash == pytest.approx(0.0, abs=0.01)

        tracker.close_position("AAPL", 60.0, T1)
        exit_comm = shares * 60.0 * COMMISSION
        expected_pnl = (60.0 - 50.0) * shares - (entry_comm + exit_comm)

        assert tracker._trades[0].pnl == pytest.approx(expected_pnl, abs=0.01)

    def test_long_loss(self):
        """Long position that loses money — ending cash < initial capital."""
        tracker = _make_tracker()
        tracker.open_long("AAPL", 50.0, T0)
        tracker.close_position("AAPL", 40.0, T1)

        shares = CAPITAL / 50.0
        expected_pnl = (40.0 - 50.0) * shares

        assert tracker.cash == pytest.approx(CAPITAL + expected_pnl, abs=0.01)
        assert tracker._trades[0].pnl < 0


# ================================
# --> Short position tests
# ================================

class TestShortPosition:
    """Verify short position cash accounting (the subtle case)."""

    def test_short_round_trip_no_commission(self):
        """Open short at $50, close at $40 — expect profit from price decline."""
        tracker = _make_tracker()
        tracker.open_short("AAPL", 50.0, T0)

        # Reason: for shorts, cash is retained as margin; no cost deducted on entry
        assert tracker.cash == pytest.approx(CAPITAL, abs=0.01)

        tracker.close_position("AAPL", 40.0, T1)
        shares = CAPITAL / 50.0
        expected_pnl = (50.0 - 40.0) * shares

        assert tracker.cash == pytest.approx(CAPITAL + expected_pnl, abs=0.01)
        assert tracker._trades[0].pnl == pytest.approx(expected_pnl, abs=0.01)

    def test_short_round_trip_with_commission(self):
        """Short round-trip with commission — verifies cash += pnl + entry_commission."""
        tracker = _make_tracker(commission_pct=COMMISSION)
        tracker.open_short("AAPL", 50.0, T0)

        shares = CAPITAL / (50.0 * (1 + COMMISSION))
        entry_comm = shares * 50.0 * COMMISSION

        # Reason: only entry commission deducted from cash on short open
        assert tracker.cash == pytest.approx(CAPITAL - entry_comm, abs=0.01)

        tracker.close_position("AAPL", 40.0, T1)
        exit_comm = shares * 40.0 * COMMISSION
        total_comm = entry_comm + exit_comm
        expected_pnl = (50.0 - 40.0) * shares - total_comm

        # Reason: close_position does cash += pnl + entry_commission
        # So final cash = (CAPITAL - entry_comm) + pnl + entry_comm = CAPITAL + pnl
        assert tracker.cash == pytest.approx(CAPITAL + expected_pnl, abs=0.01)
        assert tracker._trades[0].pnl == pytest.approx(expected_pnl, abs=0.01)

    def test_short_loss(self):
        """Short position that loses money — price goes up."""
        tracker = _make_tracker()
        tracker.open_short("AAPL", 50.0, T0)
        tracker.close_position("AAPL", 60.0, T1)

        shares = CAPITAL / 50.0
        expected_pnl = (50.0 - 60.0) * shares

        assert tracker.cash == pytest.approx(CAPITAL + expected_pnl, abs=0.01)
        assert tracker._trades[0].pnl < 0


# ================================
# --> Equity recording tests
# ================================

class TestEquityRecording:
    """Verify equity snapshots reflect mark-to-market values."""

    def test_equity_with_open_long(self):
        """Equity snapshot should reflect unrealized gain on open long."""
        tracker = _make_tracker()
        tracker.open_long("AAPL", 50.0, T0)
        tracker.record_equity(T1, {"AAPL": 55.0})

        eq = tracker.get_equity_curve()
        shares = CAPITAL / 50.0
        expected_equity = 0.0 + shares * 55.0  # cash=0, position at market price

        assert eq["equity"].iloc[0] == pytest.approx(expected_equity, abs=0.01)

    def test_equity_with_open_short(self):
        """Equity snapshot should reflect unrealized gain on open short."""
        tracker = _make_tracker()
        tracker.open_short("AAPL", 50.0, T0)
        tracker.record_equity(T1, {"AAPL": 45.0})

        eq = tracker.get_equity_curve()
        shares = CAPITAL / 50.0
        # Reason: short equity = cash + shares * (entry - current)
        expected_equity = CAPITAL + shares * (50.0 - 45.0)

        assert eq["equity"].iloc[0] == pytest.approx(expected_equity, abs=0.01)


# ================================
# --> Hydration tests (live startup)
# ================================

class TestHydration:
    """Verify seed methods used during live startup hydration."""

    def test_seed_cash_overrides_initial_capital(self):
        """seed_cash should set cash to broker-reported value, not initial_capital."""
        tracker = _make_tracker()
        assert tracker.cash == pytest.approx(CAPITAL)

        broker_cash = 75_000.0
        tracker.seed_cash(broker_cash)

        assert tracker.cash == pytest.approx(broker_cash)

    def test_seed_long_position(self):
        """Seeding a long position should appear in _positions and count."""
        tracker = _make_tracker()
        tracker.seed_position(
            symbol="AAPL",
            shares=100.0,
            direction=Direction.LONG,
            entry_price=150.0,
            entry_date=T0,
        )

        pos = tracker.get_position("AAPL")
        assert pos is not None
        assert pos.shares == 100.0
        assert pos.direction == Direction.LONG
        assert pos.entry_price == 150.0
        assert tracker.open_position_count == 1

    def test_seed_short_position(self):
        """Seeding a short position should appear in _positions and count."""
        tracker = _make_tracker()
        tracker.seed_position(
            symbol="TSLA",
            shares=50.0,
            direction=Direction.SHORT,
            entry_price=200.0,
            entry_date=T0,
        )

        pos = tracker.get_position("TSLA")
        assert pos is not None
        assert pos.shares == 50.0
        assert pos.direction == Direction.SHORT
        assert tracker.open_position_count == 1

    def test_equity_after_hydration_long(self):
        """Total equity after hydrating a long position should reflect market value."""
        tracker = _make_tracker()
        # Reason: simulate broker state — equity=100k, cash=85k, 100 shares AAPL@150
        tracker.seed_cash(85_000.0)
        tracker.seed_position(
            symbol="AAPL",
            shares=100.0,
            direction=Direction.LONG,
            entry_price=150.0,
            entry_date=T0,
        )

        # Reason: mark-to-market at current price of 160
        equity = tracker.get_total_equity(prices={"AAPL": 160.0})
        expected = 85_000.0 + 100.0 * 160.0  # cash + position value

        assert equity == pytest.approx(expected, abs=0.01)

    def test_equity_after_hydration_short(self):
        """Total equity after hydrating a short position should reflect P&L."""
        tracker = _make_tracker()
        tracker.seed_cash(100_000.0)
        tracker.seed_position(
            symbol="TSLA",
            shares=50.0,
            direction=Direction.SHORT,
            entry_price=200.0,
            entry_date=T0,
        )

        # Reason: short position value = shares * (entry - current)
        equity = tracker.get_total_equity(prices={"TSLA": 190.0})
        position_value = 50.0 * (200.0 - 190.0)
        expected = 100_000.0 + position_value

        assert equity == pytest.approx(expected, abs=0.01)

    def test_multiple_hydrated_positions(self):
        """Multiple seeded positions should all be tracked correctly."""
        tracker = _make_tracker()
        tracker.seed_cash(50_000.0)

        tracker.seed_position("AAPL", 100.0, Direction.LONG, 150.0, T0)
        tracker.seed_position("MSFT", 200.0, Direction.LONG, 300.0, T0)
        tracker.seed_position("NVDA", 30.0, Direction.SHORT, 500.0, T0)

        assert tracker.open_position_count == 3
        assert set(tracker.open_symbols) == {"AAPL", "MSFT", "NVDA"}

    def test_close_hydrated_position(self):
        """A hydrated position should be closeable through normal close_position."""
        tracker = _make_tracker()
        tracker.seed_cash(85_000.0)
        tracker.seed_position("AAPL", 100.0, Direction.LONG, 150.0, T0)

        tracker.close_position("AAPL", 160.0, T1)

        assert tracker.get_position("AAPL") is None
        assert tracker.open_position_count == 0
        assert len(tracker._trades) == 1
        assert tracker._trades[0].pnl == pytest.approx(
            (160.0 - 150.0) * 100.0, abs=0.01,
        )

    def test_seed_latest_prices(self):
        """seed_latest_prices should populate the internal price cache."""
        tracker = _make_tracker()
        prices = {"AAPL": 155.0, "MSFT": 310.0}
        tracker.seed_latest_prices(prices)

        assert tracker._latest_prices["AAPL"] == 155.0
        assert tracker._latest_prices["MSFT"] == 310.0
