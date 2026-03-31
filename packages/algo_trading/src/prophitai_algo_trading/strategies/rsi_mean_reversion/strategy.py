"""RSI(2) Mean Reversion strategy optimized for intraday timeframes.

Based on the Connors RSI(2) approach: enters on extreme RSI readings
(oversold/overbought) filtered by a trend SMA, exits when price reverts
to a short-term SMA.

Parameters tuned for 15-minute bars:
- RSI period: 2 (hyper-sensitive to short-term moves)
- Trend SMA: 200 (~8 trading days on 15-min bars)
- Exit SMA: 5 (~75 minutes on 15-min bars)
"""

import warnings

import pandas as pd

from prophitai_algo_trading.strategies.base import BaseStrategy
from prophitai_algo_trading.strategies.rsi_mean_reversion.indicators import (
    RSIMeanReversionIndicatorSuite,
)
from prophitai_algo_trading.strategies.rsi_mean_reversion.trade_logic import (
    RSIMeanReversionSignalModel,
)

warnings.filterwarnings("ignore", category=RuntimeWarning, module=__name__)


class RSIMeanReversion(BaseStrategy):
    """Mean reversion strategy using RSI(2) with SMA trend filter.

    Args:
        rsi_period: RSI lookback period.
        trend_sma_period: Trend filter SMA period.
        exit_sma_period: Exit trigger SMA period.
        rsi_oversold: RSI threshold for long entry.
        rsi_overbought: RSI threshold for short entry.
    """

    def __init__(
        self,
        rsi_period: int = 2,
        trend_sma_period: int = 200,
        exit_sma_period: int = 5,
        rsi_oversold: float = 10,
        rsi_overbought: float = 90,
    ):
        self.rsi_period = rsi_period
        self.trend_sma_period = trend_sma_period
        self.exit_sma_period = exit_sma_period
        self.rsi_oversold_threshold = rsi_oversold
        self.rsi_overbought_threshold = rsi_overbought
        self._indicator_suite: RSIMeanReversionIndicatorSuite | None = None
        self._signal_model = RSIMeanReversionSignalModel(
            rsi_oversold_threshold=rsi_oversold,
            rsi_overbought_threshold=rsi_overbought,
        )

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute RSI and SMAs on the full DataFrame."""
        if df.empty:
            return df

        self._indicator_suite = RSIMeanReversionIndicatorSuite(
            rsi_period=self.rsi_period,
            trend_sma_period=self.trend_sma_period,
            exit_sma_period=self.exit_sma_period,
        )
        return self._indicator_suite.calculate(df)

    def update_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Incrementally update RSI and SMAs for the last row."""
        if self._indicator_suite is None:
            return self.calculate_indicators(df)

        return self._indicator_suite.update_last_row(df)

    def generate_signals(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        """Return entry/exit boolean Series based on RSI and SMA conditions."""
        return self._signal_model.generate(df)

    def score_entries(self, df: pd.DataFrame) -> pd.Series:
        """RSI distance from neutral — more extreme readings = stronger mean-reversion signal."""
        return self._signal_model.score_entries(df)

    @property
    def min_bars_required(self) -> int:
        """Trend SMA needs the longest lookback."""
        return self.trend_sma_period
