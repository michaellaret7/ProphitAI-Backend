"""Base strategy class.

A strategy transforms OHLCV price data into trade signals. That's the whole job.
No data fetching, no position tracking, no execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseStrategy(ABC):
    """Pure signal generator.

    Subclasses implement two methods:
        compute_indicators(df) -> df with indicator columns added
        compute_signals(df)    -> df with 'position' column in {-1, 0, 1}

    Optionally override ``score(df)`` to rank competing entry signals;
    default is 1.0 (equal ranking).

    ``min_bars`` declares warmup — engines will skip signal generation until
    each ticker has at least this many bars.
    """

    min_bars: int = 0

    @abstractmethod
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return df enriched with indicator columns.

        Args:
            df: OHLCV DataFrame with columns 'open','high','low','close','volume'.
        """

    @abstractmethod
    def compute_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return df with a 'position' column in {-1, 0, 1}.

        The position is the intended holding state for each bar:
            1  = long
            -1 = short
            0  = flat

        Engines lag this by one bar (signal at t -> fill at t+1) to prevent
        look-ahead bias. For intraday strategies where signal-on-close fills
        at the next bar's open, this is the correct interpretation.
        """

    def score(self, df: pd.DataFrame) -> pd.Series:
        """Rank entry signals by conviction. Higher = stronger.

        Used to pick the top-N tickers when more signals fire than
        ``max_positions`` allows. Default is equal ranking.
        """
        return pd.Series(1.0, index=df.index, dtype=float)
