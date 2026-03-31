"""Regression tests for execution-layer trading rules."""

from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.execution.position_sizer import FixedQuantitySizer
from prophitai_algo_trading.rules.library.consecutive_loss import ConsecutiveLossRule
from prophitai_algo_trading.rules.library.max_daily_loss import MaxDailyLossRule
from prophitai_algo_trading.rules.library.max_drawdown import MaxDrawdownRule

T0 = datetime(2025, 1, 1, 9, 30)
T1 = datetime(2025, 1, 1, 9, 45)
T2 = datetime(2025, 1, 1, 10, 0)
DUMMY_DF = pd.DataFrame()


def _make_tracker() -> PortfolioTracker:
    cost_model = CostModel(ptc=0.0)
    return PortfolioTracker(
        initial_capital=1_000.0,
        sizer=FixedQuantitySizer(qty=1, cost_model=cost_model),
        cost_model=cost_model,
    )


def test_consecutive_loss_rule_resets_immediately_when_pause_is_zero():
    rule = ConsecutiveLossRule(max_losses=1, pause_bars=0)

    rule.on_entry("AAPL", 100.0, T0)
    rule.on_exit("AAPL", 90.0, T1)

    assert not rule.should_block_entry("AAPL", 90.0, T1, DUMMY_DF, None)


def test_consecutive_loss_rule_counts_unique_timestamps_once():
    rule = ConsecutiveLossRule(max_losses=1, pause_bars=2)

    rule.on_entry("AAPL", 100.0, T0)
    rule.on_exit("AAPL", 90.0, T0)

    assert rule.should_block_entry("AAPL", 90.0, T0, DUMMY_DF, None)

    rule.on_bar("AAPL", 90.0, T1)
    rule.on_bar("MSFT", 50.0, T1)

    assert rule.should_block_entry("AAPL", 90.0, T1, DUMMY_DF, None)

    rule.on_bar("AAPL", 90.0, T2)

    assert not rule.should_block_entry("AAPL", 90.0, T2, DUMMY_DF, None)


def test_max_daily_loss_rule_uses_full_portfolio_equity():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)
    tracker.open_long("MSFT", 100.0, T0)
    tracker.update_market_prices({"AAPL": 100.0, "MSFT": 100.0})

    rule = MaxDailyLossRule(max_pct=0.08)
    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, tracker)

    tracker.update_market_prices({"AAPL": 50.0, "MSFT": 50.0})

    assert rule.should_block_entry("AAPL", 50.0, T1, DUMMY_DF, tracker)


def test_max_drawdown_rule_uses_full_portfolio_equity():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)
    tracker.open_long("MSFT", 100.0, T0)
    tracker.update_market_prices({"AAPL": 100.0, "MSFT": 100.0})

    rule = MaxDrawdownRule(max_pct=0.08)
    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, tracker)

    tracker.update_market_prices({"AAPL": 50.0, "MSFT": 50.0})

    assert rule.should_block_entry("AAPL", 50.0, T1, DUMMY_DF, tracker)
