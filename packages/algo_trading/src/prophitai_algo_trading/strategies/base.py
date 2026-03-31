"""Base strategy class for all trading strategies.

Defines the pure strategy interface: strategies receive data and return
signals without owning state, position tracking, or execution context.
"""

from __future__ import annotations

from abc import abstractmethod, ABC
from datetime import datetime

import pandas as pd

from prophitai_algo_trading.execution.models import Direction, TradeCandidate


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Strategies are pure signal generators. They receive a DataFrame,
    compute indicators, and return entry/exit signals. They do NOT own
    data, track positions, manage warmup, or interact with brokers.

    Subclasses must implement:
        - calculate_indicators(df): Batch indicator calculation.
        - update_indicators(df): Incremental indicator update (last row).
        - generate_signals(df): Return 4 boolean Series dict.

    Optional sizing hooks:
        - get_sizing_hints(row, target_position): Strategy-specific sizing hints.
        - build_trade_candidate(...): Standardized candidate for shared sizers.
    """

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators on the full DataFrame.

        Args:
            df: OHLCV DataFrame to compute indicators on.

        Returns:
            DataFrame with indicator columns added.
        """

    @abstractmethod
    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update indicators for the last row only.

        Used by event-driven and live engines after appending a new bar.
        Falls back to calculate_indicators() if no incremental path exists.

        Args:
            df: DataFrame with indicators already computed for prior rows.

        Returns:
            DataFrame with last row's indicators updated.
        """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Generate entry/exit signals for the full DataFrame.

        Args:
            df: DataFrame with indicators already calculated.

        Returns:
            Dict with keys 'long_entry', 'long_exit', 'short_entry',
            'short_exit', each mapping to a boolean pd.Series.
        """

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """Score entry signals by conviction strength (higher = stronger).

        Used by engines to rank candidates when more entries fire than
        available position slots. Strategies should override this with
        a metric derived from their indicators (e.g. MACD histogram
        magnitude, RSI extremeness, z-score distance).

        Args:
            df: DataFrame with indicators already calculated.

        Returns:
            Float Series indexed like df. Higher values get fill priority.
        """
        return pd.Series(1.0, index=df.index)

    @property
    def min_bars_required(self) -> int:
        """Minimum bars needed before signals are meaningful.

        Override in subclasses to declare indicator warmup requirements.
        """
        return 0

    def get_sizing_hints(
        self,
        row: pd.Series,
        target_position: int,
    ) -> dict[str, object]:
        """Return standardized sizing hints derived from the latest indicator row.

        Strategies may override this to publish richer, strategy-specific sizing
        hints without exposing their private indicator internals to the sizer.
        """
        close = self._coerce_float(row.get("close"))
        volume = self._coerce_float(row.get("volume"))
        atr = self._first_finite(row, "atr", "atr_14")
        volatility = self._first_finite(
            row,
            "volatility",
            "realized_vol",
            "close_to_close_vol_20",
            "parkinson_vol_20",
        )

        stop_price = None
        if target_position > 0:
            stop_price = self._first_finite(
                row,
                "stop_long",
                "chandelier_long",
                "chandelier_long_stop",
                "chandelier_stop",
                "donchian_low",
                "or_low",
            )
        elif target_position < 0:
            stop_price = self._first_finite(
                row,
                "stop_short",
                "chandelier_short",
                "chandelier_short_stop",
                "donchian_high",
                "or_high",
            )

        stop_distance = None
        if close is not None and stop_price is not None:
            distance = abs(close - stop_price)
            stop_distance = distance if distance > 0 else None
        if stop_distance is None and atr is not None and atr > 0:
            stop_distance = atr

        hints: dict[str, object] = {}
        if atr is not None:
            hints["atr"] = atr
        if volatility is not None:
            hints["volatility"] = volatility
        if stop_price is not None:
            hints["stop_price"] = stop_price
        if stop_distance is not None:
            hints["stop_distance"] = stop_distance
            hints["risk_per_share"] = stop_distance

        regime = row.get("regime", row.get("hurst_regime"))
        if regime is not None and not pd.isna(regime):
            hints["regime"] = regime

        if close is not None and volume is not None:
            hints["liquidity"] = close * volume

        return hints

    def build_trade_candidate(
        self,
        symbol: str,
        row: pd.Series,
        target_position: int,
        timestamp: datetime | pd.Timestamp,
        score: float,
    ) -> TradeCandidate:
        """Build a standardized trade candidate from the latest strategy row."""
        if target_position == 0:
            raise ValueError("TradeCandidate is only defined for non-flat targets.")

        price = self._coerce_float(row.get("close"))
        if price is None:
            raise ValueError("TradeCandidate requires a finite close price.")

        hints = dict(self.get_sizing_hints(row, target_position))
        stop_price = self._coerce_float(hints.pop("stop_price", None))
        stop_distance = self._coerce_positive_float(hints.pop("stop_distance", None))
        risk_per_share = self._coerce_positive_float(hints.pop("risk_per_share", None))
        atr = self._coerce_positive_float(hints.pop("atr", None))
        volatility = self._coerce_positive_float(hints.pop("volatility", None))
        expected_holding_bars = self._coerce_int(hints.pop("expected_holding_bars", None))
        liquidity = self._coerce_positive_float(hints.pop("liquidity", None))
        regime = hints.pop("regime", None)

        if stop_distance is None and stop_price is not None:
            distance = abs(price - stop_price)
            stop_distance = distance if distance > 0 else None
        if risk_per_share is None:
            risk_per_share = stop_distance

        return TradeCandidate(
            symbol=symbol,
            direction=Direction.LONG if target_position > 0 else Direction.SHORT,
            target_position=target_position,
            price=price,
            timestamp=pd.Timestamp(timestamp).to_pydatetime(),
            score=float(score),
            strategy_id=self.__class__.__name__,
            stop_price=stop_price,
            stop_distance=stop_distance,
            risk_per_share=risk_per_share,
            atr=atr,
            volatility=volatility,
            regime=regime,
            expected_holding_bars=expected_holding_bars,
            liquidity=liquidity,
            raw_features=hints,
        )

    @staticmethod
    def _coerce_float(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @classmethod
    def _coerce_positive_float(cls, value: object) -> float | None:
        coerced = cls._coerce_float(value)
        if coerced is None or coerced <= 0:
            return None
        return coerced

    @staticmethod
    def _coerce_int(value: object) -> int | None:
        if value is None or pd.isna(value):
            return None
        return int(value)

    @classmethod
    def _first_finite(cls, row: pd.Series, *keys: str) -> float | None:
        for key in keys:
            if key not in row.index:
                continue
            value = cls._coerce_float(row.get(key))
            if value is not None:
                return value
        return None
