"""Unit tests for PortfolioTracker cash and P&L accounting."""

from datetime import datetime

import pytest

from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_sizer import AllInSizer
from prophitai_algo_trading.execution.cost_model import CostModel


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


# ================================
# --> Long position tests
# ================================

class TestLongPosition:
    """Verify long position cash accounting."""

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
