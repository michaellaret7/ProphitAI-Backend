"""Adaptive quality gate control for filtering weak entries and stale trades.

This control is designed as a broadly useful companion for existing strategies:
- learns a rolling distribution of candidate entry scores per ticker
- blocks the bottom percentile of signals once enough history exists
- optionally requires liquidity confirmation when volume columns exist
- optionally requires trend alignment using common indicator columns
- force-exits when the higher-level trade thesis breaks

It follows the AdvancedRiskControlTemplate pattern but ships as a concrete control
with defaults that are practical for most discretionary strategy testing.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.advanced_base import AdvancedRiskControlTemplate

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class QualityGateControl(AdvancedRiskControlTemplate):
    """Adaptive execution filter for weak entries and broken trades.

    The most useful feature is the adaptive score gate: instead of forcing
    a hardcoded score threshold, the rule learns each ticker's recent score
    distribution and blocks only the weakest slice of signals. This makes it
    portable across strategies whose score scales differ.

    Args:
        score_window: Number of recent candidate scores to retain per ticker.
        min_score_history: Minimum history required before score gating starts.
        min_score_percentile: Block entries below this rolling percentile.
        require_trend_alignment: Require common trend columns to agree with
            the candidate direction, and force-exit when that trend breaks.
        min_volume_ratio: Minimum volume confirmation when volume columns exist.
        max_atr_pct: Optional ATR/close ceiling to avoid unstable conditions.
        stop_loss_pct: Hard stop from entry.
        trail_after_profit_pct: Profit needed before the trailing stop arms.
        trailing_stop_pct: Retracement threshold once the trail is armed.
        max_bars_in_trade: Time stop.
        cooldown_bars_after_exit: Bars to wait before re-entry after exit.
    """

    def __init__(
        self,
        score_window: int = 80,
        min_score_history: int = 20,
        min_score_percentile: float = 0.35,
        require_trend_alignment: bool = True,
        min_volume_ratio: float | None = 1.05,
        max_atr_pct: float | None = None,
        stop_loss_pct: float | None = 0.03,
        trail_after_profit_pct: float | None = 0.02,
        trailing_stop_pct: float | None = 0.04,
        max_bars_in_trade: int | None = 48,
        cooldown_bars_after_exit: int = 4,
    ):
        super().__init__(
            min_entry_score=None,
            min_volume_ratio=min_volume_ratio,
            stop_loss_pct=stop_loss_pct,
            trail_after_profit_pct=trail_after_profit_pct,
            trailing_stop_pct=trailing_stop_pct,
            max_bars_in_trade=max_bars_in_trade,
            cooldown_bars_after_exit=cooldown_bars_after_exit,
        )
        self.score_window = score_window
        self.min_score_history = min_score_history
        self.min_score_percentile = min_score_percentile
        self.require_trend_alignment = require_trend_alignment
        self.max_atr_pct = max_atr_pct
        self._score_history: dict[str, deque[float]] = {}

    # ================================
    # --> Helper funcs
    # ================================

    def _score_blocked_for_ticker(self, ticker: str, df: pd.DataFrame) -> bool:
        score = self.candidate_score(df)
        history = self._score_history.setdefault(
            ticker,
            deque(maxlen=self.score_window),
        )

        blocked = False
        if len(history) >= self.min_score_history:
            threshold = float(pd.Series(list(history)).quantile(self.min_score_percentile))
            blocked = score < threshold

        history.append(score)
        return blocked

    def _atr_blocked(self, df: pd.DataFrame) -> bool:
        if self.max_atr_pct is None or not self.has_columns(df, "atr", "close"):
            return False
        latest = self.latest_row(df)
        close = float(latest["close"])
        atr = latest["atr"]
        if pd.isna(atr) or close <= 0:
            return False
        return float(atr) / close > self.max_atr_pct

    def _is_no_edge_regime(self, df: pd.DataFrame) -> bool:
        latest = self.latest_row(df)
        if "hurst_regime" in df.columns and latest["hurst_regime"] == 2:
            return True
        if "price_position" in df.columns and latest["price_position"] == "inside":
            return True
        return False

    def _trend_aligned(self, df: pd.DataFrame, direction: Direction) -> bool:
        latest = self.latest_row(df)

        if self.has_columns(df, "ema_fast", "ema_slow"):
            if pd.isna(latest["ema_fast"]) or pd.isna(latest["ema_slow"]):
                return True
            return (
                latest["ema_fast"] >= latest["ema_slow"]
                if direction == Direction.LONG
                else latest["ema_fast"] <= latest["ema_slow"]
            )

        if self.has_columns(df, "sma_fast", "sma_slow"):
            if pd.isna(latest["sma_fast"]) or pd.isna(latest["sma_slow"]):
                return True
            return (
                latest["sma_fast"] >= latest["sma_slow"]
                if direction == Direction.LONG
                else latest["sma_fast"] <= latest["sma_slow"]
            )

        if self.has_columns(df, "sma_trend", "close"):
            if pd.isna(latest["sma_trend"]):
                return True
            return (
                latest["close"] >= latest["sma_trend"]
                if direction == Direction.LONG
                else latest["close"] <= latest["sma_trend"]
            )

        if self.has_columns(df, "tenkan", "kijun", "price_position"):
            if pd.isna(latest["tenkan"]) or pd.isna(latest["kijun"]):
                return True
            if direction == Direction.LONG:
                return (
                    latest["tenkan"] >= latest["kijun"]
                    and latest["price_position"] == "above"
                )
            return (
                latest["tenkan"] <= latest["kijun"]
                and latest["price_position"] == "below"
            )

        if self.has_columns(df, "sma_50", "close"):
            if pd.isna(latest["sma_50"]):
                return True
            return (
                latest["close"] >= latest["sma_50"]
                if direction == Direction.LONG
                else latest["close"] <= latest["sma_50"]
            )

        return True

    # ================================
    # --> RiskControl impl
    # ================================

    def should_block_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        if super().should_block_entry(ticker, price, timestamp, df, portfolio):
            return True

        direction = self.candidate_direction(df)
        if direction is None:
            return True
        if self._is_no_edge_regime(df):
            return True
        if self._atr_blocked(df):
            return True
        if self._score_blocked_for_ticker(ticker, df):
            return True
        if self.require_trend_alignment and not self._trend_aligned(df, direction):
            return True

        return False

    def should_force_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        df: pd.DataFrame,
        portfolio: PortfolioTracker,
    ) -> bool:
        if super().should_force_exit(ticker, price, timestamp, df, portfolio):
            return True

        pos = portfolio.get_position(ticker)
        if pos is None:
            return False
        if self._is_no_edge_regime(df):
            return True
        if self.require_trend_alignment and not self._trend_aligned(df, pos.direction):
            return True

        return False
