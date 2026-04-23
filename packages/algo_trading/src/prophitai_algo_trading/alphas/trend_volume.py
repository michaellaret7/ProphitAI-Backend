"""Trend-with-volume-confirmation alpha.

MACD histogram gated by a rolling volume z-score. A strong trend signal
that also prints on above-average volume is treated as more informative
than the same MACD on thin volume — institutional flow is more likely
behind the higher-volume prints.

    macd_line    = EMA(close, fast) - EMA(close, slow)
    signal_line  = EMA(macd_line, signal)
    macd_hist    = macd_line - signal_line

    vol_z        = (volume_today - mean_vol_N) / std_vol_N
    gate         = max(vol_z, 0.5)    # floor so quiet days still count
    raw_score    = macd_hist * gate

The floor on the gate means quiet-volume days still contribute a
directional read at half weight. Prevents the alpha from zeroing out
during summer / thin-volume periods.
"""

from __future__ import annotations

from datetime import timedelta

from prophitai_algo_trading.framework.models import AlgorithmContext, Insight


#     ================================
# --> Helper funcs
#     ================================

def _macd_histogram(closes, fast: int, slow: int, signal: int) -> float:
    """MACD histogram at the last bar, computed vectorized via ewm()."""
    ema_fast = closes.ewm(span=fast, adjust=False).mean()
    ema_slow = closes.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow

    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    return float(macd_line.iloc[-1] - signal_line.iloc[-1])


def _volume_zscore(volume, lookback: int) -> float:
    """Z-score of today's volume vs rolling mean/std over ``lookback`` bars."""
    recent = volume.iloc[-lookback:]

    if len(recent) < 2:
        return 0.0

    mean_v = float(recent.mean())
    std_v = float(recent.std())

    if std_v <= 0.0:
        return 0.0

    return (float(volume.iloc[-1]) - mean_v) / std_v


#     ================================
# --> Alpha
#     ================================

class TrendVolumeAlpha:
    """MACD histogram scaled by rolling volume z-score.

    Args:
        fast: Fast EMA period for MACD (default 12).
        slow: Slow EMA period for MACD (default 26).
        signal: Signal-line EMA period (default 9).
        volume_lookback: Rolling window for volume z-score (default 20).
        gate_floor: Minimum gate value — thin-volume days still count
            at this weight. Default 0.5.
        hold_days: Informational ``close_time`` horizon.
    """

    name = "trend_vol"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        volume_lookback: int = 20,
        gate_floor: float = 0.5,
        hold_days: int = 5,
    ):
        self._fast = fast
        self._slow = slow
        self._signal = signal
        self._vol_lookback = volume_lookback
        self._gate_floor = gate_floor
        self._hold_days = hold_days

        # Reason: need slow-EMA to stabilize, then signal-EMA to settle on top.
        self.lookback = max(slow, volume_lookback) + signal

    def update(self, ctx: AlgorithmContext) -> list[Insight]:
        insights: list[Insight] = []

        close_time = ctx.timestamp + timedelta(days=self._hold_days)

        for symbol, df in ctx.data.items():
            if len(df) < self.lookback:
                continue

            macd_hist = _macd_histogram(
                df["close"], self._fast, self._slow, self._signal,
            )
            vol_z = _volume_zscore(df["volume"], self._vol_lookback)

            gate = max(vol_z, self._gate_floor)
            raw_score = macd_hist * gate

            direction = 1 if raw_score > 0.0 else -1 if raw_score < 0.0 else 0

            insights.append(Insight(
                symbol=symbol,
                direction=direction,
                generated_time=ctx.timestamp,
                close_time=close_time,
                magnitude=abs(raw_score),
                source_alpha=self.name,
            ))

        return insights
