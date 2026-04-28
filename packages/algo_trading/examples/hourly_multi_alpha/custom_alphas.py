"""Custom hourly alphas for the multi-alpha intraday example."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    from prophitai_algo_trading.core.panel import PricePanel


class OpeningGapContinuationAlpha(PerSymbolAlpha):
    """Follow the opening gap for the rest of the session."""

    name = "opening_gap_continuation"
    required_columns = ("open", "close")

    def __init__(self, hold_days: int = 1):
        self.hold_days = hold_days
        self.lookback = 2

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        timestamp = pd.Timestamp(df.index[-1])
        today = timestamp.normalize()
        today_bars = df[df.index.normalize() == today]

        if today_bars.empty:
            return None

        prior = df[df.index.normalize() < today]

        if prior.empty:
            return None

        first_open = float(today_bars["open"].iloc[0])
        prior_close = float(prior["close"].iloc[-1])

        if first_open <= 0.0 or prior_close <= 0.0:
            return None

        return (first_open / prior_close) - 1.0

    def compute_panel(self, panel: "PricePanel") -> pd.DataFrame:
        if panel.open is None:
            raise ValueError("OpeningGapContinuationAlpha requires panel.open")

        gap = (panel.open / panel.close.shift(1).where(panel.close.shift(1) > 0.0)) - 1.0
        date_index = pd.Series(panel.index.normalize(), index=panel.index)

        return gap.groupby(date_index).transform("first").fillna(0.0)


class EarlySessionRangeFadeAlpha(PerSymbolAlpha):
    """Fade stretches away from the first two-hour session range."""

    name = "early_session_range_fade"
    required_columns = ("high", "low", "close")

    def __init__(self, min_deviation: float = 0.25, hold_days: int = 1):
        self._min_deviation = min_deviation
        self.hold_days = hold_days
        self.lookback = 2

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        timestamp = pd.Timestamp(df.index[-1])
        today_bars = df[df.index.normalize() == timestamp.normalize()]

        if len(today_bars) < 2:
            return None

        first_two = today_bars.iloc[:2]
        range_high = float(first_two["high"].max())
        range_low = float(first_two["low"].min())
        current = float(today_bars["close"].iloc[-1])
        width = range_high - range_low

        if width <= 0.0 or current <= 0.0:
            return None

        deviation = (current - ((range_high + range_low) / 2.0)) / width

        if abs(deviation) < self._min_deviation:
            return 0.0

        return -deviation

    def compute_panel(self, panel: "PricePanel") -> pd.DataFrame:
        if panel.high is None or panel.low is None:
            raise ValueError("EarlySessionRangeFadeAlpha requires high/low")

        scores = pd.DataFrame(0.0, index=panel.index, columns=panel.tickers)
        dates = pd.Series(panel.index.normalize(), index=panel.index)

        for _, day_index in dates.groupby(dates).groups.items():
            if len(day_index) < 2:
                continue

            first_two = list(day_index[:2])
            range_high = panel.high.loc[first_two].max(axis=0)
            range_low = panel.low.loc[first_two].min(axis=0)
            width = range_high - range_low
            mid = (range_high + range_low) / 2.0
            day_close = panel.close.loc[day_index]
            deviation = day_close.sub(mid, axis=1).div(width.where(width > 0.0), axis=1)
            deviation = deviation.where(deviation.abs() >= self._min_deviation, 0.0)
            scores.loc[day_index] = -deviation

        return scores.fillna(0.0)


class IntradayTrendPersistenceAlpha(PerSymbolAlpha):
    """Ride short-term hourly trends when recent bars agree."""

    name = "intraday_trend_persistence"

    def __init__(
        self,
        window: int = 4,
        min_consistency: float = 0.75,
        hold_days: int = 1,
    ):
        self._window = window
        self._min_consistency = min_consistency
        self.hold_days = hold_days
        self.lookback = window + 1

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        returns = df["close"].pct_change().tail(self._window).dropna()

        if len(returns) < self._window:
            return None

        signs = np.sign(returns.to_numpy(dtype=float))
        consistency = abs(float(signs.sum())) / float(self._window)

        if consistency < self._min_consistency:
            return 0.0

        return float(returns.mean() * consistency)

    def compute_panel(self, panel: "PricePanel") -> pd.DataFrame:
        returns = panel.close.pct_change()
        sign_sum = np.sign(returns).rolling(self._window).sum().abs()
        consistency = sign_sum / float(self._window)
        score = returns.rolling(self._window).mean() * consistency

        return score.where(consistency >= self._min_consistency, 0.0).fillna(0.0)


class RelativeVolumeReversalAlpha(PerSymbolAlpha):
    """Fade unusually high-volume hourly price moves."""

    name = "relative_volume_reversal"
    required_columns = ("close", "volume")

    def __init__(
        self,
        volume_window: int = 20,
        min_volume_z: float = 1.5,
        hold_days: int = 1,
    ):
        self._volume_window = volume_window
        self._min_volume_z = min_volume_z
        self.hold_days = hold_days
        self.lookback = volume_window + 2

    def compute_score(self, symbol: str, df: pd.DataFrame) -> float | None:
        closes = df["close"]
        volumes = df["volume"]
        current_volume = float(volumes.iloc[-1])
        prior_volume = volumes.iloc[-(self._volume_window + 1):-1]
        mean = float(prior_volume.mean())
        std = float(prior_volume.std(ddof=1))
        prev_close = float(closes.iloc[-2])
        current_close = float(closes.iloc[-1])

        if std <= 0.0 or prev_close <= 0.0 or current_close <= 0.0:
            return None

        volume_z = (current_volume - mean) / std

        if volume_z < self._min_volume_z:
            return 0.0

        return -((current_close / prev_close) - 1.0) * volume_z

    def compute_panel(self, panel: "PricePanel") -> pd.DataFrame:
        if panel.volume is None:
            raise ValueError("RelativeVolumeReversalAlpha requires panel.volume")

        prior_mean = panel.volume.shift(1).rolling(self._volume_window).mean()
        prior_std = panel.volume.shift(1).rolling(self._volume_window).std(ddof=1)
        volume_z = panel.volume.sub(prior_mean).div(prior_std.where(prior_std > 0.0))
        returns = panel.close.pct_change()
        score = -returns * volume_z

        return score.where(volume_z >= self._min_volume_z, 0.0).fillna(0.0)
