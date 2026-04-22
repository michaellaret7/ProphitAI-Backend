"""Custom intraday indicators used by the long/short strategy.

All indicators reset at the start of each new trading session so that
intraday computations (VWAP, session return, session volatility) don't
bleed across days.
"""
from collections import deque
from math import sqrt


#     ================================
# --> Session VWAP deviation
#     ================================

class SessionVWAPDeviation:
    """Percent deviation of current price from the session-to-date VWAP.

    VWAP = sum(typical_price * volume) / sum(volume), where typical_price
    is (H + L + C) / 3. Deviation is (close - vwap) / vwap.

    Positive values mean the stock is trading above its session VWAP
    (likely overbought intraday); negative means below (likely oversold).
    """

    def __init__(self) -> None:
        self._last_day: int | None = None
        self._pv: float = 0.0
        self._v: float = 0.0
        self._vwap: float = 0.0
        self._deviation: float = 0.0

    @property
    def value(self) -> float:
        return self._deviation

    @property
    def vwap(self) -> float:
        return self._vwap

    @property
    def is_ready(self) -> bool:
        return self._v > 0.0

    def update(self, bar_time, high: float, low: float, close: float, volume: float) -> None:
        day_key = bar_time.date().toordinal()

        if self._last_day != day_key:
            self._last_day = day_key
            self._pv = 0.0
            self._v = 0.0
            self._vwap = 0.0
            self._deviation = 0.0

        typical = (high + low + close) / 3.0
        self._pv += typical * volume
        self._v += volume

        if self._v > 0:
            self._vwap = self._pv / self._v

        if self._vwap > 0:
            self._deviation = (close - self._vwap) / self._vwap


#     ================================
# --> Session return z-score
#     ================================

class SessionReturnZScore:
    """Z-score of the stock's session-to-date return vs its own rolling
    history of session-to-date returns at the same intraday time slot.

    This is a self-normalising intraday momentum gauge. Extreme positive
    values => stock is exceptionally up intraday vs its own history;
    extreme negative => exceptionally down. Used for ranking, not entry
    thresholds directly.
    """

    def __init__(self, lookback_sessions: int = 20) -> None:
        self._lookback = lookback_sessions

        self._last_day: int | None = None
        self._session_open: float | None = None
        self._session_returns: deque[float] = deque(maxlen=lookback_sessions)

        self._value: float = 0.0
        self._current_return: float = 0.0

    @property
    def value(self) -> float:
        return self._value

    @property
    def current_return(self) -> float:
        return self._current_return

    @property
    def is_ready(self) -> bool:
        return len(self._session_returns) >= max(3, self._lookback // 2)

    def update(self, bar_time, open_price: float, close: float) -> None:
        day_key = bar_time.date().toordinal()

        if self._last_day != day_key:
            if self._session_open is not None and self._current_return != 0.0:
                self._session_returns.append(self._current_return)

            self._last_day = day_key
            self._session_open = open_price
            self._current_return = 0.0
            self._value = 0.0
            return

        if self._session_open is None or self._session_open <= 0.0:
            return

        self._current_return = (close - self._session_open) / self._session_open

        if len(self._session_returns) < 3:
            return

        n = len(self._session_returns)
        mean = sum(self._session_returns) / n
        var = sum((r - mean) ** 2 for r in self._session_returns) / (n - 1)
        std = sqrt(var) if var > 0 else 0.0

        self._value = (self._current_return - mean) / std if std > 0 else 0.0
