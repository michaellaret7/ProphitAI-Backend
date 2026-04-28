"""ADX-as-alpha — trend-strength signed by long-term direction.

Wilder's Average Directional Index (1978) measures the strength of a
trend regardless of direction. Used standalone it has no sign — every
value is in [0, 100]. This alpha multiplies ADX by the sign of the
SMA(50) − SMA(200) golden-cross spread to produce a directional signal:

    +DM = max(H_t - H_{t-1}, 0) when (H_t-H_{t-1}) > (L_{t-1}-L_t), else 0
    -DM = max(L_{t-1} - L_t, 0) when (L_{t-1}-L_t) > (H_t-H_{t-1}), else 0
    TR  = max(H-L, |H - prev_C|, |L - prev_C|)

    +DI = 100 * Wilder_smooth(+DM) / Wilder_smooth(TR)
    -DI = 100 * Wilder_smooth(-DM) / Wilder_smooth(TR)
    DX  = 100 * |+DI - -DI| / (+DI + -DI)
    ADX = Wilder_smooth(DX)

    score = (ADX / 100) * sign(sma_long_short_spread)

Distinct from the other trend alphas: ADX is a *strength* gauge, not a
direction signal — multiplying by a long-term directional anchor turns
it into a regime-aware momentum bet that fires *only* when the trend
is strong.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from prophitai_algo_trading.alpha_signals.base import PerSymbolAlpha

if TYPE_CHECKING:
    import pandas as pd

    from prophitai_algo_trading.core.panel import PricePanel


#     ================================
# --> Helper funcs
#     ================================

def _wilder_smoothed(values, window: int):
    """Wilder smoothing — equivalent to ``ewm(alpha=1/window, adjust=False)``.

    Used to smooth +DM, -DM, TR, and DX into the ADX line. Wilder's
    original smoothing differs from a plain EMA by using ``alpha = 1/N``
    and an unweighted first ``window`` observations as the seed.
    """
    return values.ewm(alpha=1.0 / window, adjust=False).mean()


#     ================================
# --> Alpha
#     ================================

class ADXAlpha(PerSymbolAlpha):
    """ADX trend strength signed by long-term MA spread.

    Args:
        adx_window: Window for ADX smoothing (default 14 — Wilder's).
        ma_fast: Fast MA window for the directional sign (default 50).
        ma_slow: Slow MA window for the directional sign (default 200).
        hold_days: Informational ``close_time`` horizon. Strong trends
            persist for weeks, so hold longer than mean-reversion.
    """

    name = "adx"
    required_columns = ("high", "low", "close")

    def __init__(
        self,
        adx_window: int = 14,
        ma_fast: int = 50,
        ma_slow: int = 200,
        hold_days: int = 10,
    ):
        if ma_fast >= ma_slow:
            raise ValueError(
                f"ma_fast ({ma_fast}) must be < ma_slow ({ma_slow})",
            )

        self._adx_w = adx_window
        self._ma_fast = ma_fast
        self._ma_slow = ma_slow
        self.hold_days = hold_days

        self.lookback = ma_slow + adx_window

    def compute_score(self, symbol: str, df: "pd.DataFrame") -> float | None:
        high = df["high"]
        low = df["low"]
        close = df["close"]

        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        up = high - prev_high
        down = prev_low - low

        plus_dm = up.where((up > down) & (up > 0.0), 0.0)
        minus_dm = down.where((down > up) & (down > 0.0), 0.0)

        tr = np.maximum.reduce([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ])

        atr = _wilder_smoothed(tr, self._adx_w)

        plus_di = 100.0 * _wilder_smoothed(plus_dm, self._adx_w) / atr.where(atr > 0.0)
        minus_di = 100.0 * _wilder_smoothed(minus_dm, self._adx_w) / atr.where(atr > 0.0)

        di_sum = plus_di + minus_di
        dx = 100.0 * (plus_di - minus_di).abs() / di_sum.where(di_sum > 0.0)

        adx = _wilder_smoothed(dx.fillna(0.0), self._adx_w)

        sma_fast = close.rolling(self._ma_fast).mean()
        sma_slow = close.rolling(self._ma_slow).mean()

        sign = np.sign(sma_fast.iloc[-1] - sma_slow.iloc[-1])

        latest_adx = float(adx.iloc[-1])

        if latest_adx != latest_adx:  # NaN check
            return None

        return (latest_adx / 100.0) * float(sign)

    def compute_panel(self, panel: "PricePanel") -> "pd.DataFrame":
        """Vectorized ADX × MA-direction across the full panel."""
        if panel.high is None or panel.low is None:
            raise ValueError(
                "ADXAlpha.compute_panel requires panel.high and panel.low",
            )

        high = panel.high
        low = panel.low
        close = panel.close

        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        up = high - prev_high
        down = prev_low - low

        plus_dm = up.where((up > down) & (up > 0.0), 0.0)
        minus_dm = down.where((down > up) & (down > 0.0), 0.0)

        range_hl = high - low
        range_hc = (high - prev_close).abs()
        range_lc = (low - prev_close).abs()

        tr = np.maximum(np.maximum(range_hl, range_hc), range_lc)

        atr = _wilder_smoothed(tr, self._adx_w)

        plus_di = 100.0 * _wilder_smoothed(plus_dm, self._adx_w) / atr.where(atr > 0.0)
        minus_di = 100.0 * _wilder_smoothed(minus_dm, self._adx_w) / atr.where(atr > 0.0)

        di_sum = plus_di + minus_di
        dx = 100.0 * (plus_di - minus_di).abs() / di_sum.where(di_sum > 0.0)

        adx = _wilder_smoothed(dx.fillna(0.0), self._adx_w)

        sma_fast = close.rolling(self._ma_fast).mean()
        sma_slow = close.rolling(self._ma_slow).mean()

        direction = np.sign(sma_fast - sma_slow)

        return (adx / 100.0) * direction
