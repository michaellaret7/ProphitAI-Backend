"""Advanced risk-control template for direction-aware, stateful trade management.

Copy and adapt this file when you need a risk control that combines:
- directional entry gating
- regime / liquidity / score filters
- stateful exits (stop, trailing stop, time stop)
- post-exit cooldowns

The goal is to give agent-generated risk controls a much stronger starting
point than the simple one-condition examples in the standard risk library.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from prophitai_algo_trading.execution.models import Direction
from prophitai_algo_trading.risk.base import RiskControl

if TYPE_CHECKING:
    from prophitai_algo_trading.execution.portfolio_tracker import PortfolioTracker


class AdvancedRiskControlTemplate(RiskControl):
    """Reference scaffold for complex execution-layer risk controls.

    Example patterns this template supports:
    - Allow longs only in a bullish regime, shorts only in a bearish regime
    - Reject low-conviction entries using the strategy score
    - Require liquidity or volatility confirmation from indicator columns
    - Start with a hard stop, then upgrade to a trailing stop after profits
    - Pause re-entry for N bars after a stop-out
    """

    def __init__(
        self,
        allowed_directions: tuple[Direction, ...] = (
            Direction.LONG,
            Direction.SHORT,
        ),
        regime_column: str | None = None,
        allowed_long_regimes: tuple[str | int, ...] = (),
        allowed_short_regimes: tuple[str | int, ...] = (),
        min_entry_score: float | None = None,
        min_volume_ratio: float | None = None,
        stop_loss_pct: float | None = None,
        trail_after_profit_pct: float | None = None,
        trailing_stop_pct: float | None = None,
        max_bars_in_trade: int | None = None,
        cooldown_bars_after_exit: int = 0,
    ):
        self.allowed_directions = allowed_directions
        self.regime_column = regime_column
        self.allowed_long_regimes = allowed_long_regimes
        self.allowed_short_regimes = allowed_short_regimes
        self.min_entry_score = min_entry_score
        self.min_volume_ratio = min_volume_ratio
        self.stop_loss_pct = stop_loss_pct
        self.trail_after_profit_pct = trail_after_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_bars_in_trade = max_bars_in_trade
        self.cooldown_bars_after_exit = cooldown_bars_after_exit

        self._entry_price: dict[str, float] = {}
        self._best_price: dict[str, float] = {}
        self._bars_in_trade: dict[str, int] = {}
        self._cooldown_until_bar: dict[str, int] = {}
        self._global_bar_count: int = 0
        self._last_bar_timestamp: datetime | None = None

    # ================================
    # --> Helper funcs
    # ================================

    def _in_cooldown(self, ticker: str) -> bool:
        return self._global_bar_count < self._cooldown_until_bar.get(ticker, 0)

    def _score_blocked(self, df: pd.DataFrame) -> bool:
        if self.min_entry_score is None:
            return False
        return self.candidate_score(df) < self.min_entry_score

    def _direction_blocked(self, df: pd.DataFrame) -> bool:
        direction = self.candidate_direction(df)
        return direction is None or direction not in self.allowed_directions

    def _regime_blocked(self, df: pd.DataFrame) -> bool:
        if self.regime_column is None:
            return False
        if not self.has_columns(df, self.regime_column):
            return True

        regime_value = self.latest_row(df)[self.regime_column]
        direction = self.candidate_direction(df)

        if direction == Direction.LONG and self.allowed_long_regimes:
            return regime_value not in self.allowed_long_regimes
        if direction == Direction.SHORT and self.allowed_short_regimes:
            return regime_value not in self.allowed_short_regimes
        return False

    def _liquidity_blocked(self, df: pd.DataFrame) -> bool:
        if self.min_volume_ratio is None:
            return False
        if not self.has_columns(df, "volume", "volume_ma"):
            return True
        latest = self.latest_row(df)
        volume_ma = latest["volume_ma"]
        if pd.isna(volume_ma) or volume_ma <= 0:
            return True
        return float(latest["volume"]) / float(volume_ma) < self.min_volume_ratio

    def _update_best_price(
        self, ticker: str, price: float, direction: Direction,
    ) -> float:
        best = self._best_price.get(ticker, price)
        if direction == Direction.LONG:
            best = max(best, price)
        else:
            best = min(best, price)
        self._best_price[ticker] = best
        return best

    def _hit_stop_loss(
        self, ticker: str, price: float, direction: Direction,
    ) -> bool:
        if self.stop_loss_pct is None:
            return False
        entry = self._entry_price.get(ticker)
        if entry is None:
            return False
        if direction == Direction.LONG:
            return price <= entry * (1 - self.stop_loss_pct)
        return price >= entry * (1 + self.stop_loss_pct)

    def _hit_trailing_stop(
        self, ticker: str, price: float, direction: Direction,
    ) -> bool:
        if self.trailing_stop_pct is None:
            return False

        entry = self._entry_price.get(ticker)
        if entry is None:
            return False

        best = self._update_best_price(ticker, price, direction)

        if self.trail_after_profit_pct is not None:
            if direction == Direction.LONG:
                armed = best >= entry * (1 + self.trail_after_profit_pct)
            else:
                armed = best <= entry * (1 - self.trail_after_profit_pct)
            if not armed:
                return False

        if direction == Direction.LONG:
            return price <= best * (1 - self.trailing_stop_pct)
        return price >= best * (1 + self.trailing_stop_pct)

    def _hit_time_stop(self, ticker: str) -> bool:
        if self.max_bars_in_trade is None:
            return False
        return self._bars_in_trade.get(ticker, 0) >= self.max_bars_in_trade

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
        if self._in_cooldown(ticker):
            return True
        if self._direction_blocked(df):
            return True
        if self._score_blocked(df):
            return True
        if self._regime_blocked(df):
            return True
        if self._liquidity_blocked(df):
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
        pos = portfolio.get_position(ticker)
        if pos is None:
            return False

        if self._hit_stop_loss(ticker, price, pos.direction):
            return True
        if self._hit_trailing_stop(ticker, price, pos.direction):
            return True
        if self._hit_time_stop(ticker):
            return True

        return False

    def on_entry(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._entry_price[ticker] = price
        self._best_price[ticker] = price
        self._bars_in_trade[ticker] = 0

    def on_exit(
        self,
        ticker: str,
        price: float,
        timestamp: datetime,
        direction: Direction = Direction.LONG,
    ) -> None:
        self._entry_price.pop(ticker, None)
        self._best_price.pop(ticker, None)
        self._bars_in_trade.pop(ticker, None)
        if self.cooldown_bars_after_exit > 0:
            self._cooldown_until_bar[ticker] = (
                self._global_bar_count + self.cooldown_bars_after_exit
            )

    def on_bar(self, ticker: str, price: float, timestamp: datetime) -> None:
        if self._last_bar_timestamp != timestamp:
            self._global_bar_count += 1
            self._last_bar_timestamp = timestamp
        if ticker in self._bars_in_trade:
            self._bars_in_trade[ticker] += 1
