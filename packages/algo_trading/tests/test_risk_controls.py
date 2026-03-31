"""Regression tests for execution-layer risk controls."""

from datetime import datetime, timedelta

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker
from prophitai_algo_trading.risk.base import (
    RISK_CANDIDATE_SCORE_ATTR,
    RISK_CANDIDATE_TARGET_ATTR,
    RiskControl,
)
from prophitai_algo_trading.risk.engine import RiskEngine
from prophitai_algo_trading.risk.controls.consecutive_loss_cooldown import (
    ConsecutiveLossCooldownControl,
)
from prophitai_algo_trading.risk.controls.daily_loss_limit import DailyLossLimitControl
from prophitai_algo_trading.risk.controls.earnings_blackout import (
    EarningsBlackoutControl,
)
from prophitai_algo_trading.risk.controls.portfolio_drawdown_limit import (
    PortfolioDrawdownLimitControl,
)
from prophitai_algo_trading.risk.controls.quality_gate import QualityGateControl
from prophitai_algo_trading.risk.controls.trailing_stop_exit import (
    TrailingStopExitControl,
)
from prophitai_algo_trading.sizing import FixedQuantitySizer

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


class _CandidateAwareControl(RiskControl):
    def __init__(self):
        self.last_direction: Direction | None = None
        self.last_score: float | None = None

    def should_block_entry(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        self.last_direction = self.candidate_direction(df)
        self.last_score = self.candidate_score(df)
        return (
            self.last_direction == Direction.SHORT
            or (self.last_score is not None and self.last_score < 2.0)
        )

    def should_force_exit(
        self, ticker: str, price: float, timestamp: datetime,
        df: pd.DataFrame, portfolio: PortfolioTracker,
    ) -> bool:
        return False


def test_consecutive_loss_cooldown_control_resets_immediately_when_pause_is_zero():
    rule = ConsecutiveLossCooldownControl(max_losses=1, pause_bars=0)

    rule.on_entry("AAPL", 100.0, T0)
    rule.on_exit("AAPL", 90.0, T1)

    assert not rule.should_block_entry("AAPL", 90.0, T1, DUMMY_DF, None)


def test_consecutive_loss_cooldown_control_counts_unique_timestamps_once():
    rule = ConsecutiveLossCooldownControl(max_losses=1, pause_bars=2)

    rule.on_entry("AAPL", 100.0, T0)
    rule.on_exit("AAPL", 90.0, T0)

    assert rule.should_block_entry("AAPL", 90.0, T0, DUMMY_DF, None)

    rule.on_bar("AAPL", 90.0, T1)
    rule.on_bar("MSFT", 50.0, T1)

    assert rule.should_block_entry("AAPL", 90.0, T1, DUMMY_DF, None)

    rule.on_bar("AAPL", 90.0, T2)

    assert not rule.should_block_entry("AAPL", 90.0, T2, DUMMY_DF, None)


def test_consecutive_loss_cooldown_control_only_blocks_the_losing_ticker():
    rule = ConsecutiveLossCooldownControl(max_losses=1, pause_bars=2)

    rule.on_entry("AAPL", 100.0, T0)
    rule.on_exit("AAPL", 90.0, T0)

    assert rule.should_block_entry("AAPL", 90.0, T0, DUMMY_DF, None)
    assert not rule.should_block_entry("MSFT", 50.0, T0, DUMMY_DF, None)


def test_daily_loss_limit_control_uses_full_portfolio_equity():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)
    tracker.open_long("MSFT", 100.0, T0)
    tracker.update_market_prices({"AAPL": 100.0, "MSFT": 100.0})

    rule = DailyLossLimitControl(max_pct=0.08)
    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, tracker)

    tracker.update_market_prices({"AAPL": 50.0, "MSFT": 50.0})

    assert rule.should_block_entry("AAPL", 50.0, T1, DUMMY_DF, tracker)


def test_portfolio_drawdown_limit_control_uses_full_portfolio_equity():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)
    tracker.open_long("MSFT", 100.0, T0)
    tracker.update_market_prices({"AAPL": 100.0, "MSFT": 100.0})

    rule = PortfolioDrawdownLimitControl(max_pct=0.08)
    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, tracker)

    tracker.update_market_prices({"AAPL": 50.0, "MSFT": 50.0})

    assert rule.should_block_entry("AAPL", 50.0, T1, DUMMY_DF, tracker)


def test_risk_engine_exposes_candidate_entry_metadata_to_controls():
    rule = _CandidateAwareControl()
    engine = RiskEngine([rule])
    df = pd.DataFrame({"close": [100.0]})

    assert engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=2.5)
    assert rule.last_direction == Direction.LONG
    assert rule.last_score == 2.5
    assert RISK_CANDIDATE_TARGET_ATTR not in df.attrs
    assert RISK_CANDIDATE_SCORE_ATTR not in df.attrs

    assert not engine.allows_entry("AAPL", 100.0, T0, df, None, target=-1, score=2.5)
    assert rule.last_direction == Direction.SHORT


def test_trailing_stop_exit_control_updates_best_price_on_bar():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)

    rule = TrailingStopExitControl(pct=0.05)
    rule.on_entry("AAPL", 100.0, T0, Direction.LONG)
    rule.on_bar("AAPL", 110.0, T1)

    assert not rule.should_force_exit("AAPL", 104.6, T1, DUMMY_DF, tracker)
    assert rule.should_force_exit("AAPL", 104.5, T1, DUMMY_DF, tracker)


def test_earnings_blackout_control_uses_injected_dates():
    upcoming = T0 + timedelta(days=1)
    rule = EarningsBlackoutControl(days=2, earnings_dates={"AAPL": upcoming})

    assert rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, None)


class _ExplodingEarningsControl(EarningsBlackoutControl):
    def _query_earnings_date(self, ticker: str):
        raise RuntimeError("db unavailable")


def test_earnings_blackout_control_handles_lookup_failures():
    rule = _ExplodingEarningsControl(days=2)

    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, None)


class _FlakyEarningsControl(EarningsBlackoutControl):
    def __init__(self, days: int):
        super().__init__(days=days)
        self.calls = 0

    def _query_earnings_date(self, ticker: str):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("db unavailable")
        return T0 + timedelta(days=1)


def test_earnings_blackout_control_retries_after_lookup_failures():
    rule = _FlakyEarningsControl(days=2)

    assert not rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, None)
    assert rule.should_block_entry("AAPL", 100.0, T0, DUMMY_DF, None)
    assert rule.calls == 2


def test_quality_gate_control_blocks_bottom_tier_scores_after_history_builds():
    rule = QualityGateControl(
        score_window=10,
        min_score_history=3,
        min_score_percentile=0.5,
        require_trend_alignment=False,
        min_volume_ratio=None,
        max_atr_pct=None,
        stop_loss_pct=None,
        trail_after_profit_pct=None,
        trailing_stop_pct=None,
        max_bars_in_trade=None,
        cooldown_bars_after_exit=0,
    )
    engine = RiskEngine([rule])
    df = pd.DataFrame({"close": [100.0]})

    assert engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=5.0)
    assert engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=4.0)
    assert engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=3.0)

    assert not engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=2.0)
    assert engine.allows_entry("AAPL", 100.0, T0, df, None, target=1, score=4.5)


def test_quality_gate_control_forces_exit_when_trend_breaks():
    tracker = _make_tracker()
    tracker.open_long("AAPL", 100.0, T0)
    tracker.update_market_prices({"AAPL": 95.0})

    rule = QualityGateControl(
        require_trend_alignment=True,
        min_score_history=99,
        min_volume_ratio=None,
        max_atr_pct=None,
        stop_loss_pct=None,
        trail_after_profit_pct=None,
        trailing_stop_pct=None,
        max_bars_in_trade=None,
        cooldown_bars_after_exit=0,
    )
    df = pd.DataFrame({"close": [95.0], "sma_trend": [100.0]})

    assert rule.should_force_exit("AAPL", 95.0, T1, df, tracker)
